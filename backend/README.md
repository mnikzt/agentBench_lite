# AgentBench Lite Backend

This backend implements the MVP execution chain for AgentBench Lite:

- FastAPI application structure
- SQLAlchemy 2.x models
- PostgreSQL configuration through `.env`
- Task, task set, run, step, evaluation, and benchmark run APIs
- Asynchronous RQ worker execution for queued runs
- ReActRuntime step trace and SSE event records
- Benchmark matrix expansion into queued child runs
- Built-in evaluator pipeline for JSON schema, exact match, and lightweight LLM judge

MVP execution uses the self-built `ReActRuntime`. LangGraph and DeepEval are intentionally not dependencies; they remain second-stage adapter candidates.

By default the runtime uses `MockLLMClient`, so local runs do not require an API key. If `OPENAI_API_KEY` is configured, the OpenAI-compatible client is used instead.

## Run Locally

1. Start PostgreSQL and Redis:

```bash
docker compose up -d postgres redis
```

2. Create backend env:

```bash
cp backend/.env.example backend/.env
```

3. Install dependencies:

```bash
cd backend
python -m pip install -e ".[dev]"
```

4. Apply database migrations:

```bash
alembic upgrade head
```

5. Start the API:

```bash
uvicorn app.main:app --reload
```

6. Start a worker in another terminal:

```bash
rq worker agentbench-runs --url redis://localhost:6379/0
```

The MVP browser tool is a mock browser that returns configured page text. Real Playwright browser automation is intentionally deferred.

OpenAPI docs are available at:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## SSE Trace and Evaluation

Subscribe to a run trace:

```bash
curl -N http://localhost:8000/api/runs/{run_id}/events
```

The worker records these MVP events in `run_events` and streams them over SSE:

- `run_started`
- `step_started`
- `tool_called`
- `tool_result`
- `run_finished`
- `run_failed`
- `evaluation_finished`

When the run finishes, `EvaluatorPipeline` reads `task.spec.evaluation` and writes one row per evaluator to `evaluations`.

Supported built-in evaluators:

- `json_schema`
- `exact_match`
- `llm_judge` using a mock judge unless `OPENAI_API_KEY` is configured

Run summary fields are updated on completion:

- `score`
- `passed`
- `total_steps`
- `total_latency_ms`
- `total_tokens`
- `total_cost_usd`

## Seed Example Data

From the repository root:

```bash
python backend/scripts/seed_examples.py
```

This loads:

- `examples/tasks/*.yaml`
- `examples/task_sets/*.yaml`
- `examples/demo_files/*` for file-tool demos

The MVP demo set contains three generic tasks:

- `api_summary_001`: API information summary
- `web_extract_price_001`: price extraction using the mock browser
- `file_read_demo_001`: local file summary

The demo task set is `web_extraction_basic`.

## Benchmark Matrix

Start a benchmark run:

```bash
curl -X POST http://localhost:8000/api/benchmarks/run \
  -H "Content-Type: application/json" \
  -d "{\"task_set_key\":\"web_extraction_basic\",\"models\":[\"mock\"],\"prompts\":[\"baseline\",\"tool_first\"],\"runtimes\":[\"react\"],\"repeat\":2}"
```

The matrix expands as:

```text
tasks x models x prompts x runtimes x repeat
```

Each matrix cell becomes a child `Run` with model, prompt, runtime, and repeat metadata. When all child runs reach a terminal state, the worker updates `benchmark_runs.summary`.

Summary includes:

- `total_runs`
- `success_rate`
- `avg_score`
- `avg_latency_ms`
- `avg_cost_usd`
- `failure_distribution`

## Minimal API Smoke Test

Create a task:

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d "{\"task_key\":\"extract_price_demo\",\"name\":\"Extract Price\",\"spec\":{\"input\":{\"url\":\"https://example.com\"},\"tools\":[\"http\"],\"evaluation\":[{\"type\":\"json_schema\"}]}}"
```

Create a task set:

```bash
curl -X POST http://localhost:8000/api/task-sets \
  -H "Content-Type: application/json" \
  -d "{\"task_set_key\":\"web_basic\",\"name\":\"Web Basic\"}"
```

Add a task to the set:

```bash
curl -X POST http://localhost:8000/api/task-sets/web_basic/items \
  -H "Content-Type: application/json" \
  -d "{\"task_key\":\"extract_price_demo\",\"sort_order\":0}"
```

Create and enqueue a run:

```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d "{\"task_key\":\"file_read_demo_001\",\"model\":\"mock\",\"input\":{\"file_path\":\"demo_files/sample_page.txt\"}}"
```

Create and enqueue a benchmark matrix:

```bash
curl -X POST http://localhost:8000/api/benchmarks/run \
  -H "Content-Type: application/json" \
  -d "{\"task_set_key\":\"web_basic\",\"models\":[\"gpt-4o-mini\"],\"prompts\":[\"baseline\"],\"runtimes\":[\"react\"],\"repeat\":2}"
```

The benchmark endpoint creates a `benchmark_runs` row and child `runs` rows with `queued` status, then enqueues each child run for the worker.
