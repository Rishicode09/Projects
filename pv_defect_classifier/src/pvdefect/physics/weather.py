"""Weather and plane-of-array irradiance via pvlib.

A note on where the data comes from, because it is easy to conflate the two
datasets in this project: **ELPV contains no weather information whatsoever.**
It is a set of electroluminescence images taken in a darkened lab with the
module driven by an external current source — there is no sun involved. All
meteorological input comes from pvlib: either a PVGIS typical meteorological
year for the plant's actual coordinates, or a synthetic clear-sky year when
the machine is offline.

The two are joined only at the end: ELPV tells us the *condition* of the cells,
the TMY tells us the *conditions they operate under*, and the energy model
multiplies them out over 8,760 hours.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
import pvlib
from pvlib.location import Location

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SiteSpec:
    """Plant location and array geometry."""

    name: str = "Erlangen, DE"
    latitude: float = 49.60
    longitude: float = 11.01
    altitude: float = 280.0
    timezone: str = "Europe/Berlin"
    surface_tilt: float = 30.0
    surface_azimuth: float = 180.0  # south-facing
    albedo: float = 0.20

    def location(self) -> Location:
        return Location(
            self.latitude, self.longitude, tz=self.timezone,
            altitude=self.altitude, name=self.name,
        )


def clear_sky_year(site: SiteSpec, year: int = 2021) -> pd.DataFrame:
    """Synthetic clear-sky year — the offline fallback.

    Uses the Ineichen model with pvlib's bundled Linke turbidity climatology,
    so it needs no network. It systematically *over*-estimates annual energy
    because it has no clouds; use it for relative comparisons (defective vs
    healthy), never for an absolute yield claim.
    """
    location = site.location()
    times = pd.date_range(
        f"{year}-01-01 00:30", f"{year}-12-31 23:30", freq="1h", tz=site.timezone
    )

    clearsky = location.get_clearsky(times, model="ineichen")

    # A crude but defensible ambient temperature: sinusoidal seasonal swing
    # plus a diurnal swing driven by solar elevation. Real TMY data is far
    # better; this exists so the pipeline runs on a plane.
    day_of_year = times.dayofyear.to_numpy()
    seasonal = 10.0 + 12.0 * np.sin(2 * np.pi * (day_of_year - 100) / 365.25)
    solar_position = location.get_solarposition(times)
    diurnal = 6.0 * np.clip(np.sin(np.radians(solar_position["elevation"].to_numpy())), 0, None)

    weather = pd.DataFrame(
        {
            "ghi": clearsky["ghi"],
            "dni": clearsky["dni"],
            "dhi": clearsky["dhi"],
            "temp_air": seasonal + diurnal,
            "wind_speed": np.full(len(times), 2.0),
        },
        index=times,
    )
    logger.info("Generated synthetic clear-sky year for %s (%d hours)", site.name, len(weather))
    return weather


def typical_meteorological_year(site: SiteSpec, use_network: bool = True) -> pd.DataFrame:
    """Fetch a PVGIS TMY, falling back to clear sky if the network is unavailable.

    PVGIS covers Europe, Africa, most of Asia and the Americas. For sites it
    does not cover, or behind a restrictive proxy, you will silently get the
    clear-sky fallback — check the ``synthetic`` attribute on the result.
    """
    if use_network:
        try:
            data, _, _, _ = pvlib.iotools.get_pvgis_tmy(
                latitude=site.latitude,
                longitude=site.longitude,
                map_variables=True,
                timeout=30,
            )
            data = data.tz_convert(site.timezone)
            data = data.rename(columns={"temp_air": "temp_air", "wind_speed": "wind_speed"})
            required = {"ghi", "dni", "dhi", "temp_air", "wind_speed"}
            missing = required - set(data.columns)
            if missing:
                raise ValueError(f"PVGIS response missing columns: {sorted(missing)}")

            data.attrs["synthetic"] = False
            data.attrs["source"] = "PVGIS TMY"
            logger.info("Fetched PVGIS TMY for %s (%d hours)", site.name, len(data))
            return data
        except Exception as exc:
            logger.warning("PVGIS fetch failed (%s); using synthetic clear-sky year", exc)

    fallback = clear_sky_year(site)
    fallback.attrs["synthetic"] = True
    fallback.attrs["source"] = "pvlib Ineichen clear-sky (synthetic)"
    return fallback


def plane_of_array(site: SiteSpec, weather: pd.DataFrame) -> pd.DataFrame:
    """Transpose horizontal irradiance to the tilted array plane.

    Returns a frame with ``effective_irradiance`` (what the cells actually see,
    after the incidence-angle modifier) and ``cell_temperature``. These two
    columns are the entire interface between the weather model and the
    electrical model.
    """
    location = site.location()
    solar_position = location.get_solarposition(weather.index)

    total_irradiance = pvlib.irradiance.get_total_irradiance(
        surface_tilt=site.surface_tilt,
        surface_azimuth=site.surface_azimuth,
        solar_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"],
        dni=weather["dni"],
        ghi=weather["ghi"],
        dhi=weather["dhi"],
        albedo=site.albedo,
        model="haydavies",
        dni_extra=pvlib.irradiance.get_extra_radiation(weather.index),
    )

    # Reflection losses at glancing incidence: real, and biased toward morning
    # and evening hours, which is when the shunt mechanism dominates.
    aoi = pvlib.irradiance.aoi(
        site.surface_tilt, site.surface_azimuth,
        solar_position["apparent_zenith"], solar_position["azimuth"],
    )
    iam = pvlib.iam.ashrae(aoi)

    effective = (
        total_irradiance["poa_direct"] * iam + total_irradiance["poa_diffuse"]
    ).clip(lower=0.0)

    cell_temperature = pvlib.temperature.sapm_cell(
        poa_global=total_irradiance["poa_global"],
        temp_air=weather["temp_air"],
        wind_speed=weather["wind_speed"],
        **pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]["open_rack_glass_glass"],
    )

    result = pd.DataFrame(
        {
            "poa_global": total_irradiance["poa_global"],
            "effective_irradiance": effective,
            "cell_temperature": cell_temperature,
            "temp_air": weather["temp_air"],
        },
        index=weather.index,
    )
    result.attrs.update(weather.attrs)
    return result
