"""
utils.py — Shared utility functions for the Multi-Hazard Early Warning System AI/ML Pipeline.

Provides:
  - Structured logging setup
  - Data freshness scoring
  - Directory bootstrapping
  - JSON I/O helpers
  - Pretty-printed model comparison tables
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from ml.src.config import (
        DATA_DIR,
        FRESHNESS_THRESHOLDS,
        MODELS_DIR,
        REPORTS_DIR,
    )
except ImportError:
    try:
        from .config import (
            DATA_DIR,
            FRESHNESS_THRESHOLDS,
            MODELS_DIR,
            REPORTS_DIR,
        )
    except ImportError:
        from config import (
            DATA_DIR,
            FRESHNESS_THRESHOLDS,
            MODELS_DIR,
            REPORTS_DIR,
        )

# ─── LOGGING ─────────────────────────────────────────────────────────────────


def setup_logger(name: str, log_level: int = logging.INFO) -> logging.Logger:
    """
    Create and configure a structured logger with timestamp, level, and name.

    The logger writes to stdout with a consistent format that is easy to parse
    by log aggregation tools (Cloud Logging, ELK, etc.).  A second handler at
    WARNING level is attached to stderr so warnings/errors surface even when
    stdout is redirected.

    If a logger with *name* already has handlers attached (e.g. the function
    is called more than once during a session), the existing logger is returned
    as-is to avoid duplicate log lines.

    Args:
        name (str):
            The logger name, typically ``__name__`` of the calling module.
        log_level (int):
            Minimum severity level for the stdout handler.
            Defaults to ``logging.INFO``.

    Returns:
        logging.Logger:
            A fully configured :class:`logging.Logger` instance.

    Example::

        logger = setup_logger(__name__)
        logger.info("Pipeline started.")
        logger.warning("Missing 7 %% of values — imputation will run.")
    """
    logger = logging.getLogger(name)

    # Guard against duplicate handlers when the function is called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(log_level)

    _fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # ── stdout handler (INFO and above) ──────────────────────────────────────
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(_fmt)
    logger.addHandler(stdout_handler)

    # ── stderr handler (WARNING and above) ───────────────────────────────────
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(_fmt)
    logger.addHandler(stderr_handler)

    # Prevent messages from propagating to the root logger
    logger.propagate = False

    return logger


# ─── DATA FRESHNESS ──────────────────────────────────────────────────────────


def compute_data_freshness(
    observation_timestamp: datetime,
    inference_time: Optional[datetime] = None,
) -> Tuple[float, str]:
    """
    Compute a data-freshness score and label for a sensor observation.

    Freshness is defined as how old the observation is relative to the time of
    inference.  Older data contributes less reliable signal for real-time risk
    assessment, so the model down-weights stale inputs via this score.

    The scoring bands are taken from ``config.FRESHNESS_THRESHOLDS``::

        FRESH   : age <  6 h  → score 1.0
        RECENT  : age <  24 h → score 0.7
        STALE   : age <  72 h → score 0.4
        MISSING : age >= 72 h → score 0.0

    Args:
        observation_timestamp (datetime):
            The UTC timestamp at which the observation was recorded.  If the
            datetime is naive (no ``tzinfo``), it is assumed to be UTC.
        inference_time (datetime, optional):
            The reference "now" time used to compute age.  Defaults to
            ``datetime.now(timezone.utc)`` when ``None``.  Pass an explicit
            value in unit tests or batch back-testing runs.

    Returns:
        Tuple[float, str]:
            A ``(score, label)`` pair, e.g. ``(0.7, "RECENT")``.

    Raises:
        TypeError:
            If *observation_timestamp* is not a :class:`datetime` object.

    Example::

        from datetime import datetime, timezone, timedelta
        obs = datetime.now(timezone.utc) - timedelta(hours=10)
        score, label = compute_data_freshness(obs)
        # score == 0.7, label == "RECENT"
    """
    if not isinstance(observation_timestamp, datetime):
        raise TypeError(
            f"observation_timestamp must be a datetime object, "
            f"got {type(observation_timestamp).__name__!r}."
        )

    if inference_time is None:
        inference_time = datetime.now(timezone.utc)

    # Normalise both timestamps to UTC-aware so subtraction is safe
    if observation_timestamp.tzinfo is None:
        observation_timestamp = observation_timestamp.replace(tzinfo=timezone.utc)
    if inference_time.tzinfo is None:
        inference_time = inference_time.replace(tzinfo=timezone.utc)

    age_hours: float = (inference_time - observation_timestamp).total_seconds() / 3600.0

    # Clamp negative age (future-dated observations) to 0
    age_hours = max(0.0, age_hours)

    for label, (low, high, score) in FRESHNESS_THRESHOLDS.items():
        if low <= age_hours < high:
            return score, label

    # Fallback — should never be reached due to MISSING covering [72, inf)
    return 0.0, "MISSING"


# ─── DIRECTORY MANAGEMENT ────────────────────────────────────────────────────


def ensure_dirs() -> None:
    """
    Create the standard pipeline directories if they do not already exist.

    The directories created are::

        ml/data/
        ml/models/
        ml/reports/

    These paths are resolved from ``config.DATA_DIR``, ``config.MODELS_DIR``,
    and ``config.REPORTS_DIR`` respectively, which are all anchored to the
    ``ml/`` root directory via ``config.ROOT_DIR``.

    This function is idempotent — calling it multiple times is safe.

    Returns:
        None

    Example::

        ensure_dirs()  # call once at pipeline entry-point
    """
    for directory in (DATA_DIR, MODELS_DIR, REPORTS_DIR):
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)


# ─── JSON HELPERS ────────────────────────────────────────────────────────────


def load_json(path: Path) -> Dict[str, Any]:
    """
    Load and deserialise a JSON file from *path*.

    Args:
        path (Path):
            Absolute or relative path to a ``.json`` file.

    Returns:
        Dict[str, Any]:
            The parsed JSON content as a Python dictionary.

    Raises:
        FileNotFoundError:
            If *path* does not exist on disk.
        json.JSONDecodeError:
            If the file content is not valid JSON.

    Example::

        metadata = load_json(config.MODEL_METADATA_PATH)
        print(metadata["best_model"])
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(data: Dict[str, Any], path: Path, indent: int = 4) -> None:
    """
    Serialise *data* to a JSON file at *path*, creating parent directories as
    needed.

    Non-serialisable types (e.g. :class:`pathlib.Path`, ``numpy`` scalars) are
    converted to strings via a custom default encoder so the function does not
    raise for common pipeline objects.

    Args:
        data (Dict[str, Any]):
            The dictionary to serialise.
        path (Path):
            Destination file path.  Will be created (along with any missing
            parent directories) if it does not exist.
        indent (int):
            JSON indentation level.  Defaults to ``4`` for human-readable
            output.

    Returns:
        None

    Example::

        save_json({"best_model": "XGBoost", "roc_auc": 0.93},
                  config.MODEL_METADATA_PATH)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    def _default_encoder(obj: Any) -> str:
        """Fallback encoder: convert unknown types to their string repr."""
        if isinstance(obj, Path):
            return str(obj)
        # Handle numpy scalar types without importing numpy (optional dependency)
        if hasattr(obj, "item"):          # numpy scalar
            return obj.item()
        if hasattr(obj, "__float__"):     # other numeric-like
            return float(obj)
        return str(obj)

    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=indent, default=_default_encoder)


# ─── MODEL COMPARISON TABLE ──────────────────────────────────────────────────


def print_summary_table(results_dict: Dict[str, Dict[str, Any]]) -> None:
    """
    Pretty-print a side-by-side model comparison table to stdout.

    Accepts a nested dict of the form::

        {
            "RandomForest": {
                "ROC-AUC":        0.934,
                "PR-AUC":         0.812,
                "F1 (class=1)":   0.756,
                "Precision":      0.801,
                "Recall":         0.715,
                "Brier Score":    0.048,
            },
            "XGBoost": { ... },
            "LogisticRegression": { ... },
        }

    The function first tries to use ``tabulate`` for beautifully formatted
    output.  If ``tabulate`` is not installed, it falls back to a manually
    formatted ASCII table that requires no third-party libraries.

    Args:
        results_dict (Dict[str, Dict[str, Any]]):
            Outer keys are model names; inner keys are metric names; values
            are floats (or strings).

    Returns:
        None  (prints to stdout)

    Example::

        print_summary_table({
            "RF":  {"ROC-AUC": 0.934, "PR-AUC": 0.812},
            "XGB": {"ROC-AUC": 0.951, "PR-AUC": 0.843},
        })
    """
    if not results_dict:
        print("(No results to display.)")
        return

    # Collect all unique metric names in insertion order
    all_metrics: list[str] = []
    for metrics in results_dict.values():
        for key in metrics:
            if key not in all_metrics:
                all_metrics.append(key)

    model_names = list(results_dict.keys())

    # ── Try tabulate first ───────────────────────────────────────────────────
    try:
        from tabulate import tabulate  # type: ignore[import]

        headers = ["Metric"] + model_names
        rows = []
        for metric in all_metrics:
            row = [metric]
            for model in model_names:
                val = results_dict[model].get(metric, "—")
                row.append(f"{val:.4f}" if isinstance(val, float) else str(val))
            rows.append(row)

        print("\n" + "=" * 72)
        print(" MODEL COMPARISON SUMMARY")
        print("=" * 72)
        print(tabulate(rows, headers=headers, tablefmt="github"))
        print("=" * 72 + "\n")
        return

    except ImportError:
        pass  # Fall through to manual formatter

    # ── Manual ASCII table formatter ─────────────────────────────────────────
    col_width_metric = max(len(m) for m in all_metrics) + 2  # left column
    col_width_model = 14  # fixed width per model column

    def _fmt_val(val: Any) -> str:
        if isinstance(val, float):
            return f"{val:.4f}"
        return str(val)

    # Header row
    header_parts = [f"{'Metric':<{col_width_metric}}"]
    for model in model_names:
        header_parts.append(f"{model:^{col_width_model}}")
    header = " | ".join(header_parts)
    sep = "-" * len(header)

    print("\n" + "=" * len(header))
    print(" MODEL COMPARISON SUMMARY")
    print("=" * len(header))
    print(header)
    print(sep)

    for metric in all_metrics:
        row_parts = [f"{metric:<{col_width_metric}}"]
        for model in model_names:
            val = results_dict[model].get(metric, "—")
            row_parts.append(f"{_fmt_val(val):^{col_width_model}}")
        print(" | ".join(row_parts))

    print("=" * len(header) + "\n")