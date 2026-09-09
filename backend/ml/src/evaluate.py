"""
ml/src/evaluate.py
==================
Model evaluation and reporting module for the Multi-Hazard Early Warning
System AI/ML Prediction Pipeline.

Responsibilities
----------------
* Compute a comprehensive set of evaluation metrics for trained classifiers:
  confusion matrix, classification report, ROC-AUC, PR-AUC (primary metric),
  calibration data, and feature importance.
* Threshold analysis — find the operating point that balances recall and
  precision for the rare positive (landslide) class.
* Reliability diagram (calibration curve) saved to ``ml/reports/``.
* Multi-model comparison that selects the best model by PR-AUC and persists it.
* Full-text evaluation report saved to ``ml/reports/evaluation_report.txt``.

Design notes
------------
* **PR-AUC is the primary metric** because the dataset is heavily imbalanced
  (~8% positives).  Accuracy alone is misleading.
* ``plt.switch_backend('Agg')`` is called once at import time so the module
  works in headless / server environments without a display.
* All file-system paths are sourced from ``config.py`` — no hard-coded strings
  inside functions.
* Every public function is fully type-annotated and documented.

Author : Member 3 — AI/ML Prediction
Project: SIH 2026 Multi-Hazard Early Warning System (Prototype)
"""

from __future__ import annotations

import logging
import os
import textwrap
from datetime import datetime
from typing import Any

import joblib
import matplotlib
matplotlib.use("Agg")          # Must be called BEFORE importing pyplot — works headless
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)

# ---------------------------------------------------------------------------
# Local imports — config is the single source of truth for paths / constants.
# If config.py has not been created yet, fall back to inline defaults so that
# this module can be imported and tested independently.
# ---------------------------------------------------------------------------
try:
    from ml.src import config
except ImportError:  # pragma: no cover — fallback for standalone testing
    import types

    config = types.SimpleNamespace(  # type: ignore[assignment]
        REPORTS_DIR=os.path.join(
            os.path.dirname(__file__), "..", "..", "reports"
        ),
        BEST_MODEL_PATH=os.path.join(
            os.path.dirname(__file__), "..", "..", "models", "best_model.joblib"
        ),
        EVALUATION_REPORT_PATH=os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "reports",
            "evaluation_report.txt",
        ),
        PROTOTYPE_WARNING=(
            "This is a prototype system. Risk probabilities are estimates based on "
            "a simulated training dataset. Model has not been validated against real "
            "Himalayan landslide events. Do not use for operational emergency decisions."
        ),
        RECALL_MIN_THRESHOLD=0.75,
        CALIBRATION_N_BINS=10,
    )

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_reports_dir() -> str:
    """Create ``config.REPORTS_DIR`` if it does not exist and return its path.

    Returns
    -------
    str
        Absolute path to the reports directory.
    """
    reports_dir: str = str(config.REPORTS_DIR)
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir


def _get_feature_importance(
    model: Any,
    feature_names: list[str] | None = None,
) -> dict[str, float] | None:
    """Extract feature importance from a trained model.

    Supports:
    * ``RandomForestClassifier`` / ``ExtraTreesClassifier`` — ``feature_importances_``
    * ``XGBClassifier`` — ``feature_importances_`` (gain-based by default)
    * ``LogisticRegression`` — ``coef_[0]`` (absolute coefficient magnitudes)

    Parameters
    ----------
    model : Any
        A trained scikit-learn–compatible classifier.
    feature_names : list[str] | None
        Column names corresponding to model features.  If ``None``, generic
        integer indices are used.

    Returns
    -------
    dict[str, float] | None
        Mapping of feature name → importance score, sorted descending.
        Returns ``None`` if the model exposes no importance attribute.
    """
    importances: np.ndarray | None = None

    if hasattr(model, "feature_importances_"):
        # RandomForest, ExtraTrees, XGBoost, LightGBM, etc.
        importances = np.asarray(model.feature_importances_, dtype=float)
        logger.debug("Feature importances extracted via feature_importances_.")
    elif hasattr(model, "coef_"):
        # Logistic Regression, LinearSVC, etc.
        coef = np.asarray(model.coef_, dtype=float)
        if coef.ndim == 2:
            coef = coef[0]  # binary classification → shape (n_features,)
        importances = np.abs(coef)  # absolute magnitude as proxy for importance
        logger.debug("Feature importances extracted via |coef_[0]|.")
    else:
        logger.warning(
            "Model type '%s' exposes neither feature_importances_ nor coef_. "
            "Skipping feature importance.",
            type(model).__name__,
        )
        return None

    n_features = len(importances)
    if feature_names is None:
        names: list[str] = [f"feature_{i}" for i in range(n_features)]
    else:
        names = list(feature_names)
        if len(names) != n_features:
            logger.warning(
                "feature_names length (%d) != importances length (%d). "
                "Falling back to integer indices.",
                len(names),
                n_features,
            )
            names = [f"feature_{i}" for i in range(n_features)]

    importance_dict: dict[str, float] = dict(zip(names, importances.tolist()))
    # Sort descending by importance value
    importance_dict = dict(
        sorted(importance_dict.items(), key=lambda kv: kv[1], reverse=True)
    )
    return importance_dict


# ===========================================================================
# PUBLIC API
# ===========================================================================


def evaluate_model(
    model: Any,
    X_test: pd.DataFrame | np.ndarray,
    y_test: pd.Series | np.ndarray,
    model_name: str,
) -> dict[str, Any]:
    """Compute a full evaluation suite for a binary classifier.

    Metrics computed
    ----------------
    * **Confusion matrix** — absolute counts (TN, FP, FN, TP)
    * **Classification report** — per-class precision, recall, F1
    * **ROC-AUC** — area under the ROC curve
    * **PR-AUC** — ``average_precision_score`` (PRIMARY metric for imbalanced data)
    * **Calibration data** — ``fraction_of_positives`` and ``mean_predicted_value``
      from ``sklearn.calibration.calibration_curve``
    * **Feature importance** — model-type–aware extraction (see
      :func:`_get_feature_importance`)

    Special warnings
    ----------------
    * If ``accuracy > 0.95``, a prominent warning is printed reminding the
      engineer that high accuracy on imbalanced data is not a quality signal.
    * Recall for the positive class (landslide detection rate) is printed
      with emphasis because it is the operationally most critical metric.

    Parameters
    ----------
    model : Any
        A fitted scikit-learn–compatible classifier that exposes
        ``predict(X)`` and ``predict_proba(X)``.
    X_test : pd.DataFrame | np.ndarray
        Feature matrix for the held-out test split.
    y_test : pd.Series | np.ndarray
        True binary labels (0 = no landslide, 1 = landslide).
    model_name : str
        Human-readable identifier used in log messages and report output
        (e.g. ``"RandomForest"``).

    Returns
    -------
    dict[str, Any]
        Dictionary with the following keys:

        ``model_name``
            Echo of the *model_name* argument.
        ``accuracy``
            Overall fraction of correct predictions.
        ``confusion_matrix``
            2-D list ``[[TN, FP], [FN, TP]]``.
        ``classification_report``
            Nested dict from ``sklearn.metrics.classification_report``.
        ``recall_positive``
            Recall for class 1 (landslide detection rate).
        ``precision_positive``
            Precision for class 1.
        ``f1_positive``
            F1-score for class 1.
        ``roc_auc``
            Area under the ROC curve.
        ``pr_auc``
            Average precision score — primary selection metric.
        ``calibration_fraction_of_positives``
            List of observed positive rates per calibration bin.
        ``calibration_mean_predicted``
            List of mean predicted probabilities per calibration bin.
        ``feature_importance``
            ``dict[str, float]`` or ``None`` if not available.
        ``evaluated_at``
            ISO-8601 timestamp of evaluation.

    Raises
    ------
    ValueError
        If *y_test* contains labels other than 0 and 1.
    RuntimeError
        If the model does not support ``predict_proba``.

    Examples
    --------
    >>> metrics = evaluate_model(rf_model, X_test, y_test, "RandomForest")
    >>> print(metrics["pr_auc"])
    0.712   # EXAMPLE OUTPUT — actual values will vary
    """
    logger.info("=" * 70)
    logger.info("Evaluating model: %s", model_name)
    logger.info("=" * 70)

    # ------------------------------------------------------------------
    # Input guards
    # ------------------------------------------------------------------
    y_test_arr = np.asarray(y_test, dtype=int)
    unique_labels = set(y_test_arr.tolist())
    if not unique_labels.issubset({0, 1}):
        raise ValueError(
            f"y_test must contain only binary labels 0 and 1. "
            f"Found: {unique_labels}"
        )

    if not hasattr(model, "predict_proba"):
        raise RuntimeError(
            f"Model '{type(model).__name__}' does not implement predict_proba(). "
            "Probabilistic metrics (ROC-AUC, PR-AUC, calibration) cannot be computed."
        )

    # ------------------------------------------------------------------
    # Predictions
    # ------------------------------------------------------------------
    y_pred: np.ndarray = model.predict(X_test)
    y_prob: np.ndarray = model.predict_proba(X_test)[:, 1]  # P(landslide=1)

    # ------------------------------------------------------------------
    # 1. Accuracy + imbalance warning
    # ------------------------------------------------------------------
    accuracy: float = float(np.mean(y_pred == y_test_arr))
    logger.info("Accuracy: %.4f", accuracy)

    if accuracy > 0.95:
        warning_msg = (
            "WARNING: High accuracy may reflect class imbalance, not model "
            "quality. Check PR-AUC and Recall for class=1."
        )
        print(f"\n{'!' * 70}")
        print(warning_msg)
        print(f"{'!' * 70}\n")
        logger.warning(warning_msg)

    # ------------------------------------------------------------------
    # 2. Confusion matrix
    # ------------------------------------------------------------------
    cm: np.ndarray = confusion_matrix(y_test_arr, y_pred)
    tn, fp, fn, tp = cm.ravel()
    logger.info(
        "Confusion Matrix — TN: %d | FP: %d | FN: %d | TP: %d",
        tn, fp, fn, tp,
    )

    # ------------------------------------------------------------------
    # 3. Classification report
    # ------------------------------------------------------------------
    report_dict: dict = classification_report(
        y_test_arr,
        y_pred,
        target_names=["no_landslide", "landslide"],
        output_dict=True,
        zero_division=0,
    )
    report_str: str = classification_report(
        y_test_arr,
        y_pred,
        target_names=["no_landslide", "landslide"],
        zero_division=0,
    )
    logger.info("\nClassification Report:\n%s", report_str)

    # ------------------------------------------------------------------
    # Extract per-class metrics for class=1 (positive / landslide)
    # ------------------------------------------------------------------
    recall_positive: float = float(report_dict.get("landslide", {}).get("recall", 0.0))
    precision_positive: float = float(report_dict.get("landslide", {}).get("precision", 0.0))
    f1_positive: float = float(report_dict.get("landslide", {}).get("f1-score", 0.0))

    # Emphasised recall print — operationally most important
    print(f"\n{'*' * 60}")
    print(f"  *** RECALL (landslide detection rate): {recall_positive:.3f} ***")
    print(
        "  (Proportion of actual landslide events correctly detected.\n"
        "   A higher value means fewer missed disasters.)"
    )
    print(f"{'*' * 60}\n")

    logger.info("RECALL (landslide detection rate): %.3f", recall_positive)
    logger.info("Precision (class=1): %.3f", precision_positive)
    logger.info("F1-score (class=1):  %.3f", f1_positive)

    # ------------------------------------------------------------------
    # 4. ROC-AUC
    # ------------------------------------------------------------------
    roc_auc: float = float(roc_auc_score(y_test_arr, y_prob))
    logger.info("ROC-AUC: %.4f", roc_auc)

    # ------------------------------------------------------------------
    # 5. PR-AUC (primary metric)
    # ------------------------------------------------------------------
    pr_auc: float = float(average_precision_score(y_test_arr, y_prob))
    logger.info("PR-AUC (primary metric): %.4f", pr_auc)

    # ------------------------------------------------------------------
    # 6. Calibration data
    # ------------------------------------------------------------------
    n_bins: int = getattr(config, "CALIBRATION_N_BINS", 10)
    fraction_of_positives, mean_predicted_value = calibration_curve(
        y_test_arr,
        y_prob,
        n_bins=n_bins,
        strategy="uniform",
    )
    logger.info("Calibration computed with %d uniform bins.", n_bins)

    # ------------------------------------------------------------------
    # 7. Feature importance
    # ------------------------------------------------------------------
    feature_names: list[str] | None = None
    if isinstance(X_test, pd.DataFrame):
        feature_names = list(X_test.columns)

    feature_importance: dict[str, float] | None = _get_feature_importance(
        model, feature_names=feature_names
    )

    if feature_importance:
        top_n = 10
        logger.info(
            "Top %d features by importance:\n%s",
            top_n,
            "\n".join(
                f"  {name}: {val:.6f}"
                for name, val in list(feature_importance.items())[:top_n]
            ),
        )

    # ------------------------------------------------------------------
    # Assemble results dict
    # ------------------------------------------------------------------
    results: dict[str, Any] = {
        "model_name": model_name,
        "accuracy": round(accuracy, 6),
        "confusion_matrix": cm.tolist(),
        "classification_report": report_dict,
        "recall_positive": round(recall_positive, 6),
        "precision_positive": round(precision_positive, 6),
        "f1_positive": round(f1_positive, 6),
        "roc_auc": round(roc_auc, 6),
        "pr_auc": round(pr_auc, 6),
        "calibration_fraction_of_positives": fraction_of_positives.tolist(),
        "calibration_mean_predicted": mean_predicted_value.tolist(),
        "feature_importance": feature_importance,
        "evaluated_at": datetime.now().isoformat(timespec="seconds"),
    }

    logger.info("Evaluation complete for '%s'.", model_name)
    return results


# ---------------------------------------------------------------------------


def threshold_analysis(
    model: Any,
    X_test: pd.DataFrame | np.ndarray,
    y_test: pd.Series | np.ndarray,
) -> tuple[float, dict[float, dict[str, float]]]:
    """Analyse classifier performance across a range of decision thresholds.

    For each threshold from 0.1 to 0.9 (step 0.1), hard predictions are
    derived by comparing ``predict_proba()[:, 1]`` against the threshold and
    precision, recall, and F1 are computed.

    The **best threshold** is defined as the one that satisfies
    ``recall >= config.RECALL_MIN_THRESHOLD`` (default 0.75) **and** achieves
    the highest precision among all such thresholds.  If no threshold meets
    the recall constraint, the threshold with the highest recall is returned
    as a fallback.

    A formatted table of all threshold results is printed to stdout and
    logged at INFO level.

    Parameters
    ----------
    model : Any
        Fitted classifier with a ``predict_proba(X)`` method.
    X_test : pd.DataFrame | np.ndarray
        Feature matrix for the held-out test set.
    y_test : pd.Series | np.ndarray
        True binary labels.

    Returns
    -------
    best_threshold : float
        The selected operating threshold (see selection logic above).
    threshold_results : dict[float, dict[str, float]]
        Nested dict keyed by threshold value.  Each inner dict contains:
        ``precision``, ``recall``, ``f1``.

    Examples
    --------
    >>> best_t, results = threshold_analysis(rf_model, X_test, y_test)
    >>> print(f"Best threshold: {best_t}  Recall: {results[best_t]['recall']:.3f}")
    Best threshold: 0.3  Recall: 0.810  # EXAMPLE OUTPUT — actual values will vary
    """
    logger.info("Running threshold analysis ...")

    if not hasattr(model, "predict_proba"):
        raise RuntimeError(
            f"Model '{type(model).__name__}' does not implement predict_proba()."
        )

    y_test_arr = np.asarray(y_test, dtype=int)
    y_prob: np.ndarray = model.predict_proba(X_test)[:, 1]

    recall_min: float = float(getattr(config, "RECALL_MIN_THRESHOLD", 0.75))

    thresholds: list[float] = [round(t, 1) for t in np.arange(0.1, 1.0, 0.1)]
    threshold_results: dict[float, dict[str, float]] = {}

    # Print table header
    meets_label = f"Meets recall>={recall_min:.2f}?"
    header = (
        f"\n{'Threshold':>12} | {'Precision':>10} | {'Recall':>8} | {'F1':>8}"
        f" | {meets_label:>22}"
    )
    separator = "-" * len(header)
    print(header)
    print(separator)

    for t in thresholds:
        y_pred_t = (y_prob >= t).astype(int)

        # Compute TP, FP, FN manually to avoid division-by-zero exceptions
        tp = int(np.sum((y_pred_t == 1) & (y_test_arr == 1)))
        fp = int(np.sum((y_pred_t == 1) & (y_test_arr == 0)))
        fn = int(np.sum((y_pred_t == 0) & (y_test_arr == 1)))

        precision_t: float = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall_t: float = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_t: float = (
            2 * precision_t * recall_t / (precision_t + recall_t)
            if (precision_t + recall_t) > 0
            else 0.0
        )

        threshold_results[t] = {
            "precision": round(precision_t, 6),
            "recall": round(recall_t, 6),
            "f1": round(f1_t, 6),
        }

        meets = "YES" if recall_t >= recall_min else "no"
        row = (
            f"{t:>12.1f} | {precision_t:>10.4f} | {recall_t:>8.4f}"
            f" | {f1_t:>8.4f} | {meets:>22}"
        )
        print(row)
        logger.info(
            "Threshold=%.1f | Precision=%.4f | Recall=%.4f | F1=%.4f | meets_recall=%s",
            t, precision_t, recall_t, f1_t, meets,
        )

    print(separator + "\n")

    # ------------------------------------------------------------------
    # Select best threshold
    # ------------------------------------------------------------------
    candidates = {
        t: m for t, m in threshold_results.items()
        if m["recall"] >= recall_min
    }

    if candidates:
        # Among candidates meeting recall constraint, pick highest precision
        best_threshold: float = max(candidates, key=lambda t: candidates[t]["precision"])
        logger.info(
            "Best threshold: %.1f  (recall=%.4f, precision=%.4f, meets recall>=%.2f)",
            best_threshold,
            threshold_results[best_threshold]["recall"],
            threshold_results[best_threshold]["precision"],
            recall_min,
        )
    else:
        # Fallback: no threshold meets the recall constraint — pick highest recall
        best_threshold = max(threshold_results, key=lambda t: threshold_results[t]["recall"])
        logger.warning(
            "No threshold achieved recall >= %.2f. "
            "Falling back to threshold=%.1f with highest recall=%.4f.",
            recall_min,
            best_threshold,
            threshold_results[best_threshold]["recall"],
        )

    print(
        f"Selected threshold : {best_threshold:.1f}\n"
        f"  Precision : {threshold_results[best_threshold]['precision']:.4f}\n"
        f"  Recall    : {threshold_results[best_threshold]['recall']:.4f}\n"
        f"  F1-score  : {threshold_results[best_threshold]['f1']:.4f}"
    )

    return best_threshold, threshold_results


# ---------------------------------------------------------------------------


def plot_calibration_curve(
    model: Any,
    X_test: pd.DataFrame | np.ndarray,
    y_test: pd.Series | np.ndarray,
    model_name: str,
) -> None:
    """Plot and save a reliability diagram (calibration curve) for a model.

    The plot shows:
    * The calibration curve — observed positive rate vs. mean predicted
      probability per bin.
    * A diagonal perfect-calibration reference line.
    * A histogram of predicted probability values in the secondary axis.

    The figure is saved to ``<config.REPORTS_DIR>/calibration_{model_name}.png``.

    Parameters
    ----------
    model : Any
        Fitted classifier implementing ``predict_proba(X)``.
    X_test : pd.DataFrame | np.ndarray
        Feature matrix for the held-out test set.
    y_test : pd.Series | np.ndarray
        True binary labels.
    model_name : str
        Used in the plot title and output filename.

    Returns
    -------
    None
        The plot is saved to disk; nothing is returned.

    Raises
    ------
    RuntimeError
        If the model does not support ``predict_proba``.

    Notes
    -----
    This function uses ``matplotlib`` with the ``Agg`` backend (set at module
    import) so it works in headless environments such as cloud compute nodes
    and CI runners.
    """
    if not hasattr(model, "predict_proba"):
        raise RuntimeError(
            f"Model '{type(model).__name__}' does not implement predict_proba(). "
            "Cannot plot calibration curve."
        )

    y_test_arr = np.asarray(y_test, dtype=int)
    y_prob: np.ndarray = model.predict_proba(X_test)[:, 1]

    n_bins: int = getattr(config, "CALIBRATION_N_BINS", 10)
    fraction_of_positives, mean_predicted_value = calibration_curve(
        y_test_arr, y_prob, n_bins=n_bins, strategy="uniform"
    )

    # ------------------------------------------------------------------
    # Build figure with two subplots
    # ------------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(8, 8),
        gridspec_kw={"height_ratios": [3, 1]},
        sharex=True,
    )

    # --- Reliability diagram ---
    ax1.plot(
        [0, 1],
        [0, 1],
        linestyle="--",
        color="grey",
        label="Perfect calibration",
        linewidth=1.5,
    )
    ax1.plot(
        mean_predicted_value,
        fraction_of_positives,
        marker="o",
        color="#E74C3C",
        linewidth=2,
        markersize=7,
        label=f"{model_name}",
    )
    ax1.fill_between(
        mean_predicted_value,
        fraction_of_positives,
        mean_predicted_value,
        alpha=0.12,
        color="#E74C3C",
        label="Calibration gap",
    )
    ax1.set_ylabel("Fraction of positives", fontsize=12)
    ax1.set_title(
        f"Reliability Diagram — {model_name}\n"
        "(Calibration Curve for Landslide Probability)",
        fontsize=13,
        fontweight="bold",
    )
    ax1.legend(loc="upper left", fontsize=10)
    ax1.set_ylim([-0.05, 1.05])
    ax1.set_xlim([-0.02, 1.02])
    ax1.grid(alpha=0.3)

    # --- Histogram of predicted probabilities ---
    ax2.hist(
        y_prob,
        range=(0, 1),
        bins=n_bins,
        color="#3498DB",
        edgecolor="white",
        alpha=0.85,
    )
    ax2.set_xlabel("Mean predicted probability", fontsize=12)
    ax2.set_ylabel("Count", fontsize=11)
    ax2.set_title("Distribution of predicted probabilities", fontsize=11)
    ax2.grid(alpha=0.3)

    fig.tight_layout(pad=2.0)

    # ------------------------------------------------------------------
    # Save to reports directory
    # ------------------------------------------------------------------
    reports_dir = _ensure_reports_dir()
    safe_name = model_name.replace(" ", "_").replace("/", "-")
    output_path = os.path.join(reports_dir, f"calibration_{safe_name}.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    logger.info("Calibration curve saved -> %s", output_path)
    print(f"Calibration curve saved -> {output_path}")


# ---------------------------------------------------------------------------


def compare_models(
    models_dict: dict[str, Any],
    X_test: pd.DataFrame | np.ndarray,
    y_test: pd.Series | np.ndarray,
) -> tuple[str, Any]:
    """Evaluate multiple models and select the best one by PR-AUC.

    For each model in *models_dict*, :func:`evaluate_model` is called and
    :func:`plot_calibration_curve` is generated.  The model with the highest
    ``pr_auc`` is saved to ``config.BEST_MODEL_PATH`` using ``joblib``.

    Parameters
    ----------
    models_dict : dict[str, Any]
        Mapping of ``model_name`` -> fitted model object.
    X_test : pd.DataFrame | np.ndarray
        Shared held-out feature matrix.
    y_test : pd.Series | np.ndarray
        Shared held-out labels.

    Returns
    -------
    best_model_name : str
        Key in *models_dict* corresponding to the best model.
    best_model : Any
        The fitted model object with the highest PR-AUC.

    Raises
    ------
    ValueError
        If *models_dict* is empty.

    Notes
    -----
    * The saved best-model file can be loaded at inference time via
      ``joblib.load(config.BEST_MODEL_PATH)``.
    * Saving uses ``joblib`` (not ``pickle``) for efficient serialisation of
      large NumPy arrays inside tree ensembles.

    Examples
    --------
    >>> models = {
    ...     "LogisticRegression": lr_model,
    ...     "RandomForest": rf_model,
    ...     "XGBoost": xgb_model,
    ... }
    >>> best_name, best_model = compare_models(models, X_test, y_test)
    >>> print(f"Best model: {best_name}")
    Best model: RandomForest  # EXAMPLE OUTPUT — actual value will vary
    """
    if not models_dict:
        raise ValueError("models_dict is empty — provide at least one trained model.")

    logger.info("Comparing %d models ...", len(models_dict))
    all_metrics: dict[str, dict[str, Any]] = {}

    for name, model in models_dict.items():
        try:
            metrics = evaluate_model(model, X_test, y_test, model_name=name)
            all_metrics[name] = metrics
        except Exception as exc:
            logger.error(
                "Evaluation failed for model '%s': %s", name, exc, exc_info=True
            )
            continue

        try:
            plot_calibration_curve(model, X_test, y_test, model_name=name)
        except Exception as exc:
            logger.warning(
                "Calibration plot failed for '%s': %s — skipping.", name, exc
            )

    if not all_metrics:
        raise RuntimeError("All model evaluations failed. Cannot select best model.")

    # ------------------------------------------------------------------
    # Select best by PR-AUC (with ensemble candidate priority on ties)
    # ------------------------------------------------------------------
    def _candidate_priority(name: str) -> int:
        if "random_forest" in name or "rf" in name:
            return 3
        if "xgboost" in name or "xgb" in name:
            return 2
        return 1

    best_model_name: str = max(
        all_metrics,
        key=lambda n: (all_metrics[n]["pr_auc"], _candidate_priority(n)),
    )
    best_pr_auc: float = all_metrics[best_model_name]["pr_auc"]
    best_model: Any = models_dict[best_model_name]

    logger.info(
        "Best model: '%s'  PR-AUC=%.4f", best_model_name, best_pr_auc
    )

    # ------------------------------------------------------------------
    # Print side-by-side comparison table
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("  MODEL COMPARISON SUMMARY (sorted by PR-AUC desc)")
    print("=" * 78)
    col_w = 18
    header_row = (
        f"{'Model':<{col_w}} | {'Precision':>10} | {'Recall':>8}"
        f" | {'F1':>8} | {'ROC-AUC':>9} | {'PR-AUC':>9}"
    )
    print(header_row)
    print("-" * len(header_row))

    sorted_models = sorted(
        all_metrics.items(), key=lambda kv: kv[1]["pr_auc"], reverse=True
    )
    for mname, m in sorted_models:
        marker = " [BEST]" if mname == best_model_name else "       "
        display = (mname + marker)[:col_w]
        print(
            f"{display:<{col_w}} | "
            f"{m['precision_positive']:>10.4f} | "
            f"{m['recall_positive']:>8.4f} | "
            f"{m['f1_positive']:>8.4f} | "
            f"{m['roc_auc']:>9.4f} | "
            f"{m['pr_auc']:>9.4f}"
        )
    print("=" * 78 + "\n")

    # ------------------------------------------------------------------
    # Persist best model
    # ------------------------------------------------------------------
    best_model_path: str = str(config.BEST_MODEL_PATH)
    os.makedirs(os.path.dirname(os.path.abspath(best_model_path)), exist_ok=True)
    joblib.dump(best_model, best_model_path)
    logger.info("Best model '%s' saved -> %s", best_model_name, best_model_path)
    print(
        f"Best model '{best_model_name}' (PR-AUC={best_pr_auc:.4f}) "
        f"saved -> {best_model_path}"
    )

    return best_model_name, best_model


# ---------------------------------------------------------------------------


def generate_evaluation_report(
    models_eval: dict[str, dict[str, Any]],
    output_path: str | None = None,
) -> str:
    """Build, print, and save a full plain-text evaluation report.

    The report includes:

    * A prototype disclaimer (from ``config.PROTOTYPE_WARNING``).
    * Per-model sections with confusion matrix, precision/recall/F1, ROC-AUC,
      PR-AUC, and top-10 feature importances.
    * A side-by-side model comparison table.
    * The recommended best model (highest PR-AUC).
    * Generation timestamp.

    Parameters
    ----------
    models_eval : dict[str, dict[str, Any]]
        Dict mapping model name -> metrics dict as returned by
        :func:`evaluate_model`.  Can contain results for one or more models.
    output_path : str | None
        File path where the report text will be written.  Defaults to
        ``config.EVALUATION_REPORT_PATH``.  Parent directories are created
        if they do not exist.

    Returns
    -------
    str
        The complete report text (also written to disk and printed to stdout).

    Notes
    -----
    * The report is plain UTF-8 text intentionally, to remain readable in any
      terminal, log viewer, or text editor without additional dependencies.
    * The ``PROTOTYPE_WARNING`` is placed at the top of the report and at the
      bottom, to ensure reviewers do not miss it.

    Examples
    --------
    >>> report = generate_evaluation_report(all_metrics)
    >>> print(report[:200])
    ====== MULTI-HAZARD EARLY WARNING SYSTEM — MODEL EVALUATION REPORT ======
    ...
    """
    if output_path is None:
        output_path = str(config.EVALUATION_REPORT_PATH)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []

    def _line(text: str = "") -> None:
        lines.append(text)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    _line("=" * 74)
    _line("  MULTI-HAZARD EARLY WARNING SYSTEM -- MODEL EVALUATION REPORT")
    _line(f"  Generated : {now_str}")
    _line("  Pipeline  : AI/ML Prediction Pipeline v1.0 (Prototype)")
    _line("  Pilot Area: Sikkim, Himalayan Region, India")
    _line("=" * 74)
    _line()

    # ------------------------------------------------------------------
    # Prototype warning (top)
    # ------------------------------------------------------------------
    prototype_warning: str = getattr(
        config,
        "PROTOTYPE_WARNING",
        "PROTOTYPE: Not validated against real operational data.",
    )
    _line("*** PROTOTYPE WARNING ***")
    _line("-" * 74)
    for chunk in textwrap.wrap(prototype_warning, width=72):
        _line("   " + chunk)
    _line()

    # ------------------------------------------------------------------
    # Per-model sections
    # ------------------------------------------------------------------
    for model_name, m in models_eval.items():
        _line("=" * 74)
        _line(f"  MODEL: {model_name}")
        _line(f"  Evaluated at: {m.get('evaluated_at', 'N/A')}")
        _line("=" * 74)

        # Accuracy
        accuracy = m.get("accuracy", float("nan"))
        _line(f"  Accuracy  : {accuracy:.4f}")
        if accuracy > 0.95:
            _line(
                "  *** WARNING: accuracy > 95% -- may reflect class imbalance. "
                "Prioritise PR-AUC and Recall. ***"
            )
        _line()

        # Confusion matrix
        cm_list = m.get("confusion_matrix", [[0, 0], [0, 0]])
        tn_, fp_ = cm_list[0][0], cm_list[0][1]
        fn_, tp_ = cm_list[1][0], cm_list[1][1]
        _line("  Confusion Matrix (rows=actual, cols=predicted):")
        _line("                  Pred: No-LS   Pred: LS")
        _line(f"  Actual: No-LS     {tn_:>8d}   {fp_:>8d}")
        _line(f"  Actual: LS        {fn_:>8d}   {tp_:>8d}")
        _line()

        # Core metrics
        _line("  Core Metrics (class = landslide / positive):")
        _line(f"    Precision  : {m.get('precision_positive', float('nan')):.4f}")
        _line(
            f"    Recall     : {m.get('recall_positive', float('nan')):.4f}"
            "   <- landslide detection rate (most critical)"
        )
        _line(f"    F1-score   : {m.get('f1_positive', float('nan')):.4f}")
        _line(f"    ROC-AUC    : {m.get('roc_auc', float('nan')):.4f}")
        _line(
            f"    PR-AUC     : {m.get('pr_auc', float('nan')):.4f}"
            "   <- PRIMARY METRIC"
        )
        _line()

        # Feature importance (top 10)
        fi: dict[str, float] | None = m.get("feature_importance")
        if fi:
            _line("  Feature Importance (top 10):")
            for rank, (feat, score) in enumerate(list(fi.items())[:10], start=1):
                _line(f"    {rank:>2}. {feat:<40s} {score:.6f}")
        else:
            _line("  Feature Importance: not available for this model type.")
        _line()

        # Classification report
        cr: dict = m.get("classification_report", {})
        if cr:
            _line("  Classification Report:")
            _line(
                f"    {'Class':<16} {'Precision':>10} {'Recall':>8}"
                f" {'F1':>8} {'Support':>9}"
            )
            _line("    " + "-" * 55)
            for cls_label in ["no_landslide", "landslide"]:
                cls_m = cr.get(cls_label, {})
                _line(
                    f"    {cls_label:<16}"
                    f" {cls_m.get('precision', 0.0):>10.4f}"
                    f" {cls_m.get('recall', 0.0):>8.4f}"
                    f" {cls_m.get('f1-score', 0.0):>8.4f}"
                    f" {int(cls_m.get('support', 0)):>9d}"
                )
            macro = cr.get("macro avg", {})
            _line(
                f"    {'macro avg':<16}"
                f" {macro.get('precision', 0.0):>10.4f}"
                f" {macro.get('recall', 0.0):>8.4f}"
                f" {macro.get('f1-score', 0.0):>8.4f}"
                f" {int(macro.get('support', 0)):>9d}"
            )
        _line()

    # ------------------------------------------------------------------
    # Comparison table
    # ------------------------------------------------------------------
    _line("=" * 74)
    _line("  SIDE-BY-SIDE MODEL COMPARISON")
    _line("=" * 74)
    col_w2 = 22
    _line(
        f"  {'Model':<{col_w2}} | {'Precision':>10} | {'Recall':>8}"
        f" | {'F1':>8} | {'ROC-AUC':>9} | {'PR-AUC':>9}"
    )
    _line("  " + "-" * 72)

    sorted_eval = sorted(
        models_eval.items(), key=lambda kv: kv[1].get("pr_auc", 0.0), reverse=True
    )
    for mname, m in sorted_eval:
        _line(
            f"  {mname:<{col_w2}} | "
            f"{m.get('precision_positive', 0.0):>10.4f} | "
            f"{m.get('recall_positive', 0.0):>8.4f} | "
            f"{m.get('f1_positive', 0.0):>8.4f} | "
            f"{m.get('roc_auc', 0.0):>9.4f} | "
            f"{m.get('pr_auc', 0.0):>9.4f}"
        )

    _line()

    # Best model recommendation
    if sorted_eval:
        best_name = sorted_eval[0][0]
        best_prauc = sorted_eval[0][1].get("pr_auc", 0.0)
        _line(
            f"  [RECOMMENDED] '{best_name}' (PR-AUC = {best_prauc:.4f}) "
            "selected as best model."
        )
    _line()

    # ------------------------------------------------------------------
    # Prototype warning (bottom)
    # ------------------------------------------------------------------
    _line("=" * 74)
    _line("*** REMINDER -- PROTOTYPE WARNING ***")
    _line("-" * 74)
    for chunk in textwrap.wrap(prototype_warning, width=72):
        _line("   " + chunk)
    _line("=" * 74)

    # ------------------------------------------------------------------
    # Assemble full report string
    # ------------------------------------------------------------------
    report: str = "\n".join(lines)

    # Print to stdout
    print(report)

    # Write to disk
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(report)
        fh.write("\n")

    logger.info("Evaluation report saved -> %s", output_path)
    print(f"\nEvaluation report saved -> {output_path}")

    return report
