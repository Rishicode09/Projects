"""YOLO-based defect localisation.

Detection supplies the physics model with measured defect *area* rather than a
severity class mapped through an uncalibrated lookup table -- see
``detector.defect_area_fraction``.
"""

from .dataset import build_yolo_dataset, write_data_yaml
from .detector import (
    Detection,
    defect_area_fraction,
    detect_cells,
    load_detector,
    summarise_module,
    train_detector,
)
from .pseudo_label import CLASS_NAMES, Region, draw_proposals, propose_regions

__all__ = [
    "build_yolo_dataset", "write_data_yaml",
    "Detection", "train_detector", "load_detector", "detect_cells",
    "defect_area_fraction", "summarise_module",
    "propose_regions", "draw_proposals", "Region", "CLASS_NAMES",
]
