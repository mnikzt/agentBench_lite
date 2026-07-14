import Link from "next/link";

import { TaskSpec } from "@/components/TaskSpec";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/StateViews";
import { apiGet, type Task, type TaskSet } from "@/lib/api";

export default async function TasksPage() {
  const [tasksResult, taskSetsResult] = await Promise.allSettled([
    apiGet<Task[]>("/api/tasks"),
    apiGet<TaskSet[]>("/api/task-sets"),
  ]);
  const hasError = tasksResult.status === "rejected" || taskSetsResult.status === "rejected";
  const tasks = tasksResult.status === "fulfilled" ? tasksResult.value : [];
  const taskSets = taskSetsResult.status === "fulfilled" ? taskSetsResult.value : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Tasks</h1>
        <p className="mt-2 text-muted-foreground">Task templates and benchmark task sets.</p>
      </div>
      {hasError ? <ErrorState description="Task data could not be loaded." /> : null}
      <section className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Task Templates</CardTitle>
            <CardDescription>Inspect task specs, tools, and evaluator configuration.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {tasks.length === 0 ? (
              <EmptyState title="No tasks" description="Seed examples or create task templates through the API." />
            ) : (
              tasks.map((task) => (
                <article key={task.id} className="rounded-lg border border-border p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="font-semibold">{task.name}</h3>
                      <p className="mt-1 text-sm text-muted-foreground">{task.description}</p>
                    </div>
                    <Badge variant="secondary">{task.task_key}</Badge>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span>Tools: {Array.isArray(task.spec.tools) ? task.spec.tools.join(", ") : "-"}</span>
                    <span>Evaluators: {Array.isArray(task.spec.evaluation) ? task.spec.evaluation.length : 0}</span>
                  </div>
                  <div className="mt-4">
                    <TaskSpec spec={task.spec} />
                  </div>
                </article>
              ))
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Task Sets</CardTitle>
            <CardDescription>Launch benchmarks from a task set.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {taskSets.length === 0 ? (
              <EmptyState title="No task sets" />
            ) : (
              taskSets.map((taskSet) => (
                <div key={taskSet.id} className="rounded-lg border border-border p-4">
                  <h3 className="font-medium">{taskSet.name}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{taskSet.description}</p>
                  <p className="mt-2 text-sm">{taskSet.tasks.length} tasks</p>
                  <Button className="mt-3" variant="outline" size="sm" asChild>
                    <Link href={`/tasks/task-sets/${taskSet.task_set_key}`}>Open task set</Link>
                  </Button>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
