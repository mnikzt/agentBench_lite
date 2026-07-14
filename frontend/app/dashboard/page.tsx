import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { MetricCard } from "@/components/MetricCard";
import { EmptyState, ErrorState } from "@/components/StateViews";
import { apiGet, formatPercent, type BenchmarkRun, type Run, type Task } from "@/lib/api";

export default async function DashboardPage() {
  const [tasksResult, runsResult, benchmarksResult] = await Promise.allSettled([
    apiGet<Task[]>("/api/tasks"),
    apiGet<Run[]>("/api/runs"),
    apiGet<BenchmarkRun[]>("/api/benchmarks"),
  ]);
  const hasError = [tasksResult, runsResult, benchmarksResult].some((result) => result.status === "rejected");
  const tasks = tasksResult.status === "fulfilled" ? tasksResult.value : [];
  const runs = runsResult.status === "fulfilled" ? runsResult.value : [];
  const benchmarks = benchmarksResult.status === "fulfilled" ? benchmarksResult.value : [];
  const completed = runs.filter((run) => ["success", "failed", "timeout", "cancelled"].includes(run.status));
  const success = runs.filter((run) => run.status === "success");
  const avgLatency =
    completed.length > 0
      ? Math.round(completed.reduce((sum, run) => sum + run.total_latency_ms, 0) / completed.length)
      : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Dashboard</h1>
        <p className="mt-2 text-muted-foreground">Agent execution, trace, evaluation, and benchmark harness.</p>
      </div>
      {hasError ? <ErrorState description="Some dashboard data could not be loaded." /> : null}
      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <MetricCard title="Tasks" value={tasks.length} />
        <MetricCard title="Runs" value={runs.length} />
        <MetricCard title="Benchmarks" value={benchmarks.length} />
        <MetricCard title="Success Rate" value={formatPercent(runs.length ? success.length / runs.length : 0)} />
        <MetricCard title="Avg Latency" value={`${avgLatency} ms`} />
      </section>
      <Card>
        <CardHeader>
          <CardTitle>Recent Runs</CardTitle>
        </CardHeader>
        <CardContent>
          {runs.length === 0 ? (
            <EmptyState title="No runs yet" description="Create a run or start a benchmark to see traces." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Latency</TableHead>
                  <TableHead>Trace</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.slice(0, 8).map((run) => (
                  <TableRow key={run.id}>
                    <TableCell><Badge variant="secondary">{run.status}</Badge></TableCell>
                    <TableCell>{run.model}</TableCell>
                    <TableCell>{run.score ?? "-"}</TableCell>
                    <TableCell>{run.total_latency_ms} ms</TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/runs/${run.id}`}>Open trace</Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
