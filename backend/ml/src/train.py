"""
ml/src/train.py
================
Model Training Pipeline — AI-Assisted Multi-Hazard Early Warning System
Member 3 Responsibility: AI/ML Prediction

This module handles all model training for the three baseline classifiers:
  1. Logistic Regression  — interpretable linear baseline
  2. Random Forest        — primary tree-ensemble candidate
  3. XGBoost              — gradient-boosting candidate

Training philosophy:
  - Temporal train/test split to prevent data leakage across time.
  - Class-imbalance handling via class_weight / scale_pos_weight rather than
    synthetic oversampling, which can introduce artificial correlations.
  - StratifiedKFold cross-validation to get reliable metric estimates without
    shuffling the temporal order.
  - All hyper-parameters sourced from config.py — no magic numbers here.

SCALABILITY NOTES:
  1. MODEL SERVING: This pipeline can be wrapped in a FastAPI service and deployed
     as a Docker container on GCP Cloud Run (auto-scaling) or AWS ECS.

  2. BATCH GRID INFERENCE: For heatmap generation over a 100x100 grid:
     - Use joblib.Parallel(n_jobs=-1) for multi-core local inference.
     - For cloud: parallelize via GCP Dataflow or AWS Lambda per grid cell.

  3. MODEL RETRAINING: The train.py pipeline can be scheduled as a Cloud Run Job
     (daily/weekly) when new historical landslide data becomes available.

  4. DATA INGESTION SCALING: Replace data_loader.py stub with:
     - NASA Earthdata API connector for GPM IMERG (authenticated)
     - Google Earth Engine Python API for Sentinel-2 NDVI
     - IMD API connector (requires IP whitelisting)
     - ESP32 sensor -> MQTT -> backend -> DB pipeline

  5. VECTOR DATABASE (optional for RAG on historical data):
     Store embeddings of historical landslide reports in Pinecone/ChromaDB
     for semantic similarity retrieval during risk context generation.

  6. MULTI-INPUT TYPE SUPPORT:
     The predict_risk() function accepts:
     - JSON dict (from API call)
     - pandas DataFrame row (batch mode)
     - CSV file path (batch processing)

Usage (from ml/):
    python run_training.py
    -- or --
    from ml.src.train import train_all_models
"""

from __future__ import annotations

import json
import logging
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold

# ---------------------------------------------------------------------------
# Config import — config.py is the single source of truth for all constants.
# If config.py is not yet present, fall back to inline defaults so this module
# can be tested independently; a RuntimeWarning is emitted.
# ---------------------------------------------------------------------------
try:
    from ml.src import config  # type: ignore[import]
except ModuleNotFoundError:
    try:
        import config  # type: ignore[import]  # running from src/ directly
    except ModuleNotFoundError:
        warnings.warn(
            "config.py not found — using inline fallback defaults. "
            "Create ml/src/config.py before running the full pipeline.",
            RuntimeWarning,
            stacklevel=2,
        )

        class _FallbackConfig:  # pragma: no cover
            """Inline fallback constants when config.py is absent."""

            # File-system paths
            MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

            # Logistic Regression hyper-parameters
            LR_PARAMS: dict[str, Any] = {
                "class_weight": "balanced",
                "max_iter": 1000,
                "random_state": 42,
            }

            # Random Forest hyper-parameters
            RF_PARAMS: dict[str, Any] = {
                "n_estimators": 200,
                "max_depth": None,
                "min_samples_leaf": 5,
                "class_weight": "balanced",
                "oob_score": True,
                "n_jobs": -1,
                "random_state": 42,
            }

            # XGBoost hyper-parameters (scale_pos_weight excluded — computed at runtime)
            XGB_PARAMS: dict[str, Any] = {
                "n_estimators": 300,
                "max_depth": 6,
                "learning_rate": 0.05,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "eval_metric": "aucpr",
                "random_state": 42,
                "tree_method": "hist",
            }

        config = _FallbackConfig()  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


# ===========================================================================
# 1. Temporal Train / Test Split
# ===========================================================================

def temporal_train_test_split(
    df: pd.DataFrame,
    feature_names: list[str],
    train_ratio: float = 0.80,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Perform a **temporal** train/test split on the dataset.

    Events are sorted chronologically by the ``timestamp`` column and then
    partitioned: the earliest ``train_ratio`` fraction goes to training and the
    remaining (most recent) fraction forms the test set.

    .. important::
        **CRITICAL — Data Leakage Prevention:**
        This ordering is mandatory for geospatial hazard prediction.
        A *random* split would allow future observations to "inform" past model
        training, artificially inflating evaluation metrics.

        **Storm-event leakage:** Events from the same storm system should NOT
        appear in both train and test sets. Because we sort by timestamp,
        continuous storm sequences land entirely in one partition.  However,
        if the dataset contains an explicit ``storm_id`` or ``event_cluster_id``
        column, consider a group-aware split (GroupShuffleSplit / LeaveOneGroupOut)
        to completely eliminate within-storm leakage.

    Args:
        df: Full cleaned and feature-engineered DataFrame. Must contain a
            ``timestamp`` column and a ``landslide_occurred`` target column.
        feature_names: Ordered list of feature column names used as model inputs.
            These columns must exist in ``df``.
        train_ratio: Fraction of data (by row count after temporal sort) to
            assign to the training set. Default is ``0.80`` (80 / 20 split).

    Returns:
        A 4-tuple ``(X_train, X_test, y_train, y_test)`` where:

        * ``X_train`` — DataFrame of training features.
        * ``X_test``  — DataFrame of test features.
        * ``y_train`` — Series of training labels (``landslide_occurred``).
        * ``y_test``  — Series of test labels (``landslide_occurred``).

    Raises:
        KeyError: If ``timestamp`` or ``landslide_occurred`` columns are absent.
        ValueError: If ``train_ratio`` is not in the open interval (0, 1).

    Example:
        >>> X_train, X_test, y_train, y_test = temporal_train_test_split(
        ...     df, feature_names, train_ratio=0.80
        ... )
    """
    if not (0.0 < train_ratio < 1.0):
        raise ValueError(
            f"train_ratio must be in (0, 1), got {train_ratio!r}."
        )
    if "timestamp" not in df.columns:
        raise KeyError(
            "'timestamp' column is required for temporal splitting but was not "
            "found in the DataFrame."
        )
    if "landslide_occurred" not in df.columns:
        raise KeyError(
            "'landslide_occurred' target column is missing from the DataFrame."
        )

    missing_features = [f for f in feature_names if f not in df.columns]
    if missing_features:
        raise KeyError(
            f"The following feature columns are missing from the DataFrame: "
            f"{missing_features}"
        )

    logger.info(
        "Performing temporal train/test split | train_ratio=%.2f | "
        "input shape=%s",
        train_ratio,
        df.shape,
    )

    # -----------------------------------------------------------------------
    # Sort by timestamp — ascending (oldest first, newest last).
    # This prevents data leakage across time.
    #
    # CRITICAL: Events from the same storm should NOT appear in both train
    # and test sets. A strict temporal ordering ensures that the model is
    # always evaluated on data it has never "seen" temporally — mirroring
    # real operational conditions where inference happens on future events.
    # -----------------------------------------------------------------------
    df_sorted = df.sort_values("timestamp", ascending=True).reset_index(drop=True)

    split_idx = int(len(df_sorted) * train_ratio)

    train_df = df_sorted.iloc[:split_idx]
    test_df = df_sorted.iloc[split_idx:]

    X_train: pd.DataFrame = train_df[feature_names].reset_index(drop=True)
    X_test: pd.DataFrame = test_df[feature_names].reset_index(drop=True)
    y_train: pd.Series = train_df["landslide_occurred"].reset_index(drop=True)
    y_test: pd.Series = test_df["landslide_occurred"].reset_index(drop=True)

    # Log class distribution so imbalance is visible in the training log.
    _log_class_distribution("TRAIN", y_train)
    _log_class_distribution("TEST", y_test)

    logger.info(
        "Split complete | train=%d rows | test=%d rows | "
        "earliest_train=%s | latest_test=%s",
        len(train_df),
        len(test_df),
        str(train_df["timestamp"].iloc[0])[:10],
        str(test_df["timestamp"].iloc[-1])[:10],
    )

    return X_train, X_test, y_train, y_test


def _log_class_distribution(split_name: str, y: pd.Series) -> None:
    """Log positive/negative class counts and prevalence for a label Series.

    Args:
        split_name: Human-readable label for the split (e.g., ``'TRAIN'``).
        y: Binary label Series (0 = non-event, 1 = landslide).
    """
    n_total = len(y)
    n_pos = int(y.sum())
    n_neg = n_total - n_pos
    prevalence = n_pos / n_total * 100.0 if n_total > 0 else 0.0
    logger.info(
        "[%s] total=%d | positives=%d (%.2f%%) | negatives=%d",
        split_name,
        n_total,
        n_pos,
        prevalence,
        n_neg,
    )


# ===========================================================================
# 2. Logistic Regression
# ===========================================================================

def train_logistic_regression(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> LogisticRegression:
    """Train a Logistic Regression classifier using parameters from ``config.LR_PARAMS``.

    Logistic Regression serves as the **interpretable linear baseline**.  Its
    coefficients can be inspected directly to understand the linear contribution
    of each feature without SHAP, which is useful for rapid sanity-checking.

    Class imbalance is handled via ``class_weight='balanced'``, which re-weights
    each sample so that minority-class errors are penalised more heavily.  This
    avoids the need for synthetic oversampling (SMOTE), which can introduce
    spatial autocorrelation artefacts in geospatial datasets.

    Args:
        X_train: Training feature matrix. Shape ``(n_samples, n_features)``.
            For Logistic Regression, features should already be scaled
            (e.g., via ``StandardScaler``) — scaling is assumed to have been
            applied upstream in the preprocessing pipeline.
        y_train: Binary training labels (0 = non-event, 1 = landslide).
            Shape ``(n_samples,)``.

    Returns:
        A fitted ``sklearn.linear_model.LogisticRegression`` instance.

    Example:
        >>> model = train_logistic_regression(X_train, y_train)
        >>> model.predict_proba(X_test)[:, 1]   # risk probabilities
    """
    params: dict[str, Any] = dict(config.LR_PARAMS)
    logger.info("Training Logistic Regression | params=%s", params)

    model = LogisticRegression(**params)
    model.fit(X_train, y_train)

    converged = bool(model.n_iter_[0] < params.get("max_iter", 1000))
    if not converged:
        logger.warning(
            "Logistic Regression did NOT converge after %d iterations. "
            "Consider increasing max_iter in config.LR_PARAMS.",
            params.get("max_iter", 1000),
        )

    logger.info(
        "Logistic Regression training complete | n_iter=%d | converged=%s",
        model.n_iter_[0],
        converged,
    )
    return model


# ===========================================================================
# 3. Random Forest
# ===========================================================================

def train_random_forest(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> RandomForestClassifier:
    """Train a Random Forest classifier using parameters from ``config.RF_PARAMS``.

    Random Forest is the **primary candidate model** for this pipeline.
    It is preferred over a single decision tree because it:
      * Averages out variance via bootstrap aggregation (bagging).
      * Produces naturally calibrated probability estimates for imbalanced data
        when combined with ``class_weight='balanced'``.
      * Handles mixed feature scales without requiring normalisation.

    Key hyper-parameter rationale
    ------------------------------
    ``oob_score=True``
        The out-of-bag (OOB) samples are the ~37 % of rows excluded from each
        bootstrap replicate during training.  The OOB score provides an
        **unbiased internal validation estimate** without requiring a separate
        validation fold.  This is especially valuable when the dataset is small
        or when cross-validation is expensive.  It also serves as a quick
        sanity-check: if OOB accuracy is substantially lower than CV accuracy,
        the model may be overfitting to specific bootstrap replicates.

    ``min_samples_leaf=5``
        Prevents individual leaves from being fit to fewer than 5 samples.
        This acts as implicit regularisation — it **smooths probability
        estimates in imbalanced geospatial data** where some terrain cells
        contain very few historical events.  Without this guard, leaves
        containing a single landslide event would emit probability = 1.0,
        making the model overconfident.  A value of 5 balances bias vs. variance
        for this prototype's ~5,000-row dataset.

    ``n_jobs=-1``
        Uses all available CPU cores for parallel tree construction.  This is
        **critical for inference at scale**: when computing a risk heatmap
        over a 100 x 100 grid of Sikkim, all 10,000 cells can be evaluated
        simultaneously rather than sequentially.  In a Cloud Run environment
        this enables sub-second batch inference per grid.

    Args:
        X_train: Training feature matrix. Shape ``(n_samples, n_features)``.
            Random Forest is scale-invariant; features do NOT need to be
            standardised before being passed here.
        y_train: Binary training labels (0 = non-event, 1 = landslide).
            Shape ``(n_samples,)``.

    Returns:
        A fitted ``sklearn.ensemble.RandomForestClassifier`` instance with
        ``oob_score_`` populated.

    Raises:
        RuntimeError: If OOB score computation fails (should not occur with
            ``n_estimators >= 10``).

    Example:
        >>> model = train_random_forest(X_train, y_train)
        >>> print(f"OOB Score: {model.oob_score_:.4f}")
    """
    params: dict[str, Any] = dict(config.RF_PARAMS)
    logger.info("Training Random Forest | params=%s", params)

    model = RandomForestClassifier(**params)
    model.fit(X_train, y_train)

    # ------------------------------------------------------------------
    # OOB score — an unbiased performance estimate computed from the
    # bootstrap samples that were NOT used during each tree's training.
    # Printed prominently so it appears in the console during run_training.py.
    # ------------------------------------------------------------------
    if hasattr(model, "oob_score_"):
        oob = model.oob_score_
        print(f"\n[Random Forest] OOB Score (accuracy-equivalent, unbiased): {oob:.4f}")
        logger.info(
            "Random Forest training complete | n_estimators=%d | OOB score=%.4f",
            model.n_estimators,
            oob,
        )
    else:
        logger.warning(
            "OOB score was not computed — check that oob_score=True is set in "
            "config.RF_PARAMS."
        )

    return model


# ===========================================================================
# 4. XGBoost
# ===========================================================================

def train_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> Any:
    """Train an XGBoost gradient-boosting classifier.

    Uses the ``XGBClassifier`` scikit-learn compatible interface (not the
    lower-level ``xgb.train`` / DMatrix interface) so it integrates cleanly
    with the rest of the sklearn pipeline — i.e., it supports ``fit()``,
    ``predict_proba()``, ``get_params()``, and can be passed to
    :func:`cross_validate_model` without adapters.

    Class imbalance is handled by computing ``scale_pos_weight`` = ratio of
    negative to positive samples at runtime.  This is XGBoost's recommended
    strategy: it scales the gradient contribution of positive (minority) samples
    so that the boosting algorithm allocates more capacity to learning landslide
    patterns rather than fitting the dominant non-event class.

    Base hyper-parameters are sourced from ``config.XGB_PARAMS``.
    ``scale_pos_weight`` is intentionally excluded from config because it must
    be computed from the actual training label distribution at runtime and would
    be stale if the dataset changes.

    Args:
        X_train: Training feature matrix. Shape ``(n_samples, n_features)``.
            XGBoost is scale-invariant; standardisation is not required.
        y_train: Binary training labels (0 = non-event, 1 = landslide).
            Shape ``(n_samples,)``.

    Returns:
        A fitted ``xgboost.XGBClassifier`` instance.

    Raises:
        ImportError: If ``xgboost`` is not installed.
        ValueError: If ``y_train`` contains no positive samples (division by
            zero when computing ``scale_pos_weight``).

    Example:
        >>> model = train_xgboost(X_train, y_train)
        >>> model.predict_proba(X_test)[:, 1]
    """
    try:
        from xgboost import XGBClassifier  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "xgboost is not installed. Install it with: pip install xgboost>=2.0.0"
        ) from exc

    # ------------------------------------------------------------------
    # Compute scale_pos_weight from the training set's label distribution.
    # Formula: n_negatives / n_positives
    #
    # This tells XGBoost to weight each positive sample equivalently to
    # `scale_pos_weight` negative samples, directly counteracting the
    # 1:11.5 class imbalance (400 events vs. 4,600 non-events in prototype).
    # ------------------------------------------------------------------
    n_neg = int((y_train == 0).sum())
    n_pos = int((y_train == 1).sum())

    if n_pos == 0:
        raise ValueError(
            "y_train contains no positive samples (landslide_occurred == 1). "
            "Cannot compute scale_pos_weight. Check your dataset."
        )

    scale_pos_weight = n_neg / n_pos
    logger.info(
        "XGBoost class weights | n_neg=%d | n_pos=%d | scale_pos_weight=%.4f",
        n_neg,
        n_pos,
        scale_pos_weight,
    )

    # Merge config params with the runtime-computed scale_pos_weight.
    # config.XGB_PARAMS must NOT contain scale_pos_weight — it is injected here.
    params: dict[str, Any] = dict(config.XGB_PARAMS)
    params["scale_pos_weight"] = scale_pos_weight

    logger.info("Training XGBoost | params=%s", params)

    model = XGBClassifier(**params)
    model.fit(X_train, y_train)

    logger.info(
        "XGBoost training complete | best_iteration=%s | best_score=%s",
        getattr(model, "best_iteration", "N/A"),
        getattr(model, "best_score", "N/A"),
    )
    return model


# ===========================================================================
# 5. Cross-Validation
# ===========================================================================

def cross_validate_model(
    model: Any,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_splits: int = 5,
) -> dict[str, float]:
    """Run stratified k-fold cross-validation and return mean +/- std for key metrics.

    Uses ``StratifiedKFold(shuffle=False)`` to preserve temporal order as much
    as possible.  Shuffling would randomly interleave future observations into
    past folds, re-introducing the temporal leakage we eliminate in the main
    train/test split.  Stratification ensures each fold maintains the minority-
    class ratio, which is critical for reliable PR-AUC estimation on the
    imbalanced landslide dataset.

    Metrics computed per fold:
      * **Precision**   (positive predictive value — minimise false alarms)
      * **Recall**      (sensitivity — landslide detection rate; PRIMARY concern)
      * **F1**          (harmonic mean of precision and recall)
      * **ROC-AUC**     (area under receiver-operating-characteristic curve)
      * **PR-AUC**      (area under precision-recall curve; primary metric for
                         imbalanced hazard prediction — more informative than
                         ROC-AUC when positives are rare)

    Args:
        model: A scikit-learn compatible estimator with ``fit()``,
            ``predict_proba()``, and ``get_params()`` methods.  The model is
            re-instantiated from its ``get_params()`` dict on each fold so that
            the original fitted model remains unchanged after the call.
        X_train: Feature matrix for the training partition. Shape
            ``(n_samples, n_features)``.
        y_train: Binary label Series for the training partition.
            Shape ``(n_samples,)``.
        n_splits: Number of cross-validation folds. Default is ``5``.

    Returns:
        Dictionary containing mean and standard deviation for each metric::

            {
                "precision_mean": float,
                "precision_std":  float,
                "recall_mean":    float,
                "recall_std":     float,
                "f1_mean":        float,
                "f1_std":         float,
                "roc_auc_mean":   float,
                "roc_auc_std":    float,
                "pr_auc_mean":    float,
                "pr_auc_std":     float,
            }

    Raises:
        ValueError: If ``n_splits < 2``.

    Example:
        >>> scores = cross_validate_model(rf_model, X_train, y_train)
        >>> print(f"PR-AUC: {scores['pr_auc_mean']:.3f} +/- {scores['pr_auc_std']:.3f}")
    """
    if n_splits < 2:
        raise ValueError(f"n_splits must be >= 2, got {n_splits!r}.")

    logger.info(
        "Starting %d-fold cross-validation for %s",
        n_splits,
        type(model).__name__,
    )

    # StratifiedKFold with shuffle=False to preserve temporal order approximately.
    # shuffle=False means folds are taken as contiguous slices of the data,
    # which (after the temporal sort) corresponds to chronological segments.
    skf = StratifiedKFold(n_splits=n_splits, shuffle=False)

    # Accumulate per-fold metric scores.
    fold_metrics: dict[str, list[float]] = {
        "precision": [],
        "recall": [],
        "f1": [],
        "roc_auc": [],
        "pr_auc": [],
    }

    X_arr = X_train.values if isinstance(X_train, pd.DataFrame) else np.asarray(X_train)
    y_arr = y_train.values if isinstance(y_train, pd.Series) else np.asarray(y_train)

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X_arr, y_arr), start=1):
        X_fold_train, X_fold_val = X_arr[train_idx], X_arr[val_idx]
        y_fold_train, y_fold_val = y_arr[train_idx], y_arr[val_idx]

        # Clone the model by re-creating it with the same hyper-parameters.
        # This avoids contaminating the caller's already-fitted instance and
        # ensures each fold trains from scratch.
        fold_model = type(model)(**model.get_params())
        fold_model.fit(X_fold_train, y_fold_train)

        # Obtain probability scores for the positive class (column index 1).
        if hasattr(fold_model, "predict_proba"):
            y_prob = fold_model.predict_proba(X_fold_val)[:, 1]
        else:
            # Fallback for models that expose only decision_function (e.g. SVM).
            y_prob = fold_model.decision_function(X_fold_val)

        # Apply default 0.5 threshold to obtain hard predictions for
        # precision / recall / F1.  Threshold tuning is done in evaluate.py.
        y_pred = (y_prob >= 0.5).astype(int)

        precision = precision_score(y_fold_val, y_pred, zero_division=0)
        recall = recall_score(y_fold_val, y_pred, zero_division=0)
        f1 = f1_score(y_fold_val, y_pred, zero_division=0)
        roc_auc = roc_auc_score(y_fold_val, y_prob)
        pr_auc = average_precision_score(y_fold_val, y_prob)

        fold_metrics["precision"].append(precision)
        fold_metrics["recall"].append(recall)
        fold_metrics["f1"].append(f1)
        fold_metrics["roc_auc"].append(roc_auc)
        fold_metrics["pr_auc"].append(pr_auc)

        logger.debug(
            "Fold %d/%d | precision=%.4f | recall=%.4f | f1=%.4f | "
            "roc_auc=%.4f | pr_auc=%.4f",
            fold_idx,
            n_splits,
            precision,
            recall,
            f1,
            roc_auc,
            pr_auc,
        )

    # Compute mean +/- std across all folds.
    cv_scores: dict[str, float] = {}
    for metric_name, values in fold_metrics.items():
        arr = np.array(values, dtype=float)
        cv_scores[f"{metric_name}_mean"] = float(np.mean(arr))
        cv_scores[f"{metric_name}_std"] = float(np.std(arr))

    logger.info(
        "CV complete for %s | "
        "PR-AUC=%.4f +/- %.4f | Recall=%.4f +/- %.4f | "
        "F1=%.4f +/- %.4f | ROC-AUC=%.4f +/- %.4f | "
        "Precision=%.4f +/- %.4f",
        type(model).__name__,
        cv_scores["pr_auc_mean"],    cv_scores["pr_auc_std"],
        cv_scores["recall_mean"],    cv_scores["recall_std"],
        cv_scores["f1_mean"],        cv_scores["f1_std"],
        cv_scores["roc_auc_mean"],   cv_scores["roc_auc_std"],
        cv_scores["precision_mean"], cv_scores["precision_std"],
    )

    return cv_scores


# ===========================================================================
# 6. Model Persistence
# ===========================================================================

def save_model(
    model: Any,
    model_name: str,
    cv_scores: dict[str, float],
    feature_names: list[str],
    training_shape: tuple[int, int],
) -> None:
    """Serialise a trained model and its metadata to disk.

    Two artefacts are written:

    1. **``<model_name>.joblib``** — the serialised model binary, saved to
       ``config.MODELS_DIR`` with compression level 3 for a balance of file
       size and de-serialisation speed.
    2. **``model_metadata.json``** — a human-readable JSON file in the same
       directory containing provenance information that can be audited without
       loading the model binary.  If the file already exists, the new model's
       entry is merged in so all model records coexist in one file.

    Args:
        model: Any fitted scikit-learn compatible model instance.
        model_name: Filesystem-safe name for this model
            (e.g., ``"random_forest"``, ``"xgboost"``).  Used as the stem of
            the output ``.joblib`` filename.
        cv_scores: Dictionary of cross-validation metric means and standard
            deviations as returned by :func:`cross_validate_model`.
        feature_names: Ordered list of feature names the model was trained on.
            Stored in metadata for reproducibility and inference-time validation.
        training_shape: ``(n_rows, n_cols)`` tuple describing the training
            feature matrix dimensions.

    Returns:
        None.  Side effect: writes files to ``config.MODELS_DIR``.

    Raises:
        OSError: If ``config.MODELS_DIR`` cannot be created or written to.

    Example:
        >>> save_model(rf_model, "random_forest", cv_scores, feature_names, (4000, 22))
    """
    models_dir = Path(config.MODELS_DIR)
    models_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Serialise the model binary via joblib.
    # joblib is preferred over pickle for numpy-heavy objects (arrays,
    # decision trees) because it uses memory-mapped compression that is
    # significantly faster for large scikit-learn / XGBoost models.
    # compress=3 gives a good size/speed trade-off (~50% reduction vs raw).
    # ------------------------------------------------------------------
    model_path = models_dir / f"{model_name}.joblib"
    joblib.dump(model, model_path, compress=3)
    logger.info("Model saved | path=%s", model_path)

    # ------------------------------------------------------------------
    # 2. Build and write human-readable model_metadata.json.
    # The training_date uses UTC ISO-8601 so records are timezone-unambiguous.
    # ------------------------------------------------------------------
    metadata_entry: dict[str, Any] = {
        "model_name": model_name,
        "model_class": type(model).__name__,
        "training_date": datetime.now(tz=timezone.utc).isoformat(),
        "feature_names": feature_names,
        "n_features": len(feature_names),
        "training_data_shape": {
            "n_samples": training_shape[0],
            "n_features": training_shape[1],
        },
        "cv_scores": cv_scores,
        "hyperparameters": _safe_get_params(model),
        "pipeline_version": "1.0.0",
        "prototype_warning": (
            "This is a prototype system. Risk probabilities are estimates based "
            "on a simulated training dataset. Model has not been validated against "
            "real Himalayan landslide events. Do not use for operational emergency "
            "decisions."
        ),
    }

    metadata_path = models_dir / "model_metadata.json"

    # Merge with existing metadata (one JSON file stores all model records for
    # easy comparison by the evaluate.py and downstream tools).
    existing_metadata: dict[str, Any] = {}
    if metadata_path.exists():
        with metadata_path.open("r", encoding="utf-8") as f:
            try:
                existing_metadata = json.load(f)
            except json.JSONDecodeError:
                logger.warning(
                    "Existing model_metadata.json could not be parsed — "
                    "it will be overwritten."
                )
                existing_metadata = {}

    existing_metadata[model_name] = metadata_entry

    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(existing_metadata, f, indent=2, ensure_ascii=False, default=str)

    logger.info(
        "Metadata saved | path=%s | model_name=%s",
        metadata_path,
        model_name,
    )


def _safe_get_params(model: Any) -> dict[str, Any]:
    """Extract hyper-parameters from a model, converting non-serialisable values.

    Args:
        model: A fitted model with a ``get_params()`` method (scikit-learn API).

    Returns:
        Dictionary of hyper-parameter names to JSON-serialisable values.
        Non-serialisable objects (e.g., callable class weights) are converted
        to their ``repr()`` string so the metadata file remains valid JSON.
    """
    if not hasattr(model, "get_params"):
        return {}
    params = model.get_params()
    safe_params: dict[str, Any] = {}
    for k, v in params.items():
        try:
            json.dumps(v)
            safe_params[k] = v
        except (TypeError, ValueError):
            safe_params[k] = repr(v)
    return safe_params


# ===========================================================================
# 7. Train All Models — Top-Level Orchestration
# ===========================================================================

def train_all_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    feature_names: list[str],
) -> dict[str, tuple[Any, dict[str, float]]]:
    """Train all three baseline classifiers, run cross-validation, and persist them.

    This is the **top-level training orchestration function** called by
    ``run_training.py``.  It trains:
      1. Logistic Regression  (interpretable linear baseline)
      2. Random Forest        (primary tree-ensemble candidate)
      3. XGBoost              (gradient-boosting candidate)

    For each model it:
      * Calls the corresponding ``train_*`` function.
      * Runs 5-fold stratified cross-validation via :func:`cross_validate_model`.
      * Persists the model and metadata via :func:`save_model`.
      * Accumulates results for the comparison table.

    Finally, a side-by-side CV metric comparison table is printed to stdout.

    Args:
        X_train: Training feature matrix. Shape ``(n_samples, n_features)``.
            For Logistic Regression, features must already be scaled upstream
            (e.g., via ``StandardScaler``).  RF and XGBoost are scale-invariant.
        y_train: Binary training labels (0 = non-event, 1 = landslide).
            Shape ``(n_samples,)``.
        feature_names: Ordered list of feature column names.  Must correspond
            to the columns of ``X_train`` in order.  Stored in metadata and
            used for inference-time feature validation.

    Returns:
        A dictionary mapping model names to ``(fitted_model, cv_scores)``
        tuples::

            {
                "logistic_regression": (LogisticRegression, cv_scores_dict),
                "random_forest":       (RandomForestClassifier, cv_scores_dict),
                "xgboost":             (XGBClassifier, cv_scores_dict),
            }

        The ``cv_scores_dict`` keys follow the pattern
        ``"<metric>_mean"`` / ``"<metric>_std"`` for metrics:
        precision, recall, f1, roc_auc, pr_auc.

    Raises:
        ImportError: If XGBoost is not installed (propagated from
            :func:`train_xgboost`).
        KeyError: If feature columns are inconsistent with ``feature_names``.

    Example:
        >>> results = train_all_models(X_train, y_train, feature_names)
        >>> rf_model, rf_scores = results["random_forest"]
        >>> print(f"RF PR-AUC: {rf_scores['pr_auc_mean']:.4f}")
    """
    logger.info(
        "=== Training all models | X_train=%s | positive_rate=%.3f%% ===",
        X_train.shape,
        float(y_train.mean()) * 100.0,
    )

    training_shape: tuple[int, int] = (X_train.shape[0], X_train.shape[1])
    results: dict[str, tuple[Any, dict[str, float]]] = {}

    # ------------------------------------------------------------------
    # Registry of (model_name, train_function) pairs.
    # To add a new model to the pipeline, append an entry here — no other
    # changes to the orchestration logic are required.
    # ------------------------------------------------------------------
    model_registry: list[tuple[str, Any]] = [
        ("logistic_regression", train_logistic_regression),
        ("random_forest",       train_random_forest),
        ("xgboost",             train_xgboost),
    ]

    for model_name, train_fn in model_registry:
        logger.info("--- [%s] Starting training ---", model_name.upper())

        # Train the model.
        model = train_fn(X_train, y_train)

        # Cross-validate on the training split only — the test set must not
        # be touched until final evaluation in evaluate.py.
        cv_scores = cross_validate_model(model, X_train, y_train, n_splits=5)

        # Persist the model binary + metadata JSON.
        save_model(
            model=model,
            model_name=model_name,
            cv_scores=cv_scores,
            feature_names=feature_names,
            training_shape=training_shape,
        )

        results[model_name] = (model, cv_scores)

        logger.info(
            "--- [%s] Done | PR-AUC=%.4f +/- %.4f ---",
            model_name.upper(),
            cv_scores["pr_auc_mean"],
            cv_scores["pr_auc_std"],
        )

    # Print side-by-side CV comparison table to stdout.
    _print_comparison_table(results)

    return results


# ===========================================================================
# Internal helpers
# ===========================================================================

def _print_comparison_table(
    results: dict[str, tuple[Any, dict[str, float]]],
) -> None:
    """Print a side-by-side CV metric comparison table for all trained models.

    Args:
        results: Mapping of model names to ``(model, cv_scores)`` tuples as
            returned by :func:`train_all_models`.
    """
    metrics = ["precision", "recall", "f1", "roc_auc", "pr_auc"]
    col_w = 24   # character width for each metric column
    name_w = 22  # character width for the model-name column

    header_parts = ["Model".ljust(name_w)]
    for m in metrics:
        header_parts.append(m.upper().ljust(col_w))

    total_width = name_w + col_w * len(metrics)
    separator = "-" * total_width

    print("\n" + "=" * total_width)
    print("  CROSS-VALIDATION RESULTS SUMMARY (mean +/- std over 5 folds)")
    print("=" * total_width)
    print("".join(header_parts))
    print(separator)

    for model_name, (_, cv) in results.items():
        row_parts = [model_name.ljust(name_w)]
        for m in metrics:
            mean_val = cv.get(f"{m}_mean", float("nan"))
            std_val  = cv.get(f"{m}_std",  float("nan"))
            cell = f"{mean_val:.4f} +/- {std_val:.4f}"
            row_parts.append(cell.ljust(col_w))
        print("".join(row_parts))

    print(separator)
    print("  PRIMARY METRIC: PR-AUC (precision-recall area under curve)")
    print("  NOTE: High accuracy may reflect class imbalance, not model quality.")
    print("        Always inspect Recall (landslide detection rate) first.")
    print("=" * total_width + "\n")

    # EXAMPLE OUTPUT — actual values will vary depending on the training data:
    # ==============================================================================
    #   CROSS-VALIDATION RESULTS SUMMARY (mean +/- std over 5 folds)
    # ==============================================================================
    # Model                 PRECISION               RECALL                  F1
    # ------------------------------------------------------------------------------
    # logistic_regression   0.5123 +/- 0.0421       0.6812 +/- 0.0534       0.5845
    # random_forest         0.7234 +/- 0.0312       0.7512 +/- 0.0421       0.7370
    # xgboost               0.7456 +/- 0.0298       0.7234 +/- 0.0412       0.7343
    # ==============================================================================
