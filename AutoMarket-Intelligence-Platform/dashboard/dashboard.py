"""AutoMarket dashboard.

Run from the project root (after seeding and training):

    streamlit run dashboard/dashboard.py

The dashboard reuses the same database and ML code as the API, so there is
exactly one source of truth for data access and predictions.
"""

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import select

from app.database import engine
from app.ml.predictor import ModelNotTrainedError, get_metrics, predict_price
from app.models import Listing

SERIES_BLUE = "#3987e5"  # validated for the dark theme surface
GRID = "#2c2c2a"
MUTED = "#898781"

st.set_page_config(page_title="AutoMarket Intelligence", page_icon="🚗", layout="wide")


@st.cache_data(ttl=600)
def load_listings() -> pd.DataFrame:
    """Load all listings once and cache them for 10 minutes."""
    df = pd.read_sql(select(Listing), engine)
    df["age"] = date.today().year - df["year"]
    return df


def style(fig):
    """Shared chart look: recessive grid, no chart chrome competing with data."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_family="system-ui, -apple-system, 'Segoe UI', sans-serif",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(gridcolor=GRID, linecolor=GRID, tickfont_color=MUTED),
        yaxis=dict(gridcolor=GRID, linecolor=GRID, tickfont_color=MUTED),
    )
    return fig


df = load_listings()
if df.empty:
    st.error("The database is empty. Run: `python scripts/seed_data.py`")
    st.stop()

st.title("🚗 AutoMarket Intelligence")
st.caption("Used-car market analytics and ML price estimates")

# ---------------------------------------------------------------- sidebar filters
with st.sidebar:
    st.header("Filters")
    makes = st.multiselect("Make", sorted(df["make"].unique()))
    year_min, year_max = int(df["year"].min()), int(df["year"].max())
    years = st.slider("Year", year_min, year_max, (year_min, year_max))
    price_cap = st.slider("Max price (£)", 1000, int(df["price"].max()), int(df["price"].max()))

filtered = df[df["year"].between(*years) & (df["price"] <= price_cap)]
if makes:
    filtered = filtered[filtered["make"].isin(makes)]

overview_tab, explore_tab, estimator_tab = st.tabs(
    ["📊 Market overview", "🔍 Explore listings", "💷 Price estimator"]
)

# ---------------------------------------------------------------- market overview
with overview_tab:
    a, b, c, d = st.columns(4)
    a.metric("Listings", f"{len(filtered):,}")
    b.metric("Average price", f"£{filtered['price'].mean():,.0f}")
    c.metric("Median price", f"£{filtered['price'].median():,.0f}")
    d.metric("Average mileage", f"{filtered['mileage'].mean():,.0f} mi")

    left, right = st.columns(2)

    with left:
        by_make = filtered.groupby("make")["price"].mean().sort_values(ascending=True).reset_index()
        fig = px.bar(
            by_make,
            x="price",
            y="make",
            orientation="h",
            title="Average price by make",
            labels={"price": "Average price (£)", "make": ""},
        )
        fig.update_traces(marker_color=SERIES_BLUE, hovertemplate="%{y}: £%{x:,.0f}<extra></extra>")
        st.plotly_chart(style(fig), use_container_width=True)

    with right:
        by_age = filtered.groupby("age")["price"].mean().reset_index()
        fig = px.line(
            by_age,
            x="age",
            y="price",
            title="Depreciation: average price by vehicle age",
            labels={"age": "Age (years)", "price": "Average price (£)"},
        )
        fig.update_traces(
            line_color=SERIES_BLUE,
            line_width=2,
            hovertemplate="%{x} yrs: £%{y:,.0f}<extra></extra>",
        )
        st.plotly_chart(style(fig), use_container_width=True)

    left2, right2 = st.columns(2)

    with left2:
        fig = px.histogram(
            filtered,
            x="price",
            nbins=40,
            title="Price distribution",
            labels={"price": "Price (£)"},
        )
        fig.update_traces(marker_color=SERIES_BLUE)
        fig.update_layout(yaxis_title="Listings", bargap=0.05)
        st.plotly_chart(style(fig), use_container_width=True)

    with right2:
        sample = filtered.sample(min(1500, len(filtered)), random_state=1)
        fig = px.scatter(
            sample,
            x="mileage",
            y="price",
            title="Mileage vs price",
            labels={"mileage": "Mileage", "price": "Price (£)"},
            hover_data=["make", "model", "year"],
            opacity=0.55,
        )
        fig.update_traces(marker=dict(color=SERIES_BLUE, size=6))
        st.plotly_chart(style(fig), use_container_width=True)

# ---------------------------------------------------------------- explore listings
with explore_tab:
    st.dataframe(
        filtered.drop(columns=["age"]).sort_values("listed_date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(f"{len(filtered):,} listings match the current filters.")

# ---------------------------------------------------------------- price estimator
with estimator_tab:
    st.subheader("What is a fair price for this car?")

    col1, col2 = st.columns(2)
    with col1:
        make = st.selectbox("Make", sorted(df["make"].unique()))
        model = st.selectbox("Model", sorted(df.loc[df["make"] == make, "model"].unique()))
        year = st.slider("Year", year_min, year_max, year_max - 4)
        mileage = st.number_input("Mileage", 0, 300_000, 40_000, step=5_000)
    with col2:
        fuel = st.selectbox("Fuel type", sorted(df["fuel_type"].unique()))
        transmission = st.selectbox("Transmission", sorted(df["transmission"].unique()))
        engine_size = st.slider("Engine size (L)", 0.0, 4.0, 1.5, step=0.1)

    if st.button("Estimate price", type="primary"):
        try:
            estimate = predict_price(
                make=make,
                model=model,
                year=year,
                mileage=mileage,
                fuel_type=fuel,
                transmission=transmission,
                engine_size=engine_size,
            )
            metrics = get_metrics()
        except ModelNotTrainedError:
            st.error("No trained model found. Run: `python -m app.ml.train`")
        else:
            similar = df[(df["make"] == make) & (df["model"] == model)]
            x, y = st.columns(2)
            x.metric("Estimated fair price", f"£{estimate:,}")
            if not similar.empty:
                y.metric(
                    f"Average of {len(similar)} listed {make} {model}s",
                    f"£{similar['price'].mean():,.0f}",
                )
            st.caption(
                f"Model: {metrics['best_model']} · typical error (MAE) "
                f"±£{metrics['test_mae']:,.0f} on unseen test data"
            )
