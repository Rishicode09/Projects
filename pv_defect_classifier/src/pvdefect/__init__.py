"""EL defect classification with a physics-based power-loss model.

Two halves that meet in the middle:

* ``data`` / ``preprocess`` / ``models`` — an ordinal CNN that grades
  electroluminescence cell images on the ELPV four-level severity scale.
* ``physics`` — a pvlib/scipy single-diode simulation that turns those grades
  into module power loss and annual energy loss for a real site.

The join lives in ``physics.degradation``, which is the only place where a
visual severity becomes an electrical parameter, and the only place that needs
calibration against measured IV data.
"""

__version__ = "0.1.0"
