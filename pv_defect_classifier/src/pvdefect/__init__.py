"""EL defect detection with a physics-based power-loss model.

Three stages that meet in the physics:

* ``preprocess`` -- OpenCV module-array cropping and EL-specific cell
  enhancement.
* ``models`` / ``detection`` -- a binary functional/cracked classifier
  (torchvision ResNet-50 / EfficientNet) and a YOLO detector that localises
  defects and measures their area.
* ``physics`` -- a pvlib/SciPy single-diode simulation turning defect geometry
  into module power loss and annual energy loss for a real site.

The join lives in ``physics.degradation``, the only place where a visual defect
becomes an electrical parameter, and the only place needing calibration against
measured IV data.
"""

__version__ = "0.2.0"
