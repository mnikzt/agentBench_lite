import { RunEvents } from "@/components/RunEvents";
import { MetricCard } from "@/components/MetricCard";
import { EmptyState, ErrorState } from "@/components/StateViews";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiGet, type Run, type Step } from "@/lib/api";

export default async function RunDetailPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const [runResult, stepsResult] = await Promise.allSettled([
    apiGet<Run>(`/api/runs/${runId}`),
    apiGet<Step[]>(`/api/runs/${runId}/steps`),
  ]);
  if (runResult.status === "rejected") {
    return <ErrorState title="Run could not be loaded" description={runResult.reason instanceof Error ? runResult.reason.message : undefined} />;
  }
  const run = runResult.value;
  const steps = stepsResult.status === "fulfilled" ? stepsResult.value : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Run Detail</h1>
        <p className="mt-2 text-muted-foreground">Trace, final output, score, and live SSE updates.</p>
      </div>
      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <MetricCard title="Status" value={run.status} detail={run.failure_type ?? undefined} />
        <MetricCard title="Model" value={run.model} />
        <MetricCard title="Runtime" value={run.runtime_key} detail={run.prompt_key ?? undefined} />
        <MetricCard title="Score" value={run.score ?? "-"} detail={run.passed === null ? undefined : run.passed ? "passed" : "failed"} />
        <MetricCard title="Latency" value={`${run.total_latency_ms} ms`} detail={`${run.total_steps} steps`} />
      </section>
      <Card>
        <CardHeader>
          <CardTitle>Final Output</CardTitle>
        </CardHeader>
        <CardContent>
          {run.final_output ? <pre>{JSON.stringify(run.final_output, null, 2)}</pre> : <EmptyState title="No final output yet" />}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Step Trace Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          {stepsResult.status === "rejected" ? <div className="mb-4"><ErrorState title="Steps could not be loaded" /></div> : null}
          {steps.length === 0 ? (
            <EmptyState title="No steps recorded yet" description="The worker may not have picked up this run." />
          ) : (
            <div className="space-y-4">
              {steps.map((step) => (
                <article key={step.id} className="relative rounded-lg border border-border p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge>Step {step.step_index}</Badge>
                    {step.phase ? <Badge variant="secondary">{step.phase}</Badge> : null}
                    {step.tool_name ? <Badge variant="outline">{step.tool_name}</Badge> : null}
                    <span className="text-sm text-muted-foreground">{step.latency_ms ?? 0} ms</span>
                  </div>
                  {step.thought ? <p className="mt-3 text-sm font-medium">{step.thought}</p> : null}
                  {step.observation ? <p className="mt-2 text-sm text-muted-foreground">{step.observation}</p> : null}
                  {step.error ? <p className="mt-2 text-sm text-destructive">Error: {step.error}</p> : null}
                  <pre className="mt-3">{JSON.stringify({ input: step.tool_input, output: step.tool_output }, null, 2)}</pre>
                </article>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      <section>
        <RunEvents runId={runId} />
      </section>
    </div>
  );
}
