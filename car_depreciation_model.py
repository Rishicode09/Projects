import warnings

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.optimize import curve_fit
from scipy.ndimage import uniform_filter1d
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from typing import Tuple, Dict, Optional

# ============================================================================
# 1. DATA GENERATION (simulating realistic market data)
# ============================================================================
def generate_depreciation_data(
    max_age: int = 11,
    transition_age: float = 3.0,
    seed: int = 42
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate synthetic car depreciation data with realistic noise.

    Args:
        max_age: Oldest age (years) to generate.
        transition_age: Age at which the true depreciation rate changes.
        seed: Seed for the random number generator.

    Returns:
        years: Age in years (0 to max_age)
        mileage: Cumulative mileage in 10k miles
        prices: Average market price in GBP
    """
    rng = np.random.default_rng(seed)
    years = np.arange(0, max_age + 1, 1)
    # Typical annual mileage: 10k-12k miles -> 1.0-1.2 (10k units)
    annual_mileage = rng.uniform(0.9, 1.3, size=len(years))
    # A brand-new car has zero miles on it: mileage accrues *during* each year,
    # so year 0 must start at 0 rather than at one year's worth of driving.
    annual_mileage[0] = 0.0
    mileage = np.cumsum(annual_mileage)  # cumulative mileage

    # True underlying model (unknown to the fitting routine).
    # This is a genuine two-phase curve, so k2 is identifiable from the data.
    true_V0 = 18500
    true_k1 = 0.28   # early rapid decay
    true_k2 = 0.12   # later slower decay
    true_b = 0.08    # mileage penalty per 10k miles
    true_rate = np.where(
        years <= transition_age,
        true_k1 * years,
        true_k1 * transition_age + true_k2 * (years - transition_age)
    )
    true_prices = true_V0 * np.exp(-true_rate) * np.exp(-true_b * mileage)
    # Add realistic noise (heteroscedastic: larger variance at higher prices)
    noise = rng.normal(0, 0.05 * true_prices)
    prices = np.maximum(true_prices + noise, 1000)  # floor at £1000
    return years, mileage, prices


# ============================================================================
# 2. DEPRECIATION MODEL (continuous, physics-inspired)
# ============================================================================
class CarDepreciationModel:
    """
    Continuous double-phase exponential depreciation with mileage penalty.

    Model form:
        V(t, m) = V0 * exp(-k1 * t) * exp(-b * m)   for t <= t0
        V(t, m) = V0 * exp(-k1*t0 - k2*(t-t0)) * exp(-b * m)   for t > t0
    where t0 is a transition age (fixed at 3 years in this implementation).
    The function is continuous and smooth at t0.
    """

    N_PARAMS = 4
    DEFAULT_BOUNDS = ([10000, 0.15, 0.05, 0.01], [30000, 0.45, 0.25, 0.20])

    def __init__(self, transition_age: float = 3.0):
        """
        Args:
            transition_age: Age (years) where depreciation rate changes.
        """
        self.transition_age = transition_age
        self.params_: Optional[Dict[str, float]] = None
        self.covariance_: Optional[np.ndarray] = None
        self.bounds_: Optional[Tuple] = None
        self.metrics_: Dict = {}
        self.years_train_: Optional[np.ndarray] = None
        self.mileage_train_: Optional[np.ndarray] = None
        self.prices_train_: Optional[np.ndarray] = None

    def _model_func(self, x: Tuple[np.ndarray, np.ndarray], V0: float, k1: float, k2: float, b: float) -> np.ndarray:
        """Underlying model function for curve fitting."""
        t, m = x
        # Continuous decay: piecewise exponent with matching at transition_age
        rate = np.where(
            t <= self.transition_age,
            k1 * t,
            k1 * self.transition_age + k2 * (t - self.transition_age)
        )
        return V0 * np.exp(-rate) * np.exp(-b * m)

    def _initial_guess(self, prices: np.ndarray, bounds: Tuple) -> np.ndarray:
        """Build a starting guess that is guaranteed to lie strictly inside the bounds."""
        lower = np.asarray(bounds[0], dtype=float)
        upper = np.asarray(bounds[1], dtype=float)
        p0 = np.array([prices[0], 0.28, 0.12, 0.08], dtype=float)
        # curve_fit rejects an initial guess that sits outside (or exactly on) the
        # bounds, which happens whenever the first observed price falls outside
        # the V0 range. Pull the guess just inside instead of crashing.
        margin = 1e-6 * (upper - lower)
        return np.clip(p0, lower + margin, upper - margin)

    @staticmethod
    def _warn_if_pinned(popt: np.ndarray, bounds: Tuple, param_names) -> None:
        """
        Warn when an optimum sits on a bound.

        A parameter resting exactly on its bound was not estimated from the
        data: the optimiser wanted to go further and the constraint stopped it.
        Reporting such a value as a fitted quantity is misleading, so it is
        flagged rather than returned silently. With cumulative mileage nearly
        proportional to age this is common, because the age and mileage terms
        become hard to tell apart.
        """
        lower = np.asarray(bounds[0], dtype=float)
        upper = np.asarray(bounds[1], dtype=float)
        tol = 1e-6 * (upper - lower)
        pinned = [
            name for name, value, lo, hi, t in zip(param_names, popt, lower, upper, tol)
            if value <= lo + t or value >= hi - t
        ]
        if pinned:
            warnings.warn(
                f"Parameter(s) {', '.join(pinned)} converged onto a fitting bound. "
                f"These values are constrained, not estimated, and should not be "
                f"interpreted as depreciation rates.",
                RuntimeWarning,
                stacklevel=3
            )

    def fit(self, years: np.ndarray, mileage: np.ndarray, prices: np.ndarray,
            bounds: Optional[Tuple] = None) -> 'CarDepreciationModel':
        """
        Fit model parameters using non-linear least squares.

        Args:
            years: Age in years
            mileage: Cumulative mileage (same units as used in training)
            prices: Observed market prices
            bounds: (lower_bounds, upper_bounds) for (V0, k1, k2, b)
        """
        if bounds is None:
            # Industry-informed bounds: V0 (10k-30k), k1 (0.15-0.45), k2 (0.05-0.25), b (0.01-0.20)
            bounds = self.DEFAULT_BOUNDS
        self.bounds_ = bounds

        years = np.asarray(years, dtype=float)
        mileage = np.asarray(mileage, dtype=float)
        prices = np.asarray(prices, dtype=float)

        if len(years) < self.N_PARAMS:
            raise ValueError(
                f"Need at least {self.N_PARAMS} observations to fit "
                f"{self.N_PARAMS} parameters, got {len(years)}."
            )

        # Initial guess (reasonable starting point, clipped inside the bounds)
        p0 = self._initial_guess(prices, bounds)

        popt, self.covariance_ = curve_fit(
            self._model_func,
            (years, mileage),
            prices,
            p0=p0,
            bounds=bounds,
            maxfev=10000
        )

        # Store parameters as dictionary for clarity
        param_names = ['V0', 'k1', 'k2', 'b']
        self.params_ = dict(zip(param_names, popt))
        self._warn_if_pinned(popt, bounds, param_names)

        # Compute in-sample metrics
        pred = self.predict(years, mileage)
        residuals = prices - pred
        self.metrics_ = {
            'R2': 1 - np.sum(residuals**2) / np.sum((prices - np.mean(prices))**2),
            'MAE': mean_absolute_error(prices, pred),
            'MAPE': mean_absolute_percentage_error(prices, pred) * 100,
            'RMSE': np.sqrt(np.mean(residuals**2))
        }
        # Store training data for predict_with_uncertainty (for residuals calculation)
        self.years_train_ = years
        self.mileage_train_ = mileage
        self.prices_train_ = prices
        return self

    def predict(self, years: np.ndarray, mileage: np.ndarray) -> np.ndarray:
        """
        Return point predictions.

        Args:
            years: Array of years for prediction.
            mileage: Array of mileage for prediction.

        Returns:
            np.ndarray: Predicted prices.
        """
        if self.params_ is None:
            raise RuntimeError("Model must be fitted before predict()")
        years = np.atleast_1d(np.asarray(years, dtype=float))
        mileage = np.atleast_1d(np.asarray(mileage, dtype=float))
        return self._model_func(
            (years, mileage),
            self.params_['V0'], self.params_['k1'],
            self.params_['k2'], self.params_['b']
        )

    def predict_with_uncertainty(
        self, years: np.ndarray, mileage: np.ndarray,
        n_bootstrap: int = 500, confidence: float = 0.90,
        random_state: Optional[int] = None
    ) -> Dict[str, np.ndarray]:
        """
        Generate prediction intervals using bootstrap on residuals.

        This accounts for both parameter uncertainty (by refitting the model on
        resampled residuals) and residual noise (by adding a fresh residual draw
        to each bootstrap curve). Omitting the second step would yield a
        confidence interval for the mean curve, which is materially narrower
        than a prediction interval for an individual car.

        Args:
            years: Array of years for prediction.
            mileage: Array of mileage for prediction.
            n_bootstrap: Number of bootstrap iterations.
            confidence: Confidence level for the prediction interval (e.g., 0.90 for 90%).
            random_state: Seed for the bootstrap RNG, so intervals are reproducible.

        Returns:
            Dict[str, np.ndarray]: A dictionary containing 'mean' predictions,
            'lower' bound, 'upper' bound, and 'confidence' level.
        """
        if self.params_ is None:
            raise RuntimeError("Model must be fitted first")
        if self.prices_train_ is None or self.years_train_ is None or self.mileage_train_ is None:
            raise RuntimeError("Model training data (years, mileage, prices) not stored.")

        years = np.atleast_1d(np.asarray(years, dtype=float))
        mileage = np.atleast_1d(np.asarray(mileage, dtype=float))
        rng = np.random.default_rng(random_state)

        # Point predictions for the input years/mileage (can be future data)
        pred_mean = self.predict(years, mileage)

        # Obtain in-sample residuals (fitted on the original training data)
        # These residuals are used for bootstrapping the noise component
        train_pred_on_train_data = self.predict(self.years_train_, self.mileage_train_)
        residuals = self.prices_train_ - train_pred_on_train_data

        # Bootstrap: generate new residuals by sampling with replacement
        n_points_train = len(self.years_train_)

        # In-sample residuals are systematically smaller than the true errors,
        # because fitting four free parameters lets the curve bend towards the
        # noise. Rescaling by sqrt(n / (n - p)) restores the correct spread;
        # without it the intervals below come out far too narrow.
        dof = n_points_train - self.N_PARAMS
        if dof <= 0:
            raise ValueError(
                f"Cannot bootstrap with {n_points_train} training points and "
                f"{self.N_PARAMS} parameters: no residual degrees of freedom."
            )

        # Price noise scales with price: a £20k car is off by hundreds, a £1.5k
        # car by tens. Resampling absolute residuals across all price levels
        # therefore produces intervals that are far too narrow for new cars and
        # far too wide for old ones. Resample proportional residuals instead, so
        # each drawn error is rescaled to the price level it is applied to.
        rel_residuals = (residuals / train_pred_on_train_data) * np.sqrt(n_points_train / dof)
        n_points_predict = len(years)  # For the predicted range
        p0 = [self.params_['V0'], self.params_['k1'], self.params_['k2'], self.params_['b']]

        pred_bootstrap = []
        for _ in range(n_bootstrap):
            # Sample residuals for the training data (same size as original training data)
            resampled_resid = rng.choice(rel_residuals, size=n_points_train, replace=True)
            # Create a bootstrapped version of the training prices
            y_boot = train_pred_on_train_data * (1.0 + resampled_resid)

            # Refit model on bootstrapped data (using original training years/mileage)
            try:
                boot_params, _ = curve_fit(
                    self._model_func,
                    (self.years_train_, self.mileage_train_),
                    y_boot,
                    p0=p0,
                    bounds=self.bounds_,
                    maxfev=5000
                )
            except (RuntimeError, ValueError):
                # If curve_fit fails for a bootstrap sample, skip it
                continue

            # Predict on the *target* years/mileage for uncertainty estimation
            boot_curve = self._model_func((years, mileage), *boot_params)
            # Add an independent noise draw so the interval covers an individual
            # observation, not just the fitted mean.
            boot_pred = boot_curve * (
                1.0 + rng.choice(rel_residuals, size=n_points_predict, replace=True)
            )
            pred_bootstrap.append(boot_pred)

        if not pred_bootstrap:
            # Handle case where all bootstrap fits failed
            print("Warning: All bootstrap fits failed. Returning point prediction with no interval.")
            return {
                'mean': pred_mean,
                'lower': pred_mean,
                'upper': pred_mean,
                'confidence': confidence
            }

        pred_bootstrap = np.array(pred_bootstrap)
        # Ensure the bootstrapped predictions have the same size as the input 'years'
        if pred_bootstrap.shape[1] != n_points_predict:
            raise ValueError(f"Bootstrapped prediction shape mismatch. Expected {n_points_predict}, got {pred_bootstrap.shape[1]}")

        lower = np.percentile(pred_bootstrap, (1 - confidence) / 2 * 100, axis=0)
        upper = np.percentile(pred_bootstrap, (1 + confidence) / 2 * 100, axis=0)

        return {
            'mean': pred_mean,
            'lower': lower,
            'upper': upper,
            'confidence': confidence
        }

    def cross_validate(self, years: np.ndarray, mileage: np.ndarray, prices: np.ndarray,
                       n_splits: int = 5) -> Dict[str, float]:
        """
        Time series cross-validation to estimate real-world generalisation error.

        Folds whose training window is too small to identify all four parameters
        are skipped rather than fitted, since such a fit is unconstrained and
        would contribute a meaningless score to the average.

        Returns:
            Dictionary with mean and std of MAPE across test folds.
        """
        years = np.asarray(years, dtype=float)
        mileage = np.asarray(mileage, dtype=float)
        prices = np.asarray(prices, dtype=float)

        tscv = TimeSeriesSplit(n_splits=n_splits)
        mape_scores = []
        mae_scores = []
        n_skipped = 0

        for train_idx, test_idx in tscv.split(years):
            if len(train_idx) < self.N_PARAMS:
                n_skipped += 1
                continue

            # Train on expanding window
            years_train, miles_train = years[train_idx], mileage[train_idx]
            prices_train = prices[train_idx]
            # Fit a fresh model on this fold
            fold_model = CarDepreciationModel(transition_age=self.transition_age)
            fold_model.fit(years_train, miles_train, prices_train, bounds=self.bounds_)

            # Predict on test
            years_test, miles_test = years[test_idx], mileage[test_idx]
            prices_test = prices[test_idx]
            pred_test = fold_model.predict(years_test, miles_test)

            mape_scores.append(mean_absolute_percentage_error(prices_test, pred_test) * 100)
            mae_scores.append(mean_absolute_error(prices_test, pred_test))

        if not mape_scores:
            raise ValueError(
                f"All {n_splits} CV folds had fewer than {self.N_PARAMS} training points. "
                f"Reduce n_splits or provide more data."
            )
        if n_skipped:
            print(f"Note: skipped {n_skipped} CV fold(s) with too few training points.")

        return {
            'cv_MAPE_mean': np.mean(mape_scores),
            'cv_MAPE_std': np.std(mape_scores),
            'cv_MAE_mean': np.mean(mae_scores),
            'cv_MAE_std': np.std(mae_scores),
            'cv_n_folds': len(mape_scores)
        }


# ============================================================================
# 3. VISUALISATION (professional, publication-ready)
# ============================================================================
def plot_depreciation_analysis(
    model: CarDepreciationModel,
    years: np.ndarray,
    mileage: np.ndarray,
    prices: np.ndarray,
    future_years: np.ndarray,
    future_mileage: np.ndarray,
    cv_scores: Dict[str, float],
    random_state: Optional[int] = None
) -> None:
    """Create a comprehensive 2x2 figure with fit, residuals, uncertainty, and parameters."""

    sns.set_style("whitegrid")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # ---- Panel 1: Model fit with uncertainty (historical + future) ----
    ax = axes[0, 0]
    # Historical data
    ax.scatter(years, prices, color='black', s=60, zorder=5, label='Market data')
    # Historical fit
    years_cont = np.linspace(0, max(years), 100)
    mile_cont = np.interp(years_cont, years, mileage)  # interpolate mileage
    pred_cont = model.predict(years_cont, mile_cont)
    ax.plot(years_cont, pred_cont, 'r-', linewidth=2, label='Fitted model')

    # Future predictions with uncertainty
    pred_future = model.predict_with_uncertainty(
        future_years, future_mileage, random_state=random_state
    )
    ax.fill_between(future_years, pred_future['lower'], pred_future['upper'],
                    alpha=0.25, color='blue', label=f"{int(pred_future['confidence']*100)}% prediction interval")
    ax.plot(future_years, pred_future['mean'], 'b--', linewidth=2, label='Forecast')

    ax.axvline(x=max(years), color='gray', linestyle=':', alpha=0.7, label='Last observed')
    ax.set_xlabel('Years since new')
    ax.set_ylabel('Price (£)')
    ax.set_title('Car Depreciation: Model Fit & Forecast')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # ---- Panel 2: Residual diagnostics ----
    ax = axes[0, 1]
    pred_train = model.predict(years, mileage)
    residuals = prices - pred_train
    ax.scatter(pred_train, residuals, alpha=0.7, edgecolors='k')
    ax.axhline(y=0, color='red', linestyle='--')
    ax.set_xlabel('Predicted Price (£)')
    ax.set_ylabel('Residual (£)')
    ax.set_title('Residuals vs. Fitted Values')
    ax.grid(True, alpha=0.3)
    # Calculate running mean for visual
    order = np.argsort(pred_train)
    running_mean = uniform_filter1d(residuals[order], size=5, mode='reflect')
    ax.plot(pred_train[order], running_mean, color='darkred', linewidth=2, label='Local mean')
    ax.legend()

    # ---- Panel 3: Parameter importance and depreciation rates ----
    ax = axes[1, 0]
    params = model.params_
    # V0 (~10^4) and the rates (~10^-1) differ by five orders of magnitude, so
    # plotting them on one axis renders the rate bars invisible. Give V0 its own
    # axis on the right.
    rate_names = ['Early rate k₁', 'Late rate k₂', 'Mileage factor b']
    rate_values = [params['k1'], params['k2'], params['b']]
    x = np.arange(4)

    rate_bars = ax.bar(x[:3], rate_values, color=['coral', 'lightgreen', 'skyblue'])
    ax.set_ylabel('Rate (per year, or per 10k miles)')
    ax.set_ylim(0, max(rate_values) * 1.35)
    ax.bar_label(rate_bars, fmt='%.3f', padding=2, fontsize=9)

    ax_v0 = ax.twinx()
    v0_bar = ax_v0.bar(x[3], params['V0'], color='gold')
    ax_v0.set_ylabel('Initial price V₀ (£)')
    ax_v0.set_ylim(0, params['V0'] * 1.35)
    ax_v0.bar_label(v0_bar, fmt='£%.0f', padding=2, fontsize=9)
    ax_v0.grid(False)

    ax.set_xticks(x)
    ax.set_xticklabels(rate_names + ['Initial price V₀'], fontsize=8)

    # Convert rates to meaningful percentages: annual depreciation for k1 and k2
    annual_dep_early = (1 - np.exp(-params['k1'])) * 100
    annual_dep_late = (1 - np.exp(-params['k2'])) * 100
    mileage_penalty = (1 - np.exp(-params['b'])) * 100
    # Kept inside the title so it cannot be clipped off the bottom of the figure.
    ax.set_title(
        'Fitted Model Parameters\n'
        f'Early annual loss {annual_dep_early:.1f}%  |  Late annual loss {annual_dep_late:.1f}%'
        f'  |  Per 10k mi {mileage_penalty:.1f}%',
        fontsize=10
    )
    ax.grid(axis='y', alpha=0.3)

    # ---- Panel 4: Cross-validation performance summary ----
    ax = axes[1, 1]
    ax.axis('off')
    metrics_text = (
        f"Model Performance (in-sample)\n"
        f"{'─' * 30}\n"
        f"R² = {model.metrics_['R2']:.4f}\n"
        f"MAE = £{model.metrics_['MAE']:.0f}\n"
        f"MAPE = {model.metrics_['MAPE']:.1f}%\n"
        f"RMSE = £{model.metrics_['RMSE']:.0f}\n\n"
        f"Time Series Cross-validation ({cv_scores['cv_n_folds']} folds)\n"
        f"{'─' * 30}\n"
        f"CV MAPE = {cv_scores['cv_MAPE_mean']:.1f}% ± {cv_scores['cv_MAPE_std']:.1f}\n"
        f"CV MAE  = £{cv_scores['cv_MAE_mean']:.0f} ± £{cv_scores['cv_MAE_std']:.0f}\n\n"
        f"Interpretation:\n"
        f"• The model explains {model.metrics_['R2']*100:.1f}% of price variance.\n"
        f"• Out-of-sample error (CV MAPE) is ~{cv_scores['cv_MAPE_mean']:.1f}%,"
        f"\n  which is realistic for used car valuation."
    )
    ax.text(0.05, 0.95, metrics_text, transform=ax.transAxes, verticalalignment='top',
            fontsize=10, bbox=dict(boxstyle='round', facecolor='whitesmoke', alpha=0.8))

    plt.tight_layout()
    plt.show()


# ============================================================================
# 4. MAIN EXECUTION
# ============================================================================
if __name__ == "__main__":
    TRANSITION_AGE = 3.0
    SEED = 42

    # Generate data
    years, mileage, prices = generate_depreciation_data(
        max_age=10, transition_age=TRANSITION_AGE, seed=SEED
    )

    # Create and fit model
    model = CarDepreciationModel(transition_age=TRANSITION_AGE)
    model.fit(years, mileage, prices)

    # Cross-validation
    cv_results = model.cross_validate(years, mileage, prices, n_splits=5)

    # Future predictions (next 3 years, assuming similar annual mileage)
    future_years = np.arange(0, 13.5, 0.5)
    # Estimate future mileage by linear extrapolation of average annual increase.
    # Inside the observed age range, use the actual mileage path rather than a
    # backwards extrapolation from the final point, which would contradict the
    # data the model was fitted on.
    annual_mileage_rate = np.mean(np.diff(mileage) / np.diff(years))
    future_mileage = np.where(
        future_years <= years[-1],
        np.interp(future_years, years, mileage),
        mileage[-1] + annual_mileage_rate * (future_years - years[-1])
    )
    future_mileage = np.maximum(future_mileage, 0)

    # Plot everything
    plot_depreciation_analysis(model, years, mileage, prices,
                               future_years, future_mileage, cv_results,
                               random_state=SEED)

    # Print detailed prediction table for key ages
    print("\n" + "="*70)
    print("FORECAST WITH 90% PREDICTION INTERVALS")
    print("="*70)
    key_ages = np.arange(0, 13, 1)
    mile_at_key = np.interp(key_ages, future_years, future_mileage)
    pred_int = model.predict_with_uncertainty(
        key_ages, mile_at_key, confidence=0.90, random_state=SEED
    )
    print(f"{'Age (years)':<12} {'Predicted (£)':<15} {'Lower 90% (£)':<15} {'Upper 90% (£)':<15}")
    print("-"*70)
    for age, mean, low, high in zip(key_ages, pred_int['mean'], pred_int['lower'], pred_int['upper']):
        print(f"{age:<12.1f} £{mean:<14,.0f} £{low:<14,.0f} £{high:<14,.0f}")
    print("="*70)
    print("\nNote: Prediction intervals are obtained via residual bootstrap (500 iterations).")
    print(f"Cross-validated MAPE = {cv_results['cv_MAPE_mean']:.1f}% ± {cv_results['cv_MAPE_std']:.1f}%")
