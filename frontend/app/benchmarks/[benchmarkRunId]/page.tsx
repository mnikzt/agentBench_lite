import Link from "next/link";

import { MetricCard } from "@/components/MetricCard";
import { EmptyState, ErrorState } from "@/components/StateViews";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet, formatNumber, formatPercent, type BenchmarkItem, type BenchmarkRun, type Run } from "@/lib/api";

type DimensionSummary = Record<string, Record<string, { success_rate?: number; avg_score?: number; avg_latency_ms?: number; total_runs?: number }>>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export default async function BenchmarkDetailPage({
  params,
}: {
  params: Promise<{ benchmarkRunId: string }>;
}) {
  const { benchmarkRunId } = await params;
  const [benchmarkResult, itemsResult, runsResult] = await Promise.allSettled([
    apiGet<BenchmarkRun>(`/api/benchmarks/${benchmarkRunId}`),
    apiGet<BenchmarkItem[]>(`/api/benchmarks/${benchmarkRunId}/items`),
    apiGet<Run[]>(`/api/runs?benchmark_run_id=${benchmarkRunId}`),
  ]);
  if (benchmarkResult.status === "rejected") {
    return (
      <ErrorState
        title="Benchmark could not be loaded"
        description={benchmarkResult.reason instanceof Error ? benchmarkResult.reason.message : undefined}
      />
    );
  }
  const benchmark = benchmarkResult.value;
  const items = itemsResult.status === "fulfilled" ? itemsResult.value : [];
  const runs = runsResult.status === "fulfilled" ? runsResult.value : [];
  const runById = new Map(runs.map((run) => [run.id, run]));
  const summary = benchmark.summary ?? {};
  const byDimension = isRecord(summary.by_dimension) ? (summary.by_dimension as DimensionSummary) : {};
  const failureDistribution = isRecord(summary.failure_distribution)
    ? (Object.fromEntries(
        Object.entries(summary.failure_distribution).filter(([, value]) => typeof value === "number"),
      ) as Record<string, number>)
    : {};

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Benchmark Compare</h1>
        <p className="mt-2 text-muted-foreground">Matrix results across model, prompt, and runtime metadata.</p>
      </div>
      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <MetricCard title="Status" value={benchmark.status} />
        <MetricCard title="Planned Runs" value={benchmark.planned_runs} />
        <MetricCard title="Completed Runs" value={benchmark.completed_runs} />
        <MetricCard title="Success Rate" value={formatPercent(summary.success_rate)} />
        <MetricCard title="Avg Latency" value={`${formatNumber(summary.avg_latency_ms, 0)} ms`} />
      </section>
      <section className="grid gap-6 lg:grid-cols-3">
        {(["model", "prompt_key", "runtime_key"] as const).map((dimension) => (
          <DimensionCard key={dimension} title={dimension} values={byDimension[dimension] ?? {}} />
        ))}
      </section>
      <Card>
        <CardHeader>
          <CardTitle>Failure Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          {Object.keys(failureDistribution).length === 0 ? (
            <EmptyState title="No failures recorded" />
          ) : (
            <div className="flex flex-wrap gap-2">
              {Object.entries(failureDistribution).map(([failure, count]) => (
                <Badge key={failure} variant="destructive">{failure}: {count}</Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Matrix Items</CardTitle>
        </CardHeader>
        <CardContent>
          {itemsResult.status === "rejected" || runsResult.status === "rejected" ? (
            <div className="mb-4">
              <ErrorState title="Some matrix data could not be loaded" />
            </div>
          ) : null}
          {items.length === 0 ? (
            <EmptyState title="No matrix items" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead>Prompt</TableHead>
                  <TableHead>Runtime</TableHead>
                  <TableHead>Repeat</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Trace</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => {
                  const run = runById.get(item.run_id);
                  return (
                    <TableRow key={item.id}>
                      <TableCell>{item.model}</TableCell>
                      <TableCell>{item.prompt_key}</TableCell>
                      <TableCell>{item.runtime_key}</TableCell>
                      <TableCell>{item.repeat_index + 1}</TableCell>
                      <TableCell><Badge variant="secondary">{run?.status ?? "-"}</Badge></TableCell>
                      <TableCell>{run?.score ?? "-"}</TableCell>
                      <TableCell>
                        <Button variant="outline" size="sm" asChild>
                          <Link href={`/runs/${item.run_id}`}>Trace</Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Raw Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <pre>{JSON.stringify(benchmark.summary, null, 2)}</pre>
        </CardContent>
      </Card>
    </div>
  );
}

function DimensionCard({ title, values }: { title: string; values: DimensionSummary[string] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="capitalize">{title.replaceAll("_", " ")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {Object.keys(values ?? {}).length === 0 ? (
          <p className="text-sm text-muted-foreground">No data yet.</p>
        ) : (
          Object.entries(values ?? {}).map(([value, metrics]) => (
            <div key={value} className="rounded-lg border border-border p-3">
              <div className="font-medium">{value}</div>
              <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-muted-foreground">
                <span>Runs {metrics.total_runs ?? 0}</span>
                <span>SR {formatPercent(metrics.success_rate)}</span>
                <span>Score {formatNumber(metrics.avg_score)}</span>
                <span className="col-span-3">Latency {formatNumber(metrics.avg_latency_ms, 0)} ms</span>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
