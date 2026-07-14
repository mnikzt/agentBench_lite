# AgentBench Lite 开发文档

## 1. 项目定位

**AgentBench Lite** 是一个面向 Agent 应用开发的轻量级执行与 Benchmark Harness，用于让 Agent 任务从“能跑一次”变成“可复现、可观测、可评测、可对比”的工程系统。

AgentBench Lite 参考 DeepEval、LangSmith、OpenAI Evals 等成熟工具中的 test case、metric、trace、dataset 抽象，但项目重点不是追求指标数量，而是从后端工程视角实现 Agent 执行与评测闭环：Run / Attempt / Step 生命周期、异步 Worker、SSE Trace、失败归因与 Benchmark Matrix。评测层可以内置轻量 evaluator，也可以通过 Adapter 接入 DeepEval。

项目核心目标：

- 支持用配置文件定义 Agent 任务
- 支持 Agent 调用 Browser / HTTP / File / Python 等工具
- 记录每一步执行轨迹，包括输入、输出、耗时、成本、错误
- 支持对 Agent 输出进行自动评分，并预留 DeepEval Adapter
- 支持批量运行任务，比较不同模型、Prompt、工具策略的效果
- 提供实时日志流和可视化 Trace 面板

一句话：

> AgentBench Lite = Agent Runtime + Queue Worker + Step Trace + Benchmark Matrix + Evaluator Adapter + 可视化面板。

与 DeepEval 的关系：

| 维度 | DeepEval | AgentBench Lite |
| --- | --- | --- |
| 核心定位 | LLM / Agent 评测框架 | Agent 执行与 Benchmark Harness |
| 更像什么 | Pytest for LLM apps | Agent CI / Run 管理平台 |
| 重点 | Metrics、Dataset、LLM-as-Judge、Trace 集成 | Run、Attempt、Step、Worker、SSE、Benchmark Matrix |
| Agent 执行 | 通常接入已有 app / agent | 自己调度和执行 Agent |
| 项目价值 | 评测指标生态 | 后端工程化与实验编排 |

## 2. 技术栈

推荐使用：

- **后端**：FastAPI
- **Agent Runtime**：自研 ReAct Runtime（MVP）
- **数据库**：PostgreSQL
- **队列**：Redis + RQ / Celery
- **浏览器工具**：Playwright
- **前端**：Next.js + shadcn/ui
- **实时推送**：SSE
- **ORM**：SQLAlchemy / Prisma Python 可选
- **配置格式**：YAML / JSON
- **评测适配**：内置 JSON Schema / Exact Match，DeepEval Adapter 可选

可选扩展：

- **复杂编排**：LangGraph Runtime（第二阶段）
- **代码任务执行**：Claude Code SDK Runtime（第二阶段）
- **评测框架**：DeepEval Adapter（第二阶段）

如果更想贴后端岗，也可以用 NestJS + BullMQ。MVP 不强依赖 LangGraph，优先手写 ReAct 执行循环，把 Run / Step / Tool / Evaluation 的底层机制做清楚。

## 3. 核心业务流程

```text
用户创建任务
  ↓
后端写入 Run
  ↓
投递 Redis 队列
  ↓
Worker 加载 Task Spec / Task Set
  ↓
ReActRuntime 执行 Agent 循环
  ↓
每一步工具调用写入 Step
  ↓
SSE 推送日志
  ↓
EvaluatorPipeline 评分（内置 evaluator 或 DeepEval Adapter）
  ↓
写入 Evaluation / Metrics
  ↓
前端展示 Trace、成功率、成本、耗时
```

## 4. MVP 功能范围

第一版只做这些，控制在 2～3 周内完成。

### 4.1 任务定义

支持用 YAML 定义任务：

```yaml
id: extract_price_demo
name: Extract Product Price
description: Visit a product page and extract product price.

input:
  url: "https://example.com/product/123"

agent:
  mode: react
  model: gpt-4o-mini
  max_steps: 8
  temperature: 0

tools:
  - browser
  - http
  - file

expected_output:
  type: json
  schema:
    type: object
    required: ["price", "currency"]
    properties:
      price:
        type: number
      currency:
        type: string

evaluation:
  - type: json_schema
  - type: llm_judge
    rubric: "The answer should contain the correct price and currency."
```

### 4.2 任务集合与 Benchmark

单个 Task 只能验证 Agent 是否能跑通。AgentBench Lite 的核心价值来自 Task Set 和 Benchmark Matrix：

```text
Task Set
  ↓
tasks × models × prompts × runtimes × repeat
  ↓
Benchmark Run
  ↓
聚合 success rate / avg score / avg latency / avg cost / failure distribution
```

Task Set 示例：

```yaml
id: web_extraction_basic
name: Basic Web Extraction Benchmark
description: Basic browser extraction tasks for Agent runtime regression.
tasks:
  - web_extract_price_001
  - web_extract_contact_001
  - web_extract_event_info_001
```

Benchmark 配置示例：

```yaml
task_set: web_extraction_basic
models:
  - gpt-4o-mini
  - claude-3-5-haiku
prompts:
  - baseline
  - tool_first
runtimes:
  - react
repeat: 3
```

### 4.3 Agent 执行模式

MVP 先支持一种模式：

1. **ReAct**
   - Thought → Action → Observation 循环
   - 适合网页检索、API 调用、信息抽取

第二阶段再扩展：

- **Plan-and-Execute**：先生成计划，再逐步执行，适合多步骤任务
- **LangGraphRuntime**：当执行流程需要复杂条件路由、反思、审批、恢复时再引入
- **ClaudeCodeRuntime**：当任务类型是代码库分析、补丁生成、测试修复时再接入 Claude Code SDK

MVP 的重点不是框架编排，而是自研 Runtime 的执行闭环：

```text
while step < max_steps:
  1. LLM 根据上下文决定下一步 action
  2. ToolRegistry 调用对应工具
  3. StepStore 记录 thought / action / observation
  4. EventBus 推送 SSE 事件
  5. 判断是否 final / failed / timeout
```

### 4.4 工具系统

先做 4 个工具：

| 工具 | 作用 |
| --- | --- |
| `browser` | 用 Playwright 打开网页、点击、读取页面文本 |
| `http` | 调用 GET / POST API |
| `file` | 读取 / 写入临时文件 |
| `python` | 执行受限 Python 代码，用于数据处理 |

工具调用统一抽象：

```python
class ToolCall(BaseModel):
    tool_name: str
    input: dict
    output: dict | None = None
    error: str | None = None
    latency_ms: int
```

## 5. 数据库设计

### 5.1 `tasks`

保存任务模板。

```sql
CREATE TABLE tasks (
  id UUID PRIMARY KEY,
  task_key VARCHAR(128) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  spec JSONB NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 5.2 `runs`

一次任务执行记录。

```sql
CREATE TABLE runs (
  id UUID PRIMARY KEY,
  task_id UUID REFERENCES tasks(id),
  status VARCHAR(32) NOT NULL,
  agent_mode VARCHAR(64),
  model VARCHAR(128),
  input JSONB,
  final_output JSONB,
  error TEXT,
  score NUMERIC,
  total_steps INT DEFAULT 0,
  total_latency_ms INT DEFAULT 0,
  total_tokens INT DEFAULT 0,
  total_cost_usd NUMERIC DEFAULT 0,
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

状态建议：

```text
pending
running
evaluating
success
failed
cancelled
timeout
```

### 5.3 `steps`

记录 Agent 每一步执行轨迹。

```sql
CREATE TABLE steps (
  id UUID PRIMARY KEY,
  run_id UUID REFERENCES runs(id),
  step_index INT NOT NULL,
  phase VARCHAR(64),
  thought TEXT,
  action VARCHAR(128),
  tool_name VARCHAR(128),
  tool_input JSONB,
  tool_output JSONB,
  observation TEXT,
  error TEXT,
  latency_ms INT,
  tokens INT DEFAULT 0,
  cost_usd NUMERIC DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 5.4 `evaluations`

保存评分结果。

```sql
CREATE TABLE evaluations (
  id UUID PRIMARY KEY,
  run_id UUID REFERENCES runs(id),
  evaluator_type VARCHAR(64) NOT NULL,
  score NUMERIC,
  passed BOOLEAN,
  details JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 5.5 `task_sets`

保存任务集合。Task Set 是 Benchmark 的基本输入，避免每次手动选择一组任务。

```sql
CREATE TABLE task_sets (
  id UUID PRIMARY KEY,
  task_set_key VARCHAR(128) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  tags TEXT[],
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 5.6 `task_set_items`

维护任务集合与任务模板的关联关系。

```sql
CREATE TABLE task_set_items (
  id UUID PRIMARY KEY,
  task_set_id UUID REFERENCES task_sets(id),
  task_id UUID REFERENCES tasks(id),
  sort_order INT DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 5.7 `benchmark_runs`

一次批量评测实验。它不直接保存所有 step，而是保存实验配置和聚合结果；具体执行仍然展开为多个 `runs`。

```sql
CREATE TABLE benchmark_runs (
  id UUID PRIMARY KEY,
  task_set_id UUID REFERENCES task_sets(id),
  status VARCHAR(32) NOT NULL,
  config JSONB NOT NULL,
  summary JSONB,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  started_at TIMESTAMP,
  finished_at TIMESTAMP
);
```

`summary` 示例：

```json
{
  "total_runs": 54,
  "success_rate": 0.78,
  "avg_score": 0.82,
  "avg_latency_ms": 14320,
  "avg_cost_usd": 0.018,
  "failure_distribution": {
    "TOOL_ERROR": 4,
    "OUTPUT_SCHEMA_ERROR": 3,
    "MAX_STEPS_EXCEEDED": 5
  }
}
```

### 5.8 `run_attempts`（第二阶段）

用于支持失败恢复与多次尝试。MVP 可以先不建表，用 `runs` 表承载一次执行；第二阶段再引入。

```sql
CREATE TABLE run_attempts (
  id UUID PRIMARY KEY,
  run_id UUID REFERENCES runs(id),
  attempt_index INT NOT NULL,
  status VARCHAR(32) NOT NULL,
  error TEXT,
  failure_type VARCHAR(64),
  started_at TIMESTAMP,
  finished_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

## 6. API 设计

### 6.1 创建任务模板

```http
POST /api/tasks
```

请求：

```json
{
  "task_key": "extract_price_demo",
  "name": "Extract Product Price",
  "spec": {}
}
```

### 6.2 创建 Run

```http
POST /api/runs
```

请求：

```json
{
  "task_key": "extract_price_demo",
  "input": {
    "url": "https://example.com/product/123"
  },
  "agent_mode": "react",
  "model": "gpt-4o-mini"
}
```

响应：

```json
{
  "run_id": "uuid",
  "status": "pending"
}
```

### 6.3 查询 Run

```http
GET /api/runs/{run_id}
```

返回：

```json
{
  "id": "uuid",
  "status": "success",
  "score": 0.86,
  "total_steps": 6,
  "total_latency_ms": 12800,
  "total_cost_usd": 0.012
}
```

### 6.4 查询 Step Trace

```http
GET /api/runs/{run_id}/steps
```

### 6.5 SSE 实时日志

```http
GET /api/runs/{run_id}/events
```

事件类型：

```text
run_started
step_started
tool_called
tool_result
step_failed
run_finished
evaluation_finished
```

### 6.6 批量运行 Benchmark

```http
POST /api/benchmarks/run
```

请求：

```json
{
  "task_set_key": "web_extraction_basic",
  "models": ["gpt-4o-mini", "claude-3-5-haiku"],
  "prompts": ["baseline", "tool_first"],
  "runtimes": ["react"],
  "repeat": 3
}
```

响应：

```json
{
  "benchmark_run_id": "uuid",
  "status": "pending",
  "planned_runs": 18
}
```

### 6.7 查询 Benchmark 结果

```http
GET /api/benchmarks/{benchmark_run_id}
```

返回：

```json
{
  "id": "uuid",
  "status": "success",
  "summary": {
    "success_rate": 0.78,
    "avg_score": 0.82,
    "avg_latency_ms": 14320,
    "avg_cost_usd": 0.018
  }
}
```

## 7. 后端模块划分

推荐目录：

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── tasks.py
│   │   ├── task_sets.py
│   │   ├── runs.py
│   │   └── benchmarks.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── events.py
│   ├── models/
│   │   ├── task.py
│   │   ├── task_set.py
│   │   ├── run.py
│   │   ├── step.py
│   │   └── evaluation.py
│   ├── agent/
│   │   ├── runtime.py
│   │   ├── react_runtime.py
│   │   ├── prompts.py
│   │   └── state.py
│   ├── tools/
│   │   ├── browser_tool.py
│   │   ├── http_tool.py
│   │   ├── file_tool.py
│   │   └── python_tool.py
│   ├── evaluator/
│   │   ├── pipeline.py
│   │   ├── json_schema_eval.py
│   │   ├── exact_match_eval.py
│   │   ├── llm_judge_eval.py
│   │   └── deepeval_adapter.py
│   ├── benchmark/
│   │   ├── matrix.py
│   │   ├── scheduler.py
│   │   └── summarizer.py
│   └── worker/
│       ├── queue.py
│       └── runner.py
```

## 8. Agent Runtime 设计

MVP 使用自研 `ReActRuntime`，不直接依赖 LangGraph。目标是先把 Agent 执行循环、工具分发、Step Trace、SSE 事件、错误分类和评测闭环做透明。

后续通过统一接口扩展 `LangGraphRuntime` 或 `ClaudeCodeRuntime`。

### 8.1 Runtime 接口

```python
from typing import Protocol

class AgentRuntime(Protocol):
    async def run(self, run_id: str, task_spec: dict, input: dict) -> dict:
        ...
```

MVP 实现：

- `ReActRuntime`：手写 Thought → Action → Observation 循环

后续实现：

- `LangGraphRuntime`：用于复杂条件路由、Human approval、多阶段反思
- `ClaudeCodeRuntime`：用于代码库分析、补丁生成、测试修复等 coding task

### 8.2 Agent State

```python
class AgentState(TypedDict):
    run_id: str
    task_spec: dict
    input: dict
    messages: list
    steps: list
    current_step: int
    final_output: dict | None
    error: str | None
```

### 8.3 ReActRuntime 执行流程

```text
start
  ↓
reason
  ↓
select_tool
  ↓
execute_tool
  ↓
record_step
  ↓
should_continue?
  ├── yes → plan_or_reason
  └── no  → finalize
```

### 8.4 核心组件

| 组件 | 作用 |
| --- | --- |
| `ReActRuntime` | 执行 Agent 循环 |
| `LLMClient` | 根据上下文输出下一步 tool call 或 final answer |
| `ToolRegistry` | 注册并分发 Browser / HTTP / File / Python 工具 |
| `StepStore` | 持久化每一步 thought / action / observation |
| `EventBus` | 推送 SSE 实时事件 |
| `EvaluatorPipeline` | Run 结束后执行评分 |

### 8.5 为什么 MVP 不直接用 LangGraph

AgentBench Lite 第一阶段的核心不是复杂图编排，而是：

- 任务是否能异步执行
- Step trace 是否完整
- 工具调用是否可复盘
- 失败原因是否可分类
- 评分结果是否可比较

这些能力手写 Runtime 更透明，也更容易在面试中讲清底层机制。当后续出现复杂路由、反思、审批、恢复等需求时，再把同一个 `AgentRuntime` 接口扩展为 `LangGraphRuntime`。

## 9. 评测系统

AgentBench Lite 的评测层参考 DeepEval 等成熟工具的抽象，但实现上优先服务本项目的执行平台和 Benchmark Matrix。评测能力分两级：

1. **内置轻量 evaluator**：覆盖结构化输出、简单字段匹配和基础 LLM judge，满足 MVP。
2. **DeepEval Adapter**：第二阶段接入 DeepEval 的 Task Completion、Step Efficiency、Plan Quality、Hallucination 等成熟指标。

### 9.1 EvaluatorPipeline

所有 evaluator 通过统一接口接入：

```python
class Evaluator(Protocol):
    async def evaluate(self, run: Run, steps: list[Step], spec: dict) -> EvaluationResult:
        ...
```

`EvaluatorPipeline` 根据 task spec 选择内置 evaluator 或 DeepEval Adapter：

```yaml
evaluation:
  - type: json_schema
  - type: deepeval
    metrics:
      - task_completion
      - step_efficiency
```

### 9.2 内置 JSON Schema

判断输出是否符合结构。

适合：

- API 结果
- 信息抽取
- 表格字段生成

### 9.3 内置 Exact Match

判断文本或字段是否完全匹配。

适合：

- 简单 QA
- 固定答案任务

### 9.4 内置 LLM-as-Judge

使用模型根据 rubric 打分。

返回结构：

```json
{
  "score": 0.8,
  "passed": true,
  "reason": "The answer contains the correct price but misses source evidence."
}
```

注意：

- LLM judge 要保存 prompt、模型、输出
- 同一个任务最好支持多次重复运行
- 评分结果要能被复查

### 9.5 DeepEval Adapter（第二阶段）

DeepEval 适合承担成熟指标和 LLM eval 生态能力。AgentBench Lite 可以通过 Adapter 复用这些指标，同时保留自己的 Run / Step / Benchmark 数据模型。

DeepEval Adapter 负责：

- 将 AgentBench 的 `Run / Step / final_output` 转成 DeepEval test case / trace
- 调用 DeepEval metrics，例如 Task Completion、Step Efficiency、Plan Adherence
- 把 DeepEval 的结果写回 `evaluations`
- 将指标汇总到 `benchmark_runs.summary`

边界：

- DeepEval 负责提供成熟 metric 和 judge 能力
- AgentBench Lite 负责 Agent 的执行、记录、调度、聚合和实验编排

## 10. 前端页面

MVP 做 5 个页面：

### 10.1 Dashboard

展示：

- 总任务数
- 总 Run 数
- 成功率
- 平均耗时
- 平均成本

### 10.2 Task List

展示任务模板：

- 任务名
- 工具列表
- 评测方式
- 最近成功率

### 10.3 Task Set Detail

展示任务集合：

- Task Set 基本信息
- 包含的任务列表
- 任务类别和难度分布
- 最近一次 Benchmark Summary

### 10.4 Run Detail

重点页面。

展示：

- Run 状态
- 最终输出
- 分数
- 总耗时 / 总成本
- Step Trace 时间线

### 10.5 Benchmark Compare

展示不同模型 / Prompt 的对比：

| Model | Success Rate | Avg Score | Avg Latency | Avg Cost |
| --- | ---: | ---: | ---: | ---: |

同时展示：

- Runtime 对比：`react` / `langgraph` / `claude-code`
- Prompt 对比：`baseline` / `tool_first`
- 失败类型分布
- 单个失败 Run 的 Trace 链接

## 11. 关键工程难点

简历和面试重点讲这些：

1. **异步任务执行**
   - Run 创建后进入队列
   - Worker 后台执行
   - 前端通过 SSE 看实时状态

2. **Step-level Trace**
   - 每一步都落库
   - 方便复盘 Agent 为什么失败

3. **幂等和并发控制**
   - 同一个 Run 只能执行一次
   - Worker 崩溃后可以标记 timeout / failed

4. **评测闭环**
   - 不只看最终输出
   - 记录成功率、成本、耗时、失败原因

5. **Benchmark Matrix**
   - `tasks × models × prompts × runtimes × repeat`
   - 支持批量展开、聚合统计和失败类型分布

6. **DeepEval Adapter**
   - 复用成熟 metric framework 的能力
   - 将 Run / Step Trace 转换给 DeepEval 计算成熟指标

7. **工具安全边界**
   - Python 工具要限制执行时间
   - Browser 工具要限制域名 / 超时
   - File 工具限制工作目录

## 12. 开发里程碑

### Week 1：后端基础

- FastAPI 项目初始化
- PostgreSQL 表设计
- Task / Task Set / Run / Step API
- Redis 队列
- Worker 能消费 Run

### Week 2：Agent 执行

- 自研 ReActRuntime
- ToolRegistry
- HTTP Tool
- Browser Tool
- Step Trace 落库
- SSE 实时推送

### Week 3：评测与前端

- JSON Schema Evaluator
- LLM-as-Judge Evaluator
- Benchmark Matrix
- Task Set Detail 页面
- Run Detail 页面
- Benchmark Compare 页面
- 写 README 和 Demo 数据

### Week 4：可选增强

- DeepEval Adapter
- Run Attempt 与失败恢复
- Token / Cost / Timeout 预算控制
- Benchmark Summary 聚合优化

## 13. 简历包装

后端版：

> 独立开发 Agent Execution & Benchmark Harness，设计 Task Set / Run / Attempt / Step / Evaluation 数据模型，基于 Redis 队列实现异步执行，并通过 SSE 推送 step-level 日志；支持 Benchmark Matrix 批量对比模型、Prompt 与 Runtime，聚合成功率、延迟、成本和失败类型分布。

Agent 版：

> 独立开发 AgentBench Lite，自研 ReAct Agent Runtime，支持 LLM 规划下一步工具调用、Tool Registry 动态分发、thought-action-observation 执行轨迹记录与 SSE 实时推送；构建 Agent Benchmark Harness，对不同模型、Prompt、工具策略和 Runtime 进行可复现评测。

扩展版：

> 抽象 AgentRuntime 与 Evaluator 接口，MVP 实现自研 ReActRuntime 与轻量 evaluator，并预留 LangGraphRuntime / ClaudeCodeRuntime / DeepEval Adapter 插拔扩展，用于支持复杂工作流、代码型 Agent 任务和成熟评测指标。

## 14. 最小 Demo 任务建议

先内置 3 个任务：

1. **网页价格抽取**
   - 输入商品页面 URL
   - 输出 price / currency / evidence

2. **API 信息汇总**
   - 调用两个 mock API
   - 合并成结构化 JSON

3. **网页研究任务**
   - 搜索某公司官网
   - 提取公司简介、产品、联系方式

这 3 个任务能覆盖：

- Browser
- HTTP
- 结构化输出
- LLM judge
- 多步推理
- 失败分析

## 15. 项目亮点总结

AgentBench Lite 最值得强调的不是“用了某个 Agent 框架”或“发明了全新的评测指标”，而是：

> 把 Agent 执行过程工程化：任务可配置、执行可追踪、结果可评测、策略可对比。

MVP 阶段选择手写 ReActRuntime，是为了讲清 Agent runtime 的底层机制：LLM 决策、工具分发、Step Trace、SSE 事件、错误分类和 Evaluator。DeepEval 可以作为第二阶段评测指标后端，LangGraph 可以作为第二阶段复杂编排扩展，二者都不是第一阶段的必要依赖。

这正好补实习项目的短板：实习项目证明你做过生产 Agent Workflow，AgentBench Lite 证明你理解 Agent 的执行、评测和平台化能力。

## 16. 第二阶段增强能力

1. Run Attempt 与失败恢复
2. 结构化失败原因分类
3. Token / Cost / Timeout 预算控制
4. Benchmark Matrix：tasks × models × prompts × repeat
5. Runtime 插拔：ReActRuntime / LangGraphRuntime / ClaudeCodeRuntime
6. DeepEval Adapter：接入 Task Completion / Step Efficiency / Plan Quality 等成熟指标
