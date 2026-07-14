from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.benchmark import BenchmarkRun, BenchmarkRunItem
from app.models.run import Run


def summarize_benchmark(db: Session, benchmark_run_id: str) -> BenchmarkRun:
    benchmark = db.get(BenchmarkRun, benchmark_run_id)
    if not benchmark:
        raise ValueError(f"Benchmark run not found: {benchmark_run_id}")

    runs = list(
        db.scalars(
            select(Run)
            .join(BenchmarkRunItem, BenchmarkRunItem.run_id == Run.id)
            .where(BenchmarkRunItem.benchmark_run_id == benchmark_run_id)
        ).all()
    )
    total = len(runs)
    completed = [run for run in runs if run.status in {"success", "failed", "timeout", "cancelled"}]
    successful = [run for run in runs if run.status == "success"]
    scored = [run for run in runs if run.score is not None]
    failures = Counter(
        run.failure_type or run.status for run in runs if run.status in {"failed", "timeout", "cancelled"}
    )

    by_dimension: dict[str, dict[str, dict[str, float | int]]] = defaultdict(dict)
    items = list(
        db.scalars(
            select(BenchmarkRunItem).where(BenchmarkRunItem.benchmark_run_id == benchmark_run_id)
        ).all()
    )
    run_by_id = {run.id: run for run in runs}
    for dimension_name in ("model", "prompt_key", "runtime_key"):
        values = sorted({getattr(item, dimension_name) for item in items})
        for value in values:
            value_runs = [run_by_id[item.run_id] for item in items if getattr(item, dimension_name) == value]
            by_dimension[dimension_name][value] = _summarize_runs(value_runs)

    terminal_failures = [run for run in runs if run.status in {"failed", "timeout", "cancelled"}]
    benchmark.completed_runs = len(completed)
    benchmark.failed_runs = len(terminal_failures)
    benchmark.summary = {
        "total_runs": total,
        "completed_runs": len(completed),
        "success_rate": len(successful) / total if total else 0,
        "avg_score": _avg([float(run.score) for run in scored]),
        "avg_latency_ms": _avg([run.total_latency_ms for run in completed]),
        "avg_cost_usd": float(sum((run.total_cost_usd for run in completed), Decimal("0")) / len(completed))
        if completed
        else 0,
        "failure_distribution": dict(failures),
        "by_dimension": by_dimension,
    }
    if total and len(completed) == total:
        benchmark.status = "success" if len(successful) == total else "failed"
        benchmark.finished_at = datetime.now(UTC)
    else:
        benchmark.status = "running"
    db.add(benchmark)
    return benchmark


def _avg(values: list[float | int]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def _summarize_runs(runs: list[Run]) -> dict[str, float | int]:
    successful = [run for run in runs if run.status == "success"]
    scored = [run for run in runs if run.score is not None]
    completed = [run for run in runs if run.status in {"success", "failed", "timeout", "cancelled"}]
    return {
        "total_runs": len(runs),
        "success_rate": len(successful) / len(runs) if runs else 0,
        "avg_score": _avg([float(run.score) for run in scored]),
        "avg_latency_ms": _avg([run.total_latency_ms for run in completed]),
    }
