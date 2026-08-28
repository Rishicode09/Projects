"""Bootstrap YOLO bounding boxes for EL defects.

**The problem this exists to solve.** ELPV has image-level labels only — one
probability per cell, no boxes, no masks. Ultralytics cannot train on that.
Someone has to draw boxes, and drawing them for 821 cracked cells from scratch
is days of expert time.

**What this does instead.** It proposes boxes automatically from the classical
crack response already computed in ``preprocess.cell_prep``, restricted to cells
the annotation (or the classifier) says are cracked. A human then corrects the
proposals in a labelling tool, which is several times faster than drawing from
nothing.

**What this is not.** These are *proposals*, not ground truth. The generator has
no notion of what a crack is; it finds dark connected regions that survive
morphological filtering. Training a detector directly on unreviewed output
teaches it to reproduce the generator's mistakes.

**Measured behaviour on real ELPV cells** (run
``scripts/build_detection_dataset.py`` and look at ``proposal_preview.png``
yourself before trusting any of this):

* *Dark inactive regions: good.* Large disconnected areas are boxed tightly and
  classified correctly. This is the more valuable half, because inactive area is
  what the physics model actually consumes — see ``detector.defect_area_fraction``.
* *Hairline diagonal cracks: poor.* The faint branching cracks common in
  polycrystalline cells frequently go unboxed. The black-hat response is tuned
  for contrast against the local background and these barely clear the noise
  floor. Expect to draw most crack boxes by hand.
* *Metallisation: filtered, imperfectly.* Busbars and fingers are dark lines and
  were the largest source of junk before ``is_grid_structure`` rejected
  axis-aligned thin regions. Some finger segments still survive.

So: run this, review in a labelling tool, *then* train. The review step is not
optional and no part of this repo pretends otherwise. If your imagery is mostly
hairline cracking, ``--no-proposals`` and annotating from scratch may genuinely
be faster than correcting these.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

from ..preprocess.cell_prep import crack_response, flatten_illumination, to_grayscale_float

logger = logging.getLogger(__name__)

# Two classes, separated by shape. See classify_region for the heuristic.
CLASS_NAMES = ("crack", "inactive_area")
CRACK = 0
INACTIVE_AREA = 1


@dataclass(frozen=True)
class Region:
    """A proposed defect region in pixel coordinates."""

    x: int
    y: int
    width: int
    height: int
    class_id: int
    score: float

    def to_yolo(self, image_width: int, image_height: int) -> tuple[float, float, float, float]:
        """Normalised centre-x, centre-y, width, height — the YOLO label format."""
        return (
            (self.x + self.width / 2) / image_width,
            (self.y + self.height / 2) / image_height,
            self.width / image_width,
            self.height / image_height,
        )


def is_grid_structure(
    width: int,
    height: int,
    image_width: int,
    image_height: int,
    span_fraction: float = 0.40,
    thin_fraction: float = 0.05,
) -> bool:
    """True if a region looks like metallisation (busbar or finger), not a defect.

    Busbars and fingers are dark in EL, so the black-hat response finds them
    just as readily as it finds cracks. Every cell has several, so boxing them
    puts false positives on every image in the dataset — on real ELPV cells
    they were the single largest source of junk proposals.

    Geometry separates them. Metallisation is an **axis-aligned thin line**: it
    runs horizontally or vertically and is only a few pixels across. A real
    crack is diagonal, branched, or irregular, so its bounding box is wide in
    *both* axes even when the crack itself is hairline — a diagonal crack
    spanning a cell has a box roughly as tall as it is wide, and is not caught
    here.

    The span threshold is deliberately low (40%): fingers often break into
    segments, and a half-width thin horizontal line is still a finger.

    The cost: a crack running exactly along a busbar, or a genuine
    finger-interruption defect, is suppressed with the metallisation. That is a
    real blind spot, and it is one reason a human reviewer still has to look at
    the cells and not only at the proposals.
    """
    spans_vertically = height >= span_fraction * image_height
    spans_horizontally = width >= span_fraction * image_width
    is_thin_vertically = width <= thin_fraction * image_width
    is_thin_horizontally = height <= thin_fraction * image_height

    return (spans_vertically and is_thin_vertically) or (
        spans_horizontally and is_thin_horizontally
    )


def touches_border_marginally(
    x: int,
    y: int,
    width: int,
    height: int,
    image_width: int,
    image_height: int,
    margin: int = 3,
    small_fraction: float = 0.02,
) -> bool:
    """True for small regions hugging the crop edge.

    These are almost always the dark inter-cell gap bleeding into the crop
    rather than a defect — on real ELPV cells they appear as little boxes
    pinned to the corners. A genuine edge crack is larger than this threshold,
    so requiring both "touching the border" and "small" keeps them.
    """
    touching = (
        x <= margin
        or y <= margin
        or (x + width) >= image_width - margin
        or (y + height) >= image_height - margin
    )
    is_small = (width * height) < small_fraction * image_width * image_height
    return touching and is_small


def classify_region(width: int, height: int, area: int) -> int:
    """Crack or inactive area, from shape alone.

    A crack is thin and elongated: high bounding-box aspect ratio, and a small
    filled *fraction* of that box because the crack is a line through it. An
    inactive region is a blob — it fills most of its box.

    This is a geometric heuristic standing in for a physical distinction, and it
    is the first thing a human reviewer should expect to correct. It is worth
    keeping the two classes apart even so: they enter the physics model through
    different parameters (area loss versus series resistance).
    """
    aspect = max(width, height) / max(1, min(width, height))
    fill = area / max(1, width * height)

    if aspect >= 2.5 or fill < 0.35:
        return CRACK
    return INACTIVE_AREA


def propose_regions(
    image: np.ndarray,
    min_area_fraction: float = 0.002,
    max_area_fraction: float = 0.60,
    max_regions: int = 6,
    noise_sigmas: float = 5.0,
    minimum_response: float = 0.06,
) -> list[Region]:
    """Candidate defect boxes for one cell crop.

    Two detectors are unioned, because the two defect families look nothing
    alike in EL:

    * the black-hat crack response, thresholded against its noise floor —
      finds thin dark lines;
    * a low-intensity mask against the cell's own bright population — finds
      large dead regions, which the black-hat kernel is too small to see.

    ``noise_sigmas`` sets how far above the noise floor a pixel must sit to
    count as crack-like. Lower it to catch fainter cracks at the cost of more
    junk for the reviewer to delete.
    """
    gray = to_grayscale_float(image)
    height, width = gray.shape[:2]
    total_area = height * width

    # --- thin dark lines -------------------------------------------------
    # Threshold the crack response against its own *noise floor*, estimated
    # robustly with the median absolute deviation.
    #
    # Otsu is the obvious choice here and is wrong: it always returns a split,
    # even when the response is pure sensor noise with no crack in it. On a
    # clean cell that lights up roughly two thirds of the image, which then
    # either floods the label file with junk boxes or collapses into one
    # cell-sized box. MAD asks a different question — "is anything here far
    # above the noise?" — and answers "no" when nothing is.
    response = crack_response(gray)
    median = float(np.median(response))
    mad = float(np.median(np.abs(response - median))) * 1.4826  # -> sigma equivalent

    if mad > 1e-6:
        threshold = max(median + noise_sigmas * mad, minimum_response)
    else:
        threshold = max(minimum_response, float(response.max()) * 0.5)

    crack_mask = ((response > threshold).astype(np.uint8)) * 255

    # If the "cracks" cover most of the cell, the response was noise-dominated
    # and the threshold found nothing real. Discard rather than emit one huge
    # box; the dark-region detector below still gets its chance.
    if crack_mask.sum() / 255.0 > 0.40 * total_area:
        logger.debug("Crack response covers >40%% of the cell; treating as noise.")
        crack_mask = np.zeros((height, width), dtype=np.uint8)

    # Join collinear fragments: a crack often breaks into pieces under
    # thresholding, and six boxes on one crack is worse than one.
    crack_mask = cv2.morphologyEx(
        crack_mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    )

    # --- large dead regions ----------------------------------------------
    flattened = flatten_illumination(gray)
    reference = float(np.quantile(flattened, 0.90))
    if reference > 1e-6:
        dark_mask = ((flattened / reference) < 0.35).astype(np.uint8) * 255
        dark_mask = cv2.morphologyEx(
            dark_mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        )
    else:
        dark_mask = np.zeros((height, width), dtype=np.uint8)

    combined = cv2.bitwise_or(crack_mask, dark_mask)

    count, labels, stats, _ = cv2.connectedComponentsWithStats(combined, connectivity=8)

    regions: list[Region] = []
    for index in range(1, count):  # 0 is background
        x, y, w, h, area = stats[index]
        fraction = area / total_area

        if fraction < min_area_fraction or fraction > max_area_fraction:
            continue
        # Ignore slivers hugging the border: those are crop artefacts from the
        # inter-cell gap, not defects.
        if w < 4 or h < 4:
            continue
        # Every cell has busbars and fingers; boxing them would put a false
        # positive on every image in the dataset.
        if is_grid_structure(w, h, width, height):
            continue
        # Small boxes pinned to the crop edge are inter-cell gap bleed.
        if touches_border_marginally(x, y, w, h, width, height):
            continue

        class_id = classify_region(w, h, int(area))
        # Score by area share — the only ranking signal available without a
        # model. Used solely to keep the largest few proposals.
        regions.append(Region(int(x), int(y), int(w), int(h), class_id, float(fraction)))

    regions.sort(key=lambda r: r.score, reverse=True)
    if len(regions) > max_regions:
        logger.debug("Trimming %d proposals to %d", len(regions), max_regions)
    return regions[:max_regions]


def proposals_to_yolo_lines(regions: list[Region], width: int, height: int) -> list[str]:
    """Format proposals as YOLO label-file lines."""
    lines = []
    for region in regions:
        cx, cy, w, h = region.to_yolo(width, height)
        cx, cy = np.clip(cx, 0.0, 1.0), np.clip(cy, 0.0, 1.0)
        w, h = np.clip(w, 1e-6, 1.0), np.clip(h, 1e-6, 1.0)
        lines.append(f"{region.class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    return lines


def draw_proposals(image: np.ndarray, regions: list[Region]) -> np.ndarray:
    """Render boxes on a cell, for eyeballing proposal quality before review."""
    gray = to_grayscale_float(image)
    canvas = cv2.cvtColor((gray * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)

    colours = {CRACK: (0, 0, 255), INACTIVE_AREA: (0, 200, 255)}
    for region in regions:
        colour = colours.get(region.class_id, (0, 255, 0))
        cv2.rectangle(
            canvas, (region.x, region.y),
            (region.x + region.width, region.y + region.height), colour, 2,
        )
        cv2.putText(
            canvas, CLASS_NAMES[region.class_id], (region.x, max(12, region.y - 4)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, colour, 1, cv2.LINE_AA,
        )
    return canvas
