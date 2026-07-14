from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.benchmark.summarizer import summarize_benchmark
from app.core.database import Base
from app.models.benchmark import BenchmarkRun, BenchmarkRunItem
from app.models.run import Run
from app.models.task import Task
from app.models.task_set import TaskSet


def test_summarize_benchmark_aggregates_completed_runs(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'summary.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with session_factory() as db:
        task_set = TaskSet(task_set_key="generic_basic", name="Generic Basic")
        task = Task(task_key="api_summary_001", name="API Summary", spec={})
        db.add_all([task_set, task])
        db.flush()
        benchmark = BenchmarkRun(
            task_set_id=task_set.id,
            status="running",
            config={"models": ["mock"], "prompts": ["baseline"], "runtimes": ["react"], "repeat": 2},
            planned_runs=2,
        )
        db.add(benchmark)
        db.flush()
        success_run = Run(
            task_id=task.id,
            benchmark_run_id=benchmark.id,
            status="success",
            model="mock",
            prompt_key="baseline",
            runtime_key="react",
            score=Decimal("1.0"),
            total_latency_ms=100,
            total_cost_usd=Decimal("0.01"),
        )
        failed_run = Run(
            task_id=task.id,
            benchmark_run_id=benchmark.id,
            status="failed",
            model="mock",
            prompt_key="baseline",
            runtime_key="react",
            score=Decimal("0.0"),
            total_latency_ms=300,
            total_cost_usd=Decimal("0.03"),
            failure_type="TOOL_ERROR",
        )
        db.add_all([success_run, failed_run])
        db.flush()
        db.add_all(
            [
                BenchmarkRunItem(
                    benchmark_run_id=benchmark.id,
                    run_id=success_run.id,
                    task_id=task.id,
                    model="mock",
                    prompt_key="baseline",
                    runtime_key="react",
                    repeat_index=0,
                ),
                BenchmarkRunItem(
                    benchmark_run_id=benchmark.id,
                    run_id=failed_run.id,
                    task_id=task.id,
                    model="mock",
                    prompt_key="baseline",
                    runtime_key="react",
                    repeat_index=1,
                ),
            ]
        )
        db.commit()

        summarized = summarize_benchmark(db, benchmark.id)

        assert summarized.status == "failed"
        assert summarized.completed_runs == 2
        assert summarized.failed_runs == 1
        assert summarized.summary["total_runs"] == 2
        assert summarized.summary["success_rate"] == 0.5
        assert summarized.summary["avg_score"] == 0.5
        assert summarized.summary["avg_latency_ms"] == 200
        assert summarized.summary["avg_cost_usd"] == 0.02
        assert summarized.summary["failure_distribution"] == {"TOOL_ERROR": 1}
