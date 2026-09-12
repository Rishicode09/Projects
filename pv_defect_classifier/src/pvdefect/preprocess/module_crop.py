"""Crop a full module EL image into its individual cells (OpenCV).

ELPV ships pre-cropped cells, but a real inspection campaign produces one
photograph per *module* — a 6x10 or 6x12 grid of cells, shot at an angle from a
ladder or a drone. Everything downstream in this repo is per-cell, so this is
the front door of the pipeline.

The approach is deliberately classical rather than learned:

1. **Find the module.** The laminate is the bright region on a dark background;
   a blur + Otsu threshold + largest-contour search isolates it.
2. **Rectify it.** Fit a quadrilateral to that contour and warp it to a
   rectangle. EL photographs are almost never taken square-on, and an
   uncorrected perspective makes every cell in the far row a different size —
   which the classifier then reads as a defect signal.
3. **Split the grid.** Once rectified, cells are a regular grid. We refine the
   nominal cut lines against the dark inter-cell gaps so a slightly non-square
   laminate does not shear the crops.

A learned segmenter (Deitsch et al. 2021 do exactly this) is more robust on
badly lit or partially occluded modules. This is the dependency-light version
that works on clean inspection imagery and fails loudly rather than silently.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_CELL_SIZE = 300  # matches ELPV, so crops are drop-in for the classifier


@dataclass(frozen=True)
class ModuleGrid:
    """Result of cropping one module."""

    cells: list[np.ndarray]
    rows: int
    columns: int
    rectified: np.ndarray
    corners: np.ndarray | None

    def __len__(self) -> int:
        return len(self.cells)

    def cell_at(self, row: int, column: int) -> np.ndarray:
        """Cell by grid position. Index order matches the series string order."""
        return self.cells[row * self.columns + column]


def _order_corners(points: np.ndarray) -> np.ndarray:
    """Order four points as top-left, top-right, bottom-right, bottom-left.

    Sorted by angle about the centroid rather than by the usual x+y / y-x
    extremes. The extremes trick is shorter but it can assign the *same* point
    to two slots on quadrilaterals that are strongly sheared — which is exactly
    what a photograph taken from a ladder produces. The resulting degenerate
    quad silently warps the whole module to a uniform smear, so the robust
    version is worth the extra few lines.
    """
    points = points.reshape(4, 2).astype(np.float32)
    centroid = points.mean(axis=0)

    # atan2 measured from the centroid, y down: angles increase clockwise
    # starting from "left".
    angles = np.arctan2(points[:, 1] - centroid[1], points[:, 0] - centroid[0])
    ordered = points[np.argsort(angles)]

    # argsort by angle starts wherever the first point happens to fall; rotate
    # so index 0 is the corner closest to the origin (top-left).
    start = int(np.argmin(ordered.sum(axis=1)))
    return np.roll(ordered, -start, axis=0).astype(np.float32)


def _is_valid_quadrilateral(
    corners: np.ndarray, reference_area: float, min_coverage: float = 0.90
) -> bool:
    """Reject degenerate, concave, or loose-fitting quads.

    Three failure modes seen on real imagery:

    * **Duplicated corners** — a zero-area quad, which warps the module to a
      uniform smear.
    * **Concave fits** — ``approxPolyDP`` on a ragged contour can pick four
      vertices that fold in on themselves.
    * **Loose fits** — the killer, and the reason ``min_coverage`` is 0.90
      rather than something permissive. A quad enclosing, say, 60% of the
      contour has latched onto internal structure (the dark inter-cell gaps
      read as background after thresholding, so the contour is ragged). It
      passes a lenient check, produces cell crops whose *statistics* look
      right, and yet every crop straddles two cells. A genuinely
      perspective-distorted module still yields a tight quad, so this
      threshold does not cost us the case rectification exists for.
    """
    if corners is None or len(corners) != 4:
        return False

    # Any two corners closer than a pixel means the fit collapsed.
    for i in range(4):
        for j in range(i + 1, 4):
            if np.linalg.norm(corners[i] - corners[j]) < 1.0:
                logger.debug("Degenerate module quad: corners %d and %d coincide.", i, j)
                return False

    as_contour = corners.astype(np.float32).reshape(-1, 1, 2)
    if not cv2.isContourConvex(as_contour):
        logger.debug("Fitted module quad is not convex; rejecting.")
        return False

    quad_area = float(cv2.contourArea(as_contour))
    if quad_area < min_coverage * reference_area:
        logger.debug(
            "Fitted quad covers only %.0f%% of the detected contour; rejecting.",
            100 * quad_area / max(reference_area, 1e-9),
        )
        return False
    return True


def find_module_corners(image: np.ndarray, min_area_fraction: float = 0.15) -> np.ndarray | None:
    """Locate the four corners of the laminate, or ``None`` if not confident.

    Returning ``None`` rather than a guess is deliberate: a wrong rectification
    silently mis-crops every cell in the module, and a mis-cropped cell that
    lands half on a busbar looks exactly like a defect. Better to skip the
    perspective step and crop the raw grid.
    """
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if gray.dtype != np.uint8:
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    # Segment on local *texture*, not brightness.
    #
    # The obvious approach — Otsu on intensity, keep the bright blob — fails on
    # exactly the modules this project cares about. A module with dark
    # defective cells along one edge has those cells thresholded away as
    # background, so the outline is found several hundred pixels inside the
    # laminate and every subsequent cell crop straddles two cells. The failure
    # is silent: the crops still have plausible mean and variance.
    #
    # Local standard deviation separates them properly. Silicon has structure
    # at every brightness — busbars, fingers, grain — while the surround in an
    # EL photograph is flat. A dead black cell still has visible metallisation.
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    window = max(5, int(0.01 * max(gray.shape[:2])) | 1)
    as_float = blurred.astype(np.float32)
    local_mean = cv2.boxFilter(as_float, -1, (window, window))
    local_mean_square = cv2.boxFilter(as_float * as_float, -1, (window, window))
    local_std = np.sqrt(np.maximum(local_mean_square - local_mean * local_mean, 0.0))

    # Threshold at a low fraction of the robust maximum, NOT with Otsu.
    #
    # Otsu finds the split that best separates the two dominant populations,
    # and in a module containing both dead cells and healthy ones those two
    # populations are dark-cell texture and bright-cell texture — so it cuts
    # *inside* the laminate and discards the dead row. The question here is the
    # different one of "structure or no structure", and the background has
    # essentially none, so a low absolute cut is both correct and more stable.
    robust_max = float(np.percentile(local_std, 99.0))
    if robust_max < 1e-6:
        logger.warning("Image has no local texture at all; cannot locate a module.")
        return None

    binary = ((local_std > 0.12 * robust_max).astype(np.uint8)) * 255

    # Close the inter-cell gaps so the laminate is one blob, not a grid of them.
    #
    # The kernel must scale with the image. A fixed 15x15 works on a
    # thumbnail-sized module and is far too small on a 3000-pixel-wide
    # inspection photograph, where it leaves the cells as separate blobs and the
    # largest "contour" becomes one cell rather than the laminate.
    kernel_size = max(15, int(0.02 * max(gray.shape[:2])) | 1)  # odd, >= 15
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        logger.warning("No contours found; skipping perspective correction.")
        return None

    largest = max(contours, key=cv2.contourArea)
    contour_area = float(cv2.contourArea(largest))
    if contour_area < min_area_fraction * gray.size:
        logger.warning("Largest contour covers <%.0f%% of the frame; not a module.",
                       100 * min_area_fraction)
        return None

    # Try progressively looser polygon approximations for a 4-gon. This path
    # handles genuine perspective, where the laminate is a general trapezoid
    # that a rotated rectangle cannot represent.
    perimeter = cv2.arcLength(largest, True)
    for epsilon_factor in (0.02, 0.03, 0.05, 0.08):
        approximation = cv2.approxPolyDP(largest, epsilon_factor * perimeter, True)
        if len(approximation) == 4:
            corners = _order_corners(approximation)
            if _is_valid_quadrilateral(corners, contour_area):
                return corners

    # Fall back to the minimum-area rotated rectangle. It cannot express
    # perspective, but it is far more stable than approxPolyDP on a ragged
    # contour, and a rotated rectangle is the right answer for the common case
    # of a module photographed roughly square-on but not perfectly level.
    box = cv2.boxPoints(cv2.minAreaRect(largest))
    corners = _order_corners(box)
    # A rotated rectangle always circumscribes the contour, so it over-covers
    # rather than under-covers; judge it on how tightly it does so.
    box_area = float(cv2.contourArea(corners.astype(np.float32).reshape(-1, 1, 2)))
    if box_area <= 0 or contour_area / box_area < 0.75:
        logger.warning(
            "Best-fit rectangle covers the contour only loosely (%.0f%%); the shape is "
            "probably not a module. Skipping rectification.",
            100 * contour_area / max(box_area, 1e-9),
        )
        return None

    logger.info("Using minAreaRect for module corners.")
    return corners


def rectify_module(
    image: np.ndarray,
    corners: np.ndarray | None = None,
    output_size: tuple[int, int] | None = None,
) -> tuple[np.ndarray, np.ndarray | None]:
    """Warp the module to a front-on rectangle.

    Output dimensions default to the median side lengths of the detected
    quadrilateral, which preserves the module's aspect ratio instead of forcing
    it into a square.
    """
    if corners is None:
        corners = find_module_corners(image)
    if corners is None:
        return image, None

    top_left, top_right, bottom_right, bottom_left = corners
    width = int(max(np.linalg.norm(top_right - top_left),
                    np.linalg.norm(bottom_right - bottom_left)))
    height = int(max(np.linalg.norm(bottom_left - top_left),
                     np.linalg.norm(bottom_right - top_right)))

    if output_size is not None:
        width, height = output_size
    if width < 10 or height < 10:
        logger.warning("Degenerate module quad (%dx%d); skipping rectification.", width, height)
        return image, None

    destination = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32
    )
    transform = cv2.getPerspectiveTransform(corners, destination)
    return cv2.warpPerspective(image, transform, (width, height)), corners


def _refine_cut_positions(
    profile: np.ndarray, count: int, search_fraction: float = 0.3
) -> list[int]:
    """Snap ``count + 1`` evenly spaced cuts onto the darkest nearby columns/rows.

    Inter-cell gaps are dark lines in EL, so the intensity profile has minima
    there. We only search a fraction of a cell width around each nominal cut,
    which keeps a strong busbar from stealing a cut line.
    """
    length = len(profile)
    spacing = length / count
    window = max(1, int(search_fraction * spacing / 2))

    cuts = []
    for index in range(count + 1):
        nominal = int(round(index * spacing))
        if index in (0, count):           # outer edges stay put
            cuts.append(int(np.clip(nominal, 0, length)))
            continue
        low = max(0, nominal - window)
        high = min(length, nominal + window + 1)
        cuts.append(int(low + np.argmin(profile[low:high])) if high > low else nominal)
    return cuts


def split_into_cells(
    rectified: np.ndarray,
    rows: int = 6,
    columns: int = 10,
    cell_size: int = DEFAULT_CELL_SIZE,
    refine: bool = True,
    border_trim: float = 0.02,
) -> list[np.ndarray]:
    """Cut a rectified module into ``rows * columns`` square cell crops.

    Cells are returned in reading order (left to right, top to bottom). That
    order is what the physics model treats as the series-string order, so if
    your module is wired in a serpentine you need to reorder before simulating
    — it changes which cells share a bypass diode.
    """
    gray = rectified if rectified.ndim == 2 else cv2.cvtColor(rectified, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape[:2]

    if refine:
        # Mean along each axis: dark inter-cell gaps show as minima.
        column_cuts = _refine_cut_positions(gray.mean(axis=0), columns)
        row_cuts = _refine_cut_positions(gray.mean(axis=1), rows)
    else:
        column_cuts = [int(round(i * width / columns)) for i in range(columns + 1)]
        row_cuts = [int(round(i * height / rows)) for i in range(rows + 1)]

    cells: list[np.ndarray] = []
    for row in range(rows):
        for column in range(columns):
            y0, y1 = row_cuts[row], row_cuts[row + 1]
            x0, x1 = column_cuts[column], column_cuts[column + 1]

            # Trim a sliver off each edge so the dark gap does not bleed in and
            # register as an inactive region.
            trim_y = int(border_trim * max(1, y1 - y0))
            trim_x = int(border_trim * max(1, x1 - x0))
            crop = rectified[y0 + trim_y : max(y0 + trim_y + 1, y1 - trim_y),
                             x0 + trim_x : max(x0 + trim_x + 1, x1 - trim_x)]

            if crop.size == 0:
                logger.warning("Empty crop at row %d column %d; substituting zeros.", row, column)
                crop = np.zeros((cell_size, cell_size), dtype=rectified.dtype)

            cells.append(cv2.resize(crop, (cell_size, cell_size), interpolation=cv2.INTER_AREA))
    return cells


def crop_module(
    image: np.ndarray,
    rows: int = 6,
    columns: int = 10,
    cell_size: int = DEFAULT_CELL_SIZE,
    rectify: bool = True,
) -> ModuleGrid:
    """Full pipeline: raw module photograph -> list of cell crops.

    ``rows`` x ``columns`` must match the physical module (6x10 for a 60-cell,
    6x12 for a 72-cell). There is no attempt to infer the layout automatically:
    guessing it wrong shifts every cell index, and the physics model's bypass
    grouping depends on that index.
    """
    if rectify:
        rectified, corners = rectify_module(image)
    else:
        rectified, corners = image, None

    cells = split_into_cells(rectified, rows=rows, columns=columns, cell_size=cell_size)
    logger.info("Cropped module into %d cells (%dx%d)", len(cells), rows, columns)

    return ModuleGrid(
        cells=cells, rows=rows, columns=columns, rectified=rectified, corners=corners
    )
