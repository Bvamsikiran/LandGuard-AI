"""
run_training.py — Master End-to-End AI/ML Training Pipeline Entry Point
=======================================================================
Member 3 Responsibility: AI/ML Prediction Pipeline
Multi-Hazard Early Warning and Cascade Risk Assessment System (Sikkim Prototype)

Usage:
    cd ml/
    python run_training.py

Pipeline Steps:
  1. Bootstraps directories (ml/data/, ml/models/, ml/reports/)
  2. Ingests or generates realistic synthetic training dataset for Sikkim
  3. Executes data cleaning, validation, and median/mode imputation
  4. Performs feature engineering (rainfall windows, intensity, anomaly, log transforms, one-hot encoding)
  5. Performs temporal train/test split (earliest 80% train, latest 20% test) to prevent storm-event leakage
  6. Trains 3 baseline classifiers: Logistic Regression, Random Forest, XGBoost with class weighting
  7. Conducts 5-fold cross-validation and computes precision, recall, F1, ROC-AUC, and PR-AUC
  8. Evaluates held-out test performance and selects best model based on PR-AUC
  9. Generates global SHAP summary plot and high-risk local explanation force plot
 10. Persists all model binaries, preprocessors, metadata JSON, and plain-text evaluation reports
 11. Prints final side-by-side model comparison table
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

# Add project root and ml directory to sys.path so modules import reliably
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from ml.src import (
        config,
        data_loader,
        evaluate,
        explain,
        features,
        preprocessing,
        train,
        utils,
    )
except ImportError:
    from src import (
        config,
        data_loader,
        evaluate,
        explain,
        features,
        preprocessing,
        train,
        utils,
    )

logger = utils.setup_logger("ml.run_training", log_level=logging.INFO)


def main() -> None:
    """Execute the end-to-end training pipeline."""
    start_time = time.time()

    print("\n" + "=" * 80)
    print(" MULTI-HAZARD EARLY WARNING SYSTEM — AI/ML TRAINING PIPELINE (SIKKIM)")
    print("=" * 80)
    print(f"Prototype Status: {config.PROTOTYPE_WARNING}\n")

    # -------------------------------------------------------------------------
    # Step 1: Ensure Directories Exist
    # -------------------------------------------------------------------------
    logger.info("Step 1/8: Initializing pipeline directories...")
    utils.ensure_dirs()

    # -------------------------------------------------------------------------
    # Step 2: Ingest / Generate Training Data
    # -------------------------------------------------------------------------
    logger.info("Step 2/8: Ingesting dataset...")
    df_raw = data_loader.load_training_data(
        filepath=config.TRAINING_DATA_PATH,
        chunksize=config.CSV_CHUNK_SIZE,
    )
    logger.info(f"Loaded {len(df_raw)} records with columns: {list(df_raw.columns)[:8]}...")

    # -------------------------------------------------------------------------
    # Step 3: Preprocessing, Validation & Imputation
    # -------------------------------------------------------------------------
    logger.info("Step 3/8: Preprocessing and validating observations...")
    df_clean, val_report = preprocessing.preprocess_pipeline(
        df_raw,
        fit=True,
        preprocessor_path=config.PREPROCESSOR_PATH,
    )
    logger.info(
        f"Validation summary: {val_report['clean_rows']} clean rows | "
        f"Duplicates dropped: {val_report['duplicates_dropped']} | "
        f"Future timestamps flagged: {val_report['future_timestamps_flagged']}"
    )

    # -------------------------------------------------------------------------
    # Step 4: Feature Engineering
    # -------------------------------------------------------------------------
    logger.info("Step 4/8: Running feature engineering transformations...")
    df_fe, feature_names = features.run_feature_engineering(df_clean)
    logger.info(f"Generated {len(feature_names)} model features.")

    # -------------------------------------------------------------------------
    # Step 5: Temporal Train / Test Split (Prevent Storm Leakage)
    # -------------------------------------------------------------------------
    logger.info("Step 5/8: Performing temporal train/test split (80/20)...")
    X_train, X_test, y_train, y_test = train.temporal_train_test_split(
        df_fe,
        feature_names=feature_names,
        train_ratio=config.TEMPORAL_TRAIN_RATIO,
    )
    logger.info(
        f"Partition sizes: Train={len(X_train)} (positives={int(y_train.sum())}), "
        f"Test={len(X_test)} (positives={int(y_test.sum())})"
    )

    # -------------------------------------------------------------------------
    # Step 6: Train Baseline Models with Class Imbalance Strategy
    # -------------------------------------------------------------------------
    logger.info("Step 6/8: Training baseline models (Logistic Regression, Random Forest, XGBoost)...")
    trained_models = train.train_all_models(
        X_train,
        y_train,
        feature_names=feature_names,
    )

    # Extract fitted models dictionary
    models_dict = {name: model for name, (model, cv_scores) in trained_models.items()}

    # -------------------------------------------------------------------------
    # Step 7: Evaluate Models, Compare by PR-AUC, and Generate Reports
    # -------------------------------------------------------------------------
    logger.info("Step 7/8: Evaluating models on held-out temporal test set...")

    eval_results = {}
    for name, model in models_dict.items():
        metrics = evaluate.evaluate_model(model, X_test, y_test, model_name=name)
        eval_results[name] = metrics

    # Compare models, select best by PR-AUC, and persist best_model.joblib
    best_model_name, best_model = evaluate.compare_models(models_dict, X_test, y_test)

    # Write evaluation report to disk
    report_text = evaluate.generate_evaluation_report(
        eval_results,
        output_path=str(config.EVALUATION_REPORT_PATH),
    )
    logger.info(f"Evaluation report written to {config.EVALUATION_REPORT_PATH}")

    # -------------------------------------------------------------------------
    # Step 8: SHAP Explainability (Global + Local High-Risk Force Plot)
    # -------------------------------------------------------------------------
    logger.info(f"Step 8/8: Generating SHAP explainability visualizations for {best_model_name}...")
    try:
        explain_artifacts = explain.run_explainability(
            best_model,
            X_test=X_test,
            feature_names=feature_names,
            model_name=best_model_name,
        )
        logger.info(f"SHAP summary saved -> {explain_artifacts.get('shap_summary_path')}")
        logger.info(f"SHAP force plot saved -> {explain_artifacts.get('force_plot_path')}")
    except Exception as ex:
        logger.warning(f"SHAP generation encountered a non-fatal warning: {ex}")

    # -------------------------------------------------------------------------
    # Final Comparison Summary
    # -------------------------------------------------------------------------
    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f" PIPELINE EXECUTION COMPLETED IN {elapsed:.1f} SECONDS")
    print("=" * 80)
    print(f" Best Selected Model: {best_model_name.upper()} (PR-AUC = {eval_results[best_model_name]['pr_auc']:.4f})")
    print(f" Artifacts Saved:")
    print(f"   - Best Model:          {config.BEST_MODEL_PATH}")
    print(f"   - Preprocessor:        {config.PREPROCESSOR_PATH}")
    print(f"   - Model Metadata:      {config.MODEL_METADATA_PATH}")
    print(f"   - Evaluation Report:   {config.EVALUATION_REPORT_PATH}")
    print(f"   - SHAP Summary:        {config.SHAP_SUMMARY_PATH}")
    print(f"   - SHAP Force Plot:     {config.SHAP_FORCE_PATH}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
