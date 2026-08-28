"""OpenCV preprocessing for electroluminescence cell crops.

EL imagery has failure modes that ordinary photographic augmentation pipelines
handle badly:

* **Exposure varies between modules, not within them.** EL brightness depends
  on injection current and camera integration time, both set per module. A
  network trained on raw intensities learns the exposure of each module rather
  than its defects. We normalise per cell.

* **Busbars and fingers are high-contrast vertical/horizontal lines** that look
  like cracks to an edge detector. They are also *informative* (a broken finger
  is a real defect), so we do not remove them; we give the model a channel
  where they are suppressed alongside one where they are not.

* **Vignetting.** Cells at a module's edge are dimmer at their outer border.
  A large-kernel background division flattens this without touching the small
  dark features that indicate cracks.

The output of :func:`preprocess_cell` is a 3-channel stack that stays
compatible with ImageNet-pretrained backbones while carrying more physics than
a replicated grayscale image would.
"""

from __future__ import annotations

import cv2
import numpy as np

DEFAULT_SIZE = 224


def to_grayscale_float(image: np.ndarray) -> np.ndarray:
    """Coerce any input to a single-channel float32 array in [0, 1]."""
    if image.ndim == 3:
        channels = image.shape[2]
        if channels == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY)
        elif channels == 3:
            image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            image = image[..., 0]

    image = image.astype(np.float32)
    if image.max() > 1.5:  # 8- or 16-bit integer range
        image /= float(np.iinfo(np.uint8).max if image.max() <= 255 else np.iinfo(np.uint16).max)
    return np.clip(image, 0.0, 1.0)


def flatten_illumination(image: np.ndarray, sigma_fraction: float = 0.25) -> np.ndarray:
    """Divide out low-frequency vignetting while preserving local contrast.

    The blur kernel is deliberately large (a quarter of the cell width) so that
    it models the illumination field and not the defects themselves. Division
    rather than subtraction because EL intensity is multiplicative in the
    collection efficiency.
    """
    sigma = max(1.0, sigma_fraction * min(image.shape[:2]))
    background = cv2.GaussianBlur(image, ksize=(0, 0), sigmaX=sigma, sigmaY=sigma)
    # Guard the divide: background is >= 0 and can legitimately reach 0 in a
    # fully dark (completely disconnected) cell.
    background = np.maximum(background, 1e-3)
    flattened = image / background
    return np.clip(flattened / 2.0, 0.0, 1.0)


def enhance_contrast(image: np.ndarray, clip_limit: float = 2.5, grid: int = 8) -> np.ndarray:
    """CLAHE on the cell.

    Global histogram equalisation destroys the intensity relationship between a
    dark crack and its surroundings; CLAHE keeps it local, which is what makes
    hairline cracks visible in dim polycrystalline cells.
    """
    as_uint8 = (np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid, grid))
    return clahe.apply(as_uint8).astype(np.float32) / 255.0


def suppress_grid(image: np.ndarray, kernel_length: int = 15) -> np.ndarray:
    """Attenuate busbars and fingers using morphological line opening.

    We extract the long horizontal and vertical bright structures with
    directional opening, then subtract them. What survives is crack-like:
    short, oriented arbitrarily, and not periodic.
    """
    as_uint8 = (np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)

    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_length, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_length))

    horizontal = cv2.morphologyEx(as_uint8, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(as_uint8, cv2.MORPH_OPEN, vertical_kernel)
    grid = cv2.max(horizontal, vertical)

    residual = cv2.subtract(as_uint8, grid)
    return residual.astype(np.float32) / 255.0


def crack_response(image: np.ndarray) -> np.ndarray:
    """Ridge-like response highlighting dark linear features.

    A black-hat transform responds to structures *darker* than their
    surroundings and smaller than the kernel, which is exactly what a crack or
    an inactive finger region looks like in EL.
    """
    as_uint8 = (np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    blackhat = cv2.morphologyEx(as_uint8, cv2.MORPH_BLACKHAT, kernel)
    # Denoise: EL sensors are read out at high gain and are visibly noisy.
    blackhat = cv2.medianBlur(blackhat, 3)
    return blackhat.astype(np.float32) / 255.0


def preprocess_cell(
    image: np.ndarray,
    size: int = DEFAULT_SIZE,
    build_channels: bool = True,
) -> np.ndarray:
    """Full preprocessing chain for one cell crop.

    Returns ``float32`` of shape ``(size, size, 3)`` in [0, 1], with channels:

    0. contrast-equalised, illumination-flattened cell (what a human inspects)
    1. grid-suppressed residual (crack candidates without busbars)
    2. black-hat crack response (dark linear features)

    Set ``build_channels=False`` to get the equalised single channel replicated
    three ways, which is the ablation baseline for "does the extra physics in
    channels 1-2 actually help?".
    """
    gray = to_grayscale_float(image)
    gray = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA)

    flattened = flatten_illumination(gray)
    equalised = enhance_contrast(flattened)

    if not build_channels:
        return np.stack([equalised] * 3, axis=-1)

    return np.stack(
        [equalised, suppress_grid(equalised), crack_response(equalised)],
        axis=-1,
    )


def estimate_inactive_area_fraction(image: np.ndarray, dark_quantile: float = 0.08) -> float:
    """Fraction of the cell that is electrically inactive (dark in EL).

    This is the one preprocessing output that feeds the *physics* model rather
    than the network: EL intensity is roughly proportional to local minority
    carrier collection, so a persistently dark region is an area contributing
    no photocurrent. We threshold against the cell's own bright population
    instead of an absolute level, because absolute EL counts are not calibrated
    between modules.

    The estimate is deliberately conservative. It is a geometric proxy, not a
    measurement, and ``physics/degradation.py`` treats it as a prior that gets
    blended with the classifier's severity rather than as ground truth.
    """
    gray = to_grayscale_float(image)
    flattened = flatten_illumination(gray)

    # Reference "healthy" brightness = the bright end of this cell's own
    # distribution, which is robust to a large dark defect dragging the mean.
    bright_reference = np.quantile(flattened, 0.90)
    if bright_reference <= 1e-6:
        return 1.0  # the whole cell is dark: fully disconnected

    relative = flattened / bright_reference
    # Areas below ~35% of local peak emission are not meaningfully collecting.
    inactive = relative < 0.35

    # Remove speckle so sensor noise does not inflate the estimate.
    inactive_uint8 = inactive.astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    inactive_uint8 = cv2.morphologyEx(inactive_uint8, cv2.MORPH_OPEN, kernel)

    fraction = float(inactive_uint8.mean())
    # Even a pristine cell has dark busbars; subtract that floor.
    return float(np.clip(fraction - dark_quantile, 0.0, 1.0) / (1.0 - dark_quantile))
