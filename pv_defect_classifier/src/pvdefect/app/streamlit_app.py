"""Streamlit front end: EL image in, euros per year out.

    streamlit run src/pvdefect/app/streamlit_app.py

Three tabs, matching the three questions a research group actually asks of this
pipeline:

1. **Inspect a cell** — what does the model see, and where is it looking?
2. **Module simulation** — given a module's worth of severities, what does the
   I-V curve and the annual energy look like?
3. **Sensitivity** — how much does the answer move when the uncalibrated
   degradation coefficients move? (Usually: a lot. That is the point.)

The app runs without a trained checkpoint; the model tab degrades to manual
severity sliders so the physics half stays explorable on its own.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# Allow `streamlit run src/pvdefect/app/streamlit_app.py` from the repo root.
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pvdefect.data.elpv import CLASS_NAMES, NUM_CLASSES  # noqa: E402
from pvdefect.physics.cell_model import ModuleSpec, cell_parameters_at_conditions  # noqa: E402
from pvdefect.physics.degradation import DegradationModel  # noqa: E402
from pvdefect.physics.energy import revenue_impact, simulate_annual_energy  # noqa: E402
from pvdefect.physics.mismatch import iv_curve, solve_maximum_power_point  # noqa: E402
from pvdefect.physics.weather import (  # noqa: E402
    SiteSpec,
    plane_of_array,
    typical_meteorological_year,
)

st.set_page_config(page_title="PV Defect → Power Loss", page_icon="☀", layout="wide")


# --------------------------------------------------------------------------
# Cached resources
# --------------------------------------------------------------------------

@st.cache_resource(show_spinner="Loading model…")
def load_model(checkpoint_path: str):
    """Load a trained checkpoint, or return ``None`` if there isn't one.

    Torch is imported lazily so the physics tabs stay usable on a machine
    without it installed.
    """
    path = Path(checkpoint_path)
    if not path.exists():
        return None, None

    import torch

    from pvdefect.config import Config
    from pvdefect.models.classifier import build_model

    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    config = Config.from_dict(checkpoint["config"])
    model = build_model(config.model)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model, checkpoint.get("val_metrics", {})


@st.cache_data(show_spinner="Fetching weather…")
def load_weather(site_dict: dict, use_network: bool) -> pd.DataFrame:
    site = SiteSpec(**site_dict)
    weather = typical_meteorological_year(site, use_network=use_network)
    return plane_of_array(site, weather)


@st.cache_data(show_spinner="Running annual simulation…")
def run_simulation(
    severities: tuple[float, ...],
    poa: pd.DataFrame,
    module_dict: dict,
    degradation_dict: dict,
):
    module = ModuleSpec(**module_dict)
    degradation = DegradationModel(**degradation_dict)
    return simulate_annual_energy(np.array(severities), poa, module, degradation)


# --------------------------------------------------------------------------
# Sidebar: site, module, degradation assumptions
# --------------------------------------------------------------------------

st.sidebar.title("Configuration")

st.sidebar.subheader("Site")
site_dict = {
    "name": st.sidebar.text_input("Site name", "Erlangen, DE"),
    "latitude": st.sidebar.number_input("Latitude", -90.0, 90.0, 49.60, format="%.4f"),
    "longitude": st.sidebar.number_input("Longitude", -180.0, 180.0, 11.01, format="%.4f"),
    "altitude": st.sidebar.number_input("Altitude (m)", 0.0, 5000.0, 280.0),
    "timezone": st.sidebar.text_input("Timezone", "Europe/Berlin"),
    "surface_tilt": st.sidebar.slider("Tilt (deg)", 0.0, 90.0, 30.0),
    "surface_azimuth": st.sidebar.slider("Azimuth (deg, 180 = S)", 0.0, 360.0, 180.0),
    "albedo": 0.20,
}
use_network = st.sidebar.checkbox(
    "Fetch PVGIS TMY", value=False,
    help="Off = synthetic clear-sky year (no network, but over-estimates yield).",
)

st.sidebar.subheader("Module")
module_dict = dict(
    ModuleSpec.default().__dict__,
    cells_in_series=st.sidebar.selectbox("Cells in series", [60, 72], index=0),
    bypass_diode_count=st.sidebar.selectbox("Bypass diodes", [1, 2, 3, 4, 6], index=2),
)

st.sidebar.subheader("Degradation model")
st.sidebar.caption(
    "Uncalibrated — these coefficients set how a visual severity becomes an "
    "electrical fault. Fit them against flash-test data before trusting absolute watts."
)
severity_scale = st.sidebar.slider(
    "Severity → damage scaling", 0.25, 2.0, 1.0, 0.05,
    help="1.0 = literature-plausible defaults. Sweep it to bracket the answer.",
)
degradation_model = DegradationModel().with_uncertainty(severity_scale)
degradation_dict = degradation_model.__dict__.copy()

tariff = st.sidebar.number_input("Tariff (currency/kWh)", 0.0, 1.0, 0.12, format="%.3f")
checkpoint_path = st.sidebar.text_input("Checkpoint", "artifacts/model.pt")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

st.title("PV defect classifier → power loss")
st.caption(
    "Electroluminescence cell grading (ELPV / PyTorch) coupled to a single-diode "
    "mismatch simulation (pvlib / SciPy)."
)

model, val_metrics = load_model(checkpoint_path)
if model is None:
    st.info(
        f"No checkpoint at `{checkpoint_path}` — the physics tabs work regardless, and "
        "the inspection tab falls back to manual severities. Train one with "
        "`python -m pvdefect.train`.",
        icon="ℹ",
    )

inspect_tab, module_tab, sensitivity_tab = st.tabs(
    ["Inspect a cell", "Module simulation", "Sensitivity"]
)


with inspect_tab:
    st.subheader("Cell inspection")
    uploaded = st.file_uploader(
        "Electroluminescence cell crop", type=["png", "jpg", "jpeg", "tif", "tiff"]
    )

    if uploaded is None:
        st.write("Upload a 300×300 EL cell crop from the ELPV dataset, or any single-cell EL image.")
    else:
        import cv2

        from pvdefect.preprocess.cell_prep import (
            estimate_inactive_area_fraction,
            preprocess_cell,
        )

        raw = cv2.imdecode(
            np.frombuffer(uploaded.getvalue(), np.uint8), cv2.IMREAD_UNCHANGED
        )
        if raw is None:
            st.error("Could not decode that image.")
        else:
            processed = preprocess_cell(raw)
            inactive = estimate_inactive_area_fraction(raw)

            columns = st.columns(4)
            columns[0].image(
                raw, caption="Raw EL", use_container_width=True, clamp=True
            )
            for i, title in enumerate(
                ["Equalised", "Grid-suppressed", "Crack response"]
            ):
                columns[i + 1].image(
                    processed[..., i], caption=title, use_container_width=True, clamp=True
                )

            st.metric("Estimated inactive area", f"{inactive:.1%}")

            if model is not None:
                import torch

                from pvdefect.explain import GradCam, overlay_heatmap

                tensor = torch.from_numpy(processed.transpose(2, 0, 1)).unsqueeze(0).float()
                with torch.no_grad():
                    prediction = model.predict(tensor)

                severity = float(prediction["severity"][0])
                predicted_class = int(prediction["label"][0])
                probabilities = prediction["probabilities"][0].numpy()

                left, right = st.columns([1, 1])
                with left:
                    st.metric("Predicted class", CLASS_NAMES[predicted_class])
                    st.metric("Expected severity", f"{severity:.3f}")
                    st.bar_chart(
                        pd.DataFrame({"probability": probabilities}, index=list(CLASS_NAMES))
                    )
                with right:
                    with GradCam(model) as cam:
                        heatmap = cam(tensor, level=max(0, predicted_class - 1))
                    st.image(
                        overlay_heatmap(processed, heatmap),
                        caption="Grad-CAM — check it points at the defect, not the frame",
                        use_container_width=True,
                    )

                st.session_state["last_severity"] = severity
                st.session_state["last_inactive"] = inactive


with module_tab:
    st.subheader("Module-level simulation")
    n_cells = int(module_dict["cells_in_series"])

    st.write(
        "Set the severity of each cell in the string. One badly damaged cell limits "
        "the whole series string — that is the effect this simulation exists to capture."
    )

    preset = st.selectbox(
        "Preset",
        [
            "All healthy",
            "One severe cell",
            "One substring damaged",
            "Scattered mild cracking",
            "Uniform moderate degradation",
        ],
    )

    severities = np.zeros(n_cells)
    if preset == "One severe cell":
        severities[n_cells // 2] = 1.0
    elif preset == "One substring damaged":
        severities[: max(1, n_cells // int(module_dict["bypass_diode_count"]))] = 1.0
    elif preset == "Scattered mild cracking":
        rng = np.random.default_rng(0)
        severities[rng.choice(n_cells, size=max(1, n_cells // 5), replace=False)] = 1 / 3
    elif preset == "Uniform moderate degradation":
        severities[:] = 2 / 3

    worst = st.slider("Override: severity of the worst cell", 0.0, 1.0,
                      float(severities.max()), 1 / 3)
    if worst != float(severities.max()):
        severities[int(np.argmax(severities)) if severities.max() > 0 else 0] = worst

    st.caption(
        "Cell severities: "
        + "  ".join(
            f"{CLASS_NAMES[i]}={int(np.sum(np.round(severities * 3) == i))}"
            for i in range(NUM_CLASSES)
        )
    )

    if st.button("Run annual simulation", type="primary"):
        poa = load_weather(site_dict, use_network)
        result = run_simulation(tuple(severities), poa, module_dict, degradation_dict)

        if poa.attrs.get("synthetic", True):
            st.warning(
                "Synthetic clear-sky weather: relative losses are meaningful, absolute "
                "yield is over-stated because there are no clouds.",
                icon="⚠",
            )

        metrics = st.columns(4)
        metrics[0].metric("STC power loss", f"{result.stc_power_loss_fraction:.2%}")
        metrics[1].metric("Annual energy loss", f"{result.annual_energy_loss_fraction:.2%}")
        metrics[2].metric("Energy lost", f"{result.annual_energy_loss_kwh:.1f} kWh/yr")
        impact = revenue_impact(result, 1, tariff, years=10)
        metrics[3].metric("Revenue lost (10 yr)", f"{impact['cumulative_revenue_loss']:.0f}")

        st.caption(
            f"Healthy module: {result.stc_power_healthy_w:.1f} W at STC, "
            f"{result.annual_energy_healthy_kwh:.0f} kWh/yr. "
            f"Weather: {result.weather_source}."
        )

        module = ModuleSpec(**module_dict)
        perturbation = degradation_model.perturb(severities)
        healthy_parameters = cell_parameters_at_conditions(module, 1000.0, 25.0)
        defective_parameters = cell_parameters_at_conditions(
            module, 1000.0, 25.0,
            photocurrent_scale=perturbation["photocurrent_scale"],
            series_resistance_gain=perturbation["series_resistance_gain"],
            shunt_resistance_retention=perturbation["shunt_resistance_retention"],
        )

        left, right = st.columns(2)
        with left:
            st.markdown("**I-V curve at STC**")
            i_h, v_h, _ = iv_curve(healthy_parameters, module)
            i_d, v_d, _ = iv_curve(defective_parameters, module)
            st.line_chart(
                pd.DataFrame({"healthy": i_h, "defective": np.interp(v_h, v_d[::-1], i_d[::-1])},
                             index=pd.Index(v_h, name="Voltage (V)"))
            )
        with right:
            st.markdown("**P-V curve at STC**")
            st.line_chart(
                pd.DataFrame(
                    {"healthy": v_h * i_h,
                     "defective": v_h * np.interp(v_h, v_d[::-1], i_d[::-1])},
                    index=pd.Index(v_h, name="Voltage (V)"),
                )
            )

        operating_point = solve_maximum_power_point(defective_parameters, module)
        if operating_point.bypassed_substrings:
            st.info(
                f"{operating_point.bypassed_substrings} substring(s) bypassed at MPP — "
                "the diode is protecting the module, and the loss curve flattens from here.",
                icon="🔌",
            )

        st.markdown("**Where the energy is lost**")
        hourly = result.hourly.copy()
        hourly["month"] = hourly.index.month
        monthly = hourly.groupby("month")[["power_healthy_w", "power_loss_w"]].sum() / 1000.0
        monthly.columns = ["healthy kWh", "lost kWh"]
        st.bar_chart(monthly)

        st.caption(
            "Loss binned by irradiance shows which mechanism dominates: series-resistance "
            "damage concentrates the loss in bright hours, shunts in dim ones."
        )
        bins = pd.cut(hourly["effective_irradiance"], [0, 200, 400, 600, 800, 1100])
        by_irradiance = hourly.groupby(bins, observed=True)["power_loss_w"].sum() / 1000.0
        st.bar_chart(by_irradiance.rename("kWh lost"))


with sensitivity_tab:
    st.subheader("How much does the uncalibrated model matter?")
    st.write(
        "The severity→damage mapping is the one part of this pipeline with no measured "
        "backing. This sweep shows the spread of answers it produces. If the spread is "
        "wider than the decision you are trying to make, calibrate before deciding."
    )

    n_cells = int(module_dict["cells_in_series"])
    n_defective = st.slider("Number of severe cells", 0, n_cells, 1)

    if st.button("Sweep", type="primary"):
        poa = load_weather(site_dict, use_network)
        severities = np.zeros(n_cells)
        if n_defective:
            severities[:n_defective] = 1.0

        rows = []
        scales = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
        progress = st.progress(0.0)
        for i, scale in enumerate(scales):
            model_variant = DegradationModel().with_uncertainty(scale)
            result = run_simulation(
                tuple(severities), poa, module_dict, model_variant.__dict__.copy()
            )
            rows.append(
                {
                    "damage scaling": scale,
                    "STC loss %": 100 * result.stc_power_loss_fraction,
                    "annual loss %": 100 * result.annual_energy_loss_fraction,
                    "kWh lost/yr": result.annual_energy_loss_kwh,
                }
            )
            progress.progress((i + 1) / len(scales))

        table = pd.DataFrame(rows).set_index("damage scaling")
        st.dataframe(table.style.format("{:.2f}"), use_container_width=True)
        st.line_chart(table[["STC loss %", "annual loss %"]])

        span = table["annual loss %"].max() - table["annual loss %"].min()
        st.metric("Spread across assumptions", f"{span:.1f} percentage points")
