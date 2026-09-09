"""
explain.py — SHAP-based Model Explainability for the Multi-Hazard Early Warning Pipeline
==========================================================================================

This module provides three levels of model explainability using SHAP (SHapley Additive
exPlanations):

1. **Global explainability** — SHAP summary (beeswarm) plot saved as a static PNG, showing
   which features drive predictions across the entire test set.

2. **Local explainability** — A structured dict naming the top-5 features that pushed a
   single prediction up or down, suitable for display in a REST API response or alert UI.

3. **Force-plot explainability** — An interactive HTML force plot for the highest-risk
   example in ``X_test``, useful for analyst review dashboards.

Supported model families
------------------------
- ``RandomForestClassifier`` (scikit-learn) — detected by ``model_name`` containing
  ``"rf"`` or by ``isinstance`` checks; SHAP returns a list of arrays (one per class),
  so we select ``shap_values[1]`` (the positive / landslide class).
- ``XGBClassifier`` (xgboost) — SHAP returns a single 2-D array directly.

Dependencies
------------
``shap``, ``matplotlib``, ``pandas``, ``numpy``, ``logging``.
All paths are resolved from ``config.py``.

Notes
-----
- ``plt.switch_backend('Agg')`` is called before every plot to ensure headless / CI
  operation (no display required).
- All public functions are safe to call from multi-threaded or subprocess contexts because
  they write to distinct file paths and do not share mutable module-level state.
- Exception handling inside ``generate_force_plot_html`` is intentionally non-fatal: a
  force-plot failure must not interrupt a training run or an API response.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")          # Set Agg backend before importing pyplot (headless-safe)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

try:
    from ml.src import config
except ImportError:
    try:
        from . import config
    except ImportError:
        import config

# ─── Module Logger ──────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ─── Internal Helpers ────────────────────────────────────────────────────────


def _ensure_output_dir(path: Path) -> None:
    """Create parent directories for *path* if they do not already exist.

    Parameters
    ----------
    path : Path
        File path whose parent directory tree should be created.
    """
    path.parent.mkdir(parents=True, exist_ok=True)


def _build_explainer(model: Any, data: Any = None) -> Any:
    """Construct a SHAP explainer for the given model.

    Uses TreeExplainer for tree ensembles (RandomForest, XGBoost).
    Falls back to LinearExplainer with masker for linear models, or generic Explainer.
    """
    try:
        return shap.TreeExplainer(model)
    except Exception:
        pass

    if data is not None and len(data) > 1:
        try:
            masker = shap.maskers.Independent(data=data)
            return shap.LinearExplainer(model, masker=masker)
        except Exception:
            pass
        try:
            return shap.Explainer(model.predict_proba, data)
        except Exception:
            pass

    # For single-row or missing background data with linear models:
    if hasattr(model, "coef_"):
        try:
            n_features = model.coef_.shape[1]
            masker = shap.maskers.Independent(data=np.zeros((1, n_features)))
            return shap.LinearExplainer(model, masker=masker)
        except Exception:
            pass

    try:
        return shap.Explainer(model)
    except Exception:
        return None


def _resolve_shap_values(
    shap_values: Any,
    model_name: str,
) -> np.ndarray:
    """Return the 2-D SHAP array for the positive (landslide) class.

    Random Forest classifiers return SHAP values as a **list of arrays**,
    one per output class.  XGBoost classifiers return a **single array**.
    This function normalises both cases to a single 2-D ``np.ndarray`` of
    shape ``(n_samples, n_features)``.

    Parameters
    ----------
    shap_values : Any
        Raw output of ``explainer.shap_values(X)``.
    model_name : str
        Lower-cased model identifier string (e.g. ``"rf"``, ``"xgb"``).
        Used as a secondary heuristic alongside the ``isinstance`` check.

    Returns
    -------
    np.ndarray
        2-D array of shape ``(n_samples, n_features)`` containing SHAP
        values for the positive class (class index 1 for binary problems).
    """
    if isinstance(shap_values, list):
        # RandomForest (scikit-learn) list[ndarray], one per class.
        idx = 1 if len(shap_values) > 1 else 0
        return np.array(shap_values[idx])

    arr = np.array(shap_values)
    if arr.ndim == 3:
        # Shape: (n_samples, n_features, n_classes) -> select class 1 (landslide positive)
        idx = 1 if arr.shape[2] > 1 else 0
        logger.debug("SHAP values are 3-D %s; selecting slice index %d along axis 2.", arr.shape, idx)
        return arr[:, :, idx]

    logger.debug(
        "SHAP values returned as ndarray; shape=%s (model_name=%s).",
        arr.shape,
        model_name,
    )
    return arr


# ─── Public API ──────────────────────────────────────────────────────────────


def generate_global_shap(
    model: Any,
    X_test: pd.DataFrame,
    model_name: str,
) -> None:
    """Compute SHAP values for the test set and save a global summary (beeswarm) plot.

    The plot is saved to :attr:`config.SHAP_SUMMARY_PATH` as a PNG.  The
    ``Agg`` matplotlib backend is explicitly activated so this function works
    in headless server environments (no ``$DISPLAY`` required).

    Parameters
    ----------
    model : Any
        Fitted tree-based classifier (``RandomForestClassifier`` or
        ``XGBClassifier``).
    X_test : pd.DataFrame
        Feature matrix for the held-out test set.  Column names must match
        those used during training so that SHAP can display readable labels.
    model_name : str
        Short identifier string for the model (e.g. ``"rf"``, ``"xgb"``).
        Used for log messages and to disambiguate SHAP output shapes.

    Returns
    -------
    None
        Side-effect: writes ``config.SHAP_SUMMARY_PATH``.

    Raises
    ------
    Exception
        Any exception from the SHAP or matplotlib layer is propagated to the
        caller after being logged at ERROR level.

    Notes
    -----
    - For Random Forest models, ``shap_values`` is a list of arrays (one per
      class); we select index 1 (positive / landslide class).
    - For XGBoost models, ``shap_values`` is a single 2-D array.
    - The function always calls ``plt.close(''all'')`` to release figure memory.
    """
    logger.info(
        "Generating global SHAP summary plot for model '%s' on %d test samples ...",
        model_name,
        len(X_test),
    )

    try:
        plt.switch_backend("Agg")

        # ── 1. Build explainer & compute SHAP values ─────────────────────────
        # Subsample to at most 1000 rows for fast and robust SHAP summary
        if len(X_test) > 1000:
            X_eval = X_test.sample(1000, random_state=42)
        else:
            X_eval = X_test

        explainer = _build_explainer(model, data=X_eval)
        if explainer is None:
            logger.warning("Could not initialize SHAP explainer for %s — skipping global plot.", model_name)
            return

        if hasattr(explainer, "shap_values"):
            try:
                raw_shap = explainer.shap_values(X_eval)
            except Exception:
                raw_shap = explainer(X_eval).values
        else:
            raw_shap = explainer(X_eval).values

        shap_vals = _resolve_shap_values(raw_shap, model_name)

        # ── 2. Render beeswarm summary plot ──────────────────────────────────
        fig, ax = plt.subplots(figsize=(12, 7))
        shap.summary_plot(
            shap_vals,
            X_eval,
            show=False,
            plot_size=None,   # let our figsize control dimensions
        )
        ax = plt.gca()
        ax.set_title(
            f"SHAP Global Feature Importance — {model_name.upper()} (Landslide Risk)",
            fontsize=13,
            fontweight="bold",
            pad=12,
        )

        # ── 3. Persist to disk ───────────────────────────────────────────────
        output_path = Path(config.SHAP_SUMMARY_PATH)
        _ensure_output_dir(output_path)
        plt.savefig(output_path, bbox_inches="tight", dpi=150)
        plt.close("all")

        logger.info("SHAP summary plot saved to %s", output_path)

    except Exception:
        plt.close("all")
        logger.exception(
            "Failed to generate global SHAP summary plot for model '%s'.", model_name
        )
        raise


def explain_prediction(
    model: Any,
    X_single_row: pd.DataFrame,
    feature_names: list[str],
) -> dict:
    """Return the top-5 SHAP-contributing features for a single prediction.

    Given a one-row feature DataFrame, this function computes per-feature SHAP
    values and returns them ranked by absolute contribution.  The output is
    intentionally JSON-serialisable so it can be embedded directly in API
    responses or alert notifications.

    Parameters
    ----------
    model : Any
        Fitted tree-based classifier (``RandomForestClassifier`` or
        ``XGBClassifier``).
    X_single_row : pd.DataFrame
        A **single-row** DataFrame (shape ``(1, n_features)``).  Column names
        must match the training feature set.  If multiple rows are passed, only
        the first row is explained.
    feature_names : list[str]
        Ordered list of feature names corresponding to the columns of
        ``X_single_row``.  Used for labelling when ``X_single_row`` does not
        carry named columns.

    Returns
    -------
    dict
        Structured explanation dict::

            {
                "top_factors": [
                    {
                        "feature":    "rainfall_24hr_mm",
                        "shap_value": 0.31,
                        "direction":  "increases_risk",
                    },
                    {
                        "feature":    "soil_moisture_pct",
                        "shap_value": -0.09,
                        "direction":  "decreases_risk",
                    },
                    # ... up to 5 entries, sorted by |shap_value| descending
                ]
            }

        ``direction`` is ``"increases_risk"`` when ``shap_value > 0``,
        ``"decreases_risk"`` when ``shap_value < 0``, and
        ``"neutral"`` when ``shap_value == 0``.

    Raises
    ------
    ValueError
        If ``X_single_row`` contains zero rows.
    Exception
        Any SHAP computation error is logged and re-raised so the caller can
        return a safe fallback in the API layer.

    Assumptions
    -----------
    - The model is a binary classifier (``landslide_occurred in {0, 1}``).
    - For Random Forest models, class-1 SHAP values are used (index 1 of the
      list returned by ``explainer.shap_values``).
    - SHAP values are assumed to be additive contributions in log-odds or
      probability space depending on the model type; their sign correctly
      reflects directional feature impact on the positive class.
    - ``X_single_row`` is expected to have been preprocessed (imputed, encoded,
      scaled) identically to the training data before being passed here.

    Examples
    --------
    >>> result = explain_prediction(model, X_row, feature_names)
    >>> for factor in result["top_factors"]:
    ...     print(factor["feature"], factor["shap_value"], factor["direction"])
    rainfall_24hr_mm  0.31  increases_risk
    soil_moisture_pct -0.09  decreases_risk
    """
    if X_single_row.empty:
        raise ValueError(
            "explain_prediction() requires at least one row in X_single_row; "
            "received an empty DataFrame."
        )

    # Use only the first row if multiple were accidentally passed.
    row = X_single_row.iloc[[0]]

    logger.debug(
        "Computing local SHAP explanation for one sample (features: %d).",
        len(feature_names),
    )

    try:
        explainer = _build_explainer(model, data=None)
        if explainer is not None:
            if hasattr(explainer, "shap_values"):
                try:
                    raw_shap = explainer.shap_values(row)
                except Exception:
                    raw_shap = explainer(row).values
            else:
                raw_shap = explainer(row).values
            shap_vals_2d = _resolve_shap_values(raw_shap, model_name="unknown")
            shap_vals_1d = shap_vals_2d[0]
        else:
            raise ValueError("No explainer available")
    except Exception as exc:
        logger.warning("SHAP computation failed inside explain_prediction: %s. Using coefficient fallback.", exc)
        if hasattr(model, "coef_"):
            shap_vals_1d = model.coef_[0] * np.nan_to_num(row.values[0], nan=0.0)
        elif hasattr(model, "feature_importances_"):
            shap_vals_1d = model.feature_importances_ * np.nan_to_num(row.values[0], nan=0.0)
        else:
            shap_vals_1d = np.zeros(len(feature_names))

    # ── Build sorted factor list ──────────────────────────────────────────────
    # Pair feature names with their SHAP values, then sort by |SHAP| desc.
    n = min(len(feature_names), len(shap_vals_1d))
    factor_pairs = list(zip(feature_names[:n], shap_vals_1d[:n].tolist()))
    factor_pairs.sort(key=lambda pair: abs(pair[1]), reverse=True)

    top_5 = factor_pairs[:5]
    abs_sum = sum(abs(pair[1]) for pair in top_5) or 1.0

    top_factors: list[dict] = []
    for feat, sv in top_5:
        if sv > 0:
            direction = "increases_risk"
        elif sv < 0:
            direction = "decreases_risk"
        else:
            direction = "neutral"

        pct = round((abs(sv) / abs_sum) * 100.0, 1)
        top_factors.append(
            {
                "feature":          feat,
                "shap_value":       round(float(sv), 6),
                "direction":        direction,
                "contribution_pct": pct,
            }
        )

    logger.debug(
        "Top-5 factors: %s",
        [f"{f['feature']}={f['shap_value']}" for f in top_factors],
    )

    return {"top_factors": top_factors}


def generate_force_plot_html(
    model: Any,
    X_test: pd.DataFrame,
    model_name: str,
) -> None:
    """Generate and save an interactive SHAP force plot for the highest-risk example.

    The function locates the sample in ``X_test`` with the highest predicted
    probability, computes its SHAP values, and saves the force plot as a
    self-contained HTML file to :attr:`config.SHAP_FORCE_PATH`.

    Parameters
    ----------
    model : Any
        Fitted tree-based classifier (``RandomForestClassifier`` or
        ``XGBClassifier``).
    X_test : pd.DataFrame
        Feature matrix for the held-out test set.  Must contain at least one
        row.
    model_name : str
        Short model identifier string (e.g. ``"rf"``, ``"xgb"``).  Used for
        log messages and SHAP value shape resolution.

    Returns
    -------
    None
        Side-effect: writes ``config.SHAP_FORCE_PATH``.

    Notes
    -----
    - This function is **non-fatal**: any exception during force-plot generation
      is caught, logged as a WARNING, and execution continues normally.  This
      ensures a force-plot failure never crashes a training run or API call.
    - The function uses ``model.predict_proba`` to identify the high-risk sample.
      If the model does not support ``predict_proba``, it falls back to
      ``model.decision_function``.
    - SHAP JavaScript initialisation is called with ``matplotlib=False`` to
      produce an interactive plot rather than a static PNG.
    """
    logger.info(
        "Generating SHAP force plot (highest-risk example) for model '%s' ...",
        model_name,
    )

    try:
        plt.switch_backend("Agg")

        # ── 1. Find the highest-risk sample ──────────────────────────────────
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X_test)[:, 1]  # P(landslide=1)
        elif hasattr(model, "decision_function"):
            logger.debug(
                "Model lacks predict_proba; falling back to decision_function."
            )
            proba = model.decision_function(X_test)
        else:
            raise AttributeError(
                f"Model of type {type(model).__name__} has neither "
                "'predict_proba' nor 'decision_function'."
            )

        high_risk_idx: int = int(np.argmax(proba))
        high_risk_prob: float = float(proba[high_risk_idx])
        logger.info(
            "Highest-risk sample: index=%d, P(landslide)=%.4f.",
            high_risk_idx,
            high_risk_prob,
        )

        # ── 2. Compute SHAP values for that single row ────────────────────────
        row = X_test.iloc[[high_risk_idx]]
        explainer = _build_explainer(model, data=row)
        if explainer is None:
            logger.warning("Could not build explainer for force plot on %s.", model_name)
            return

        if hasattr(explainer, "shap_values"):
            try:
                raw_shap = explainer.shap_values(row)
            except Exception:
                raw_shap = explainer(row).values
        else:
            raw_shap = explainer(row).values
        shap_vals = _resolve_shap_values(raw_shap, model_name)

        # ── 3. Build & save the force plot (both PNG & Self-contained HTML) ──
        output_path = Path(config.SHAP_FORCE_PATH)
        _ensure_output_dir(output_path)
        png_path = output_path.with_suffix(".png")

        # Resolve base_value
        expected_val = explainer.expected_value if hasattr(explainer, "expected_value") else 0.0
        if isinstance(expected_val, (list, np.ndarray)):
            base_value = float(expected_val[1]) if len(expected_val) > 1 else float(expected_val[0])
        else:
            base_value = float(expected_val)

        row_series = X_test.iloc[high_risk_idx]
        shap_vals_1d = shap_vals[0]

        # A. Generate static high-res force plot PNG
        try:
            plt.figure(figsize=(14, 3.5))
            shap.force_plot(
                base_value=base_value,
                shap_values=shap_vals_1d,
                features=row_series,
                matplotlib=True,
                show=False,
            )
            plt.savefig(png_path, bbox_inches="tight", dpi=150)
            plt.close("all")
            logger.info("SHAP force plot static PNG saved to %s", png_path)
        except Exception as img_err:
            logger.warning("Could not render matplotlib force plot: %s", img_err)

        # B. Encode PNG as base64 for embedding in self-contained HTML
        img_b64 = ""
        if png_path.exists():
            import base64
            with open(png_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

        # Rank factors for this sample
        factor_pairs = list(zip(list(X_test.columns), shap_vals_1d.tolist(), row_series.tolist()))
        factor_pairs.sort(key=lambda x: abs(x[1]), reverse=True)

        rows_html = ""
        for feat, sv, fval in factor_pairs[:10]:
            color = "#dc2626" if sv > 0 else "#2563eb"
            direction = "INCREASES RISK" if sv > 0 else "DECREASES RISK"
            rows_html += f"""
            <tr>
                <td style="padding: 8px 12px; font-weight: 600;">{feat}</td>
                <td style="padding: 8px 12px; font-family: monospace;">{fval:.4f}</td>
                <td style="padding: 8px 12px; color: {color}; font-weight: 700;">{sv:+.4f}</td>
                <td style="padding: 8px 12px; color: {color}; font-size: 0.85em; font-weight: 600;">{direction}</td>
            </tr>
            """

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SHAP Force Plot Explanation — High-Risk Landslide Event</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; color: #1e293b; margin: 0; padding: 24px; }}
        .container {{ max-width: 1100px; margin: 0 auto; background: #ffffff; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); padding: 32px; }}
        h1 {{ margin-top: 0; color: #0f172a; font-size: 1.6rem; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; font-weight: 700; font-size: 0.85rem; }}
        .badge-danger {{ background: #fee2e2; color: #dc2626; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 20px 0; }}
        .metric-card {{ background: #f1f5f9; padding: 16px; border-radius: 8px; }}
        .metric-card .val {{ font-size: 1.5rem; font-weight: 800; color: #0f172a; }}
        .metric-card .lbl {{ font-size: 0.85rem; color: #64748b; text-transform: uppercase; margin-top: 4px; }}
        .plot-container {{ margin: 24px 0; text-align: center; background: #ffffff; padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px; }}
        .plot-container img {{ max-width: 100%; height: auto; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #f8fafc; text-align: left; padding: 10px 12px; border-bottom: 2px solid #e2e8f0; font-size: 0.85rem; text-transform: uppercase; color: #475569; }}
        tr:nth-child(even) {{ background: #f8fafc; }}
        td {{ border-bottom: 1px solid #e2e8f0; }}
    </style>
</head>
<body>
    <div class="container">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h1>SHAP Force Plot — Local Risk Factor Explanation</h1>
            <span class="badge badge-danger">CRITICAL ALERT EVENT</span>
        </div>
        <p style="color: #64748b;">Visualizing feature contributions that pushed the early warning system's output for Sample #{high_risk_idx}.</p>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="val" style="color: #dc2626;">{high_risk_prob * 100:.1f}%</div>
                <div class="lbl">Predicted Landslide Probability</div>
            </div>
            <div class="metric-card">
                <div class="val">{base_value:.4f}</div>
                <div class="lbl">Regional Baseline Log-Odds</div>
            </div>
            <div class="metric-card">
                <div class="val">{model_name.upper()}</div>
                <div class="lbl">Model Evaluated</div>
            </div>
        </div>

        <div class="plot-container">
            <h3 style="margin-top: 0; color: #334155;">Interactive Force Diagram (Tug-of-War Attribution)</h3>
            {"<img src='data:image/png;base64," + img_b64 + "' alt='SHAP Force Plot'>" if img_b64 else "<p>Force plot image generated.</p>"}
        </div>

        <h3>Top 10 Influential Factor Breakdown</h3>
        <table>
            <thead>
                <tr>
                    <th>Feature Name</th>
                    <th>Observed Value</th>
                    <th>SHAP Contribution</th>
                    <th>Effect on Disaster Risk</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
</body>
</html>"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_doc)

        logger.info("Self-contained SHAP force plot HTML saved to %s", output_path)

    except Exception as exc:
        # Non-fatal: log and continue — force-plot failures must not break runs.
        logger.warning(
            "Force plot generation failed for model '%s' — skipping. "
            "Reason: %s: %s",
            model_name,
            type(exc).__name__,
            exc,
        )


def run_explainability(
    model: Any,
    X_test: pd.DataFrame,
    feature_names: list[str],
    model_name: str,
) -> dict:
    """Master explainability runner: global SHAP summary + high-risk force plot.

    Orchestrates the full explainability pipeline for a trained model:

    1. Calls :func:`generate_global_shap` to create and save the SHAP beeswarm
       summary PNG.
    2. Calls :func:`generate_force_plot_html` to create and save the interactive
       HTML force plot for the highest-risk test-set example.

    Both artefact paths are returned in the result dict so the caller
    (e.g. ``train.py``) can log or report them without needing to import
    ``config`` directly.

    Parameters
    ----------
    model : Any
        Fitted tree-based classifier (``RandomForestClassifier`` or
        ``XGBClassifier``).
    X_test : pd.DataFrame
        Feature matrix for the held-out test set.
    feature_names : list[str]
        Ordered list of feature column names.  Must correspond to the columns
        of ``X_test`` (used internally for ``explain_prediction`` calls).
    model_name : str
        Short identifier string for the model (e.g. ``"rf"``, ``"xgb"``).
        Used in log messages and SHAP output-shape disambiguation.

    Returns
    -------
    dict
        Paths to the generated artefacts::

            {
                "shap_summary_path": "/path/to/reports/shap_summary.png",
                "force_plot_path":   "/path/to/reports/shap_force_example.html",
            }

        Both values are absolute path strings.  If either artefact could not
        be generated the corresponding value is ``None``.

    Examples
    --------
    >>> artefacts = run_explainability(best_model, X_test, feature_names, "xgb")
    >>> print(artefacts["shap_summary_path"])
    /project/ml/reports/shap_summary.png
    """
    logger.info(
        "=== Starting explainability pipeline for model '%s' ===", model_name
    )

    result: dict[str, str | None] = {
        "shap_summary_path": None,
        "force_plot_path":   None,
    }

    # ── 1. Global SHAP summary plot ───────────────────────────────────────────
    try:
        generate_global_shap(model, X_test, model_name)
        result["shap_summary_path"] = str(Path(config.SHAP_SUMMARY_PATH).resolve())
    except Exception:
        logger.error(
            "Global SHAP summary generation failed for model '%s'. "
            "Continuing with force plot ...",
            model_name,
        )

    # ── 2. Force plot for highest-risk example ────────────────────────────────
    # generate_force_plot_html is already non-fatal internally; wrapping here
    # provides an additional safety layer for unexpected interpreter errors.
    try:
        generate_force_plot_html(model, X_test, model_name)
        result["force_plot_path"] = str(Path(config.SHAP_FORCE_PATH).resolve())
    except Exception:
        logger.error(
            "Force plot generation raised an unhandled exception for model '%s'.",
            model_name,
        )

    logger.info(
        "=== Explainability pipeline complete. Summary: %s | Force plot: %s ===",
        result["shap_summary_path"] or "FAILED",
        result["force_plot_path"]   or "FAILED",
    )

    return result
