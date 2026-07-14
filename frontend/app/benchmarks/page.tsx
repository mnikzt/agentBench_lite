import Link from "next/link";

import { EmptyState, ErrorState } from "@/components/StateViews";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet, formatPercent, type BenchmarkRun } from "@/lib/api";

export default async function BenchmarksPage() {
  const result = await apiGet<BenchmarkRun[]>("/api/benchmarks")
    .then((benchmarks) => ({ benchmarks, error: null }))
    .catch((error: Error) => ({ benchmarks: [], error }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Benchmarks</h1>
        <p className="mt-2 text-muted-foreground">Compare model, prompt, and runtime matrix runs.</p>
      </div>
      {result.error ? <ErrorState description={result.error.message} /> : null}
      <Card>
        <CardHeader>
          <CardTitle>Benchmark Runs</CardTitle>
        </CardHeader>
        <CardContent>
          {result.benchmarks.length === 0 ? (
            <EmptyState title="No benchmarks yet" description="Open a task set and start a benchmark run." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Planned Runs</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead>Success Rate</TableHead>
                  <TableHead>Compare</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {result.benchmarks.map((benchmark) => (
                  <TableRow key={benchmark.id}>
                    <TableCell><Badge variant="secondary">{benchmark.status}</Badge></TableCell>
                    <TableCell>{benchmark.planned_runs}</TableCell>
                    <TableCell>{benchmark.completed_runs}</TableCell>
                    <TableCell>{formatPercent(benchmark.summary?.success_rate)}</TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/benchmarks/${benchmark.id}`}>Open matrix</Link>
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
