"""Quantitative analysis toolkit (numpy only) for confirmatory evidence.

- Error metrics: MAE, RMSE, MAPE, R2, and ASHRAE Guideline 14 style CV(RMSE) and NMBE
  (returned as fractions; multiply by 100 for percent). Thresholds belong in
  ``evidence/analysis_plan.json``, not here.
- Uncertainty: seeded percentile bootstrap, with moving-block resampling for
  autocorrelated time series.
- Comparison: paired bootstrap of loss differences, sign-flip permutation test,
  Diebold-Mariano test with Harvey-Leybourne-Newbold correction, skill score,
  effect sizes (paired Cohen's d_z, Cliff's delta).
- Multiplicity: Holm and Benjamini-Hochberg adjusted p-values.
- Leakage control: rolling-origin time-series splits with a gap and a temporal
  leakage check.

CLI ``evaluate`` turns a CSV of observed/predicted (and optional baseline) columns into
a JSON result whose values can be copied into ``evidence/claims.csv``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Callable, Iterable, Iterator, Sequence

import numpy as np

ArrayLike = Sequence[float] | np.ndarray


def _pair(y: ArrayLike, yhat: ArrayLike) -> tuple[np.ndarray, np.ndarray]:
    y, yhat = np.asarray(y, dtype=float), np.asarray(yhat, dtype=float)
    if y.shape != yhat.shape:
        raise ValueError("observed and predicted must have the same shape")
    if np.isnan(y).any() or np.isnan(yhat).any():
        raise ValueError("NaN in inputs; drop or impute explicitly before evaluation")
    return y, yhat


def mae(y: ArrayLike, yhat: ArrayLike) -> float:
    y, yhat = _pair(y, yhat)
    return float(np.mean(np.abs(y - yhat)))


def rmse(y: ArrayLike, yhat: ArrayLike) -> float:
    y, yhat = _pair(y, yhat)
    return float(np.sqrt(np.mean((y - yhat) ** 2)))


def mape(y: ArrayLike, yhat: ArrayLike) -> float:
    y, yhat = _pair(y, yhat)
    if np.any(y == 0):
        raise ValueError("MAPE undefined with zero observations; use CV(RMSE) or MAE")
    return float(np.mean(np.abs((y - yhat) / y)))


def r2(y: ArrayLike, yhat: ArrayLike) -> float:
    y, yhat = _pair(y, yhat)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return float(1 - np.sum((y - yhat) ** 2) / ss_tot) if ss_tot else float("nan")


def cv_rmse(y: ArrayLike, yhat: ArrayLike, n_parameters: int = 0) -> float:
    """sqrt(sum((y - yhat)^2) / (n - p)) / mean(y)."""
    y, yhat = _pair(y, yhat)
    dof = len(y) - n_parameters
    if dof <= 0 or y.mean() == 0:
        raise ValueError("CV(RMSE) needs n > p and non-zero mean observation")
    return float(np.sqrt(np.sum((y - yhat) ** 2) / dof) / y.mean())


def nmbe(y: ArrayLike, yhat: ArrayLike, n_parameters: int = 0) -> float:
    """sum(y - yhat) / ((n - p) * mean(y)); positive means the model under-predicts."""
    y, yhat = _pair(y, yhat)
    dof = len(y) - n_parameters
    if dof <= 0 or y.mean() == 0:
        raise ValueError("NMBE needs n > p and non-zero mean observation")
    return float(np.sum(y - yhat) / (dof * y.mean()))


def bootstrap_indices(n: int, rng: np.random.Generator, block_length: int | None = None) -> np.ndarray:
    if not block_length or block_length <= 1:
        return rng.integers(0, n, size=n)
    block_length = min(block_length, n)
    starts = rng.integers(0, n - block_length + 1, size=math.ceil(n / block_length))
    return (starts[:, None] + np.arange(block_length)[None, :]).ravel()[:n]


def bootstrap_ci(
    statistic: Callable[..., float],
    *arrays: ArrayLike,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
    block_length: int | None = None,
) -> dict:
    """Percentile CI; arrays are resampled jointly (paired). Use block_length for time series."""
    data = [np.asarray(a, dtype=float) for a in arrays]
    n = len(data[0])
    if any(len(a) != n for a in data):
        raise ValueError("arrays must have equal length")
    rng = np.random.default_rng(seed)
    estimate = float(statistic(*data))
    draws = np.empty(n_boot)
    for i in range(n_boot):
        idx = bootstrap_indices(n, rng, block_length)
        draws[i] = statistic(*(a[idx] for a in data))
    low, high = np.quantile(draws, [alpha / 2, 1 - alpha / 2])
    return {"estimate": estimate, "ci_low": float(low), "ci_high": float(high), "alpha": alpha,
            "n_boot": n_boot, "seed": seed, "block_length": block_length or 1, "n": n}


def paired_bootstrap_difference(loss_a: ArrayLike, loss_b: ArrayLike, **kwargs) -> dict:
    """CI of mean(loss_a - loss_b). Negative upper bound means A has lower loss than B."""
    return bootstrap_ci(lambda a, b: float(np.mean(a - b)), loss_a, loss_b, **kwargs)


def sign_flip_test(differences: ArrayLike, n_perm: int = 10000, seed: int = 0) -> float:
    """Two-sided paired permutation p-value for mean difference = 0 (assumes exchangeable pairs)."""
    d = np.asarray(differences, dtype=float)
    rng = np.random.default_rng(seed)
    observed = abs(d.mean())
    signs = rng.choice([-1.0, 1.0], size=(n_perm, len(d)))
    null = np.abs((signs * d).mean(axis=1))
    return float((np.sum(null >= observed) + 1) / (n_perm + 1))


def _normal_two_sided(z: float) -> float:
    return float(math.erfc(abs(z) / math.sqrt(2)))


def diebold_mariano(errors_a: ArrayLike, errors_b: ArrayLike, horizon: int = 1, power: int = 2) -> dict:
    """DM test of equal predictive accuracy with HLN small-sample correction.

    Loss is |e|^power. Negative statistic means model A is more accurate. The p-value uses
    the normal approximation (HLN suggest t with n-1 df; differences are small for n > 50).
    """
    ea, eb = _pair(errors_a, errors_b)
    d = np.abs(ea) ** power - np.abs(eb) ** power
    n = len(d)
    if n < 3:
        raise ValueError("DM test needs at least 3 observations")
    mean = d.mean()
    centered = d - mean
    variance = np.dot(centered, centered) / n
    for k in range(1, horizon):
        variance += 2 * np.dot(centered[k:], centered[:-k]) / n
    if variance <= 0:
        return {"statistic": float("nan"), "p_value": float("nan"), "mean_loss_difference": float(mean),
                "n": n, "horizon": horizon, "note": "non-positive long-run variance"}
    statistic = mean / math.sqrt(variance / n)
    statistic *= math.sqrt((n + 1 - 2 * horizon + horizon * (horizon - 1) / n) / n)
    return {"statistic": float(statistic), "p_value": _normal_two_sided(statistic),
            "mean_loss_difference": float(mean), "n": n, "horizon": horizon, "loss_power": power}


def skill_score(metric_model: float, metric_baseline: float) -> float:
    """1 - model/baseline for error metrics; > 0 means better than baseline."""
    return float(1 - metric_model / metric_baseline) if metric_baseline else float("nan")


def cohens_dz(differences: ArrayLike) -> float:
    d = np.asarray(differences, dtype=float)
    sd = d.std(ddof=1)
    return float(d.mean() / sd) if sd else float("nan")


def cliffs_delta(x: ArrayLike, y: ArrayLike) -> float:
    """P(X > Y) - P(X < Y); |delta| < 0.147 negligible, < 0.33 small, < 0.474 medium (Romano et al.)."""
    x, ys = np.asarray(x, dtype=float), np.sort(np.asarray(y, dtype=float))
    less = np.searchsorted(ys, x, side="left")
    greater = len(ys) - np.searchsorted(ys, x, side="right")
    return float((less.sum() - greater.sum()) / (len(x) * len(ys)))


def holm(p_values: ArrayLike) -> list[float]:
    p = np.asarray(p_values, dtype=float)
    m = len(p)
    order = np.argsort(p)
    adjusted = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[idx]))
        adjusted[idx] = running
    return adjusted.tolist()


def benjamini_hochberg(p_values: ArrayLike) -> list[float]:
    p = np.asarray(p_values, dtype=float)
    m = len(p)
    order = np.argsort(p)[::-1]
    adjusted = np.empty(m)
    running = 1.0
    for position, idx in enumerate(order):
        rank = m - position
        running = min(running, p[idx] * m / rank)
        adjusted[idx] = running
    return adjusted.tolist()


def rolling_origin_splits(
    n: int, initial: int, horizon: int, step: int | None = None, gap: int = 0, expanding: bool = True,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Time-ordered train/test folds; ``gap`` samples between train end and test start."""
    step = step or horizon
    end = initial
    while end + gap + horizon <= n:
        start = 0 if expanding else end - initial
        yield np.arange(start, end), np.arange(end + gap, end + gap + horizon)
        end += step


def temporal_leakage_issues(train_times: Sequence, test_times: Sequence, min_gap=None) -> list[str]:
    """Flag overlap or test data that precedes the end of training (+ optional gap)."""
    issues: list[str] = []
    train, test = sorted(train_times), sorted(test_times)
    if not train or not test:
        return ["empty train or test set"]
    overlap = set(train) & set(test)
    if overlap:
        issues.append(f"{len(overlap)} timestamps appear in both train and test")
    boundary = train[-1] if min_gap is None else train[-1] + min_gap
    if test[0] <= boundary:
        issues.append(f"test starts at {test[0]}, not after train end {train[-1]} plus gap")
    return issues


def evaluate(y, yhat, baseline=None, n_parameters=0, n_boot=2000, seed=0, block_length=None, horizon=1) -> dict:
    y, yhat = _pair(y, yhat)
    boot = {"n_boot": n_boot, "seed": seed, "block_length": block_length}
    metrics = {
        "MAE": bootstrap_ci(mae, y, yhat, **boot),
        "RMSE": bootstrap_ci(rmse, y, yhat, **boot),
        "CV_RMSE": bootstrap_ci(lambda a, b: cv_rmse(a, b, n_parameters), y, yhat, **boot),
        "NMBE": bootstrap_ci(lambda a, b: nmbe(a, b, n_parameters), y, yhat, **boot),
        "R2": bootstrap_ci(r2, y, yhat, **boot),
    }
    result: dict = {"n": len(y), "n_parameters": n_parameters, "metrics": metrics}
    if baseline is not None:
        y, base = _pair(y, baseline)
        err_model, err_base = y - yhat, y - base
        result["baseline_metrics"] = {"RMSE": rmse(y, base), "MAE": mae(y, base),
                                      "CV_RMSE": cv_rmse(y, base, n_parameters)}
        result["comparison"] = {
            "rmse_skill_score": bootstrap_ci(lambda a, b, c: skill_score(rmse(a, b), rmse(a, c)),
                                             y, yhat, base, **boot),
            "squared_error_difference": paired_bootstrap_difference(err_model ** 2, err_base ** 2, **boot),
            "diebold_mariano_squared": diebold_mariano(err_model, err_base, horizon=horizon, power=2),
            "diebold_mariano_absolute": diebold_mariano(err_model, err_base, horizon=horizon, power=1),
            "cohens_dz_squared_error": cohens_dz(err_model ** 2 - err_base ** 2),
        }
    return result


def cmd_evaluate(args: argparse.Namespace) -> int:
    with Path(args.file).open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    columns = [args.observed, args.predicted] + ([args.baseline] if args.baseline else [])
    kept, dropped = [], 0
    for row in rows:
        try:
            values = [float(row[c]) for c in columns]
        except (KeyError, ValueError, TypeError):
            dropped += 1
            continue
        if any(math.isnan(v) for v in values):
            dropped += 1
            continue
        kept.append(values)
    if not kept:
        raise SystemExit("[stats] no complete rows")
    data = np.asarray(kept)
    result = evaluate(data[:, 0], data[:, 1], data[:, 2] if args.baseline else None,
                      n_parameters=args.parameters, n_boot=args.n_boot, seed=args.seed,
                      block_length=args.block_length, horizon=args.horizon)
    result.update({"file": args.file, "columns": columns, "rows_dropped_incomplete": dropped})
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[stats] wrote {output} (n={len(kept)}, dropped={dropped})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--file", required=True)
    ev.add_argument("--observed", required=True)
    ev.add_argument("--predicted", required=True)
    ev.add_argument("--baseline")
    ev.add_argument("--parameters", type=int, default=0, help="model parameters p for CV(RMSE)/NMBE")
    ev.add_argument("--n-boot", type=int, default=2000)
    ev.add_argument("--seed", type=int, default=0)
    ev.add_argument("--block-length", type=int, help="moving-block length for autocorrelated series")
    ev.add_argument("--horizon", type=int, default=1, help="forecast horizon for the DM test")
    ev.add_argument("--output", required=True)
    ev.set_defaults(func=cmd_evaluate)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
