import { BenchmarkRunForm } from "@/components/BenchmarkRunForm";
import { TaskSpec } from "@/components/TaskSpec";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/StateViews";
import { apiGet, type TaskSet } from "@/lib/api";

export default async function TaskSetDetailPage({
  params,
}: {
  params: Promise<{ taskSetKey: string }>;
}) {
  const { taskSetKey } = await params;
  const taskSet = await apiGet<TaskSet>(`/api/task-sets/${taskSetKey}`);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">{taskSet.name}</h1>
        <p className="mt-2 text-muted-foreground">{taskSet.description}</p>
        <Badge className="mt-3" variant="secondary">{taskSet.task_set_key}</Badge>
      </div>
      <BenchmarkRunForm taskSetKey={taskSet.task_set_key} />
      <Card>
        <CardHeader>
          <CardTitle>Included Tasks</CardTitle>
          <CardDescription>Tasks are executed across the benchmark matrix.</CardDescription>
        </CardHeader>
        <CardContent>
          {taskSet.tasks.length === 0 ? (
            <EmptyState title="No tasks in this set" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Key</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Tools</TableHead>
                  <TableHead>Evaluation</TableHead>
                  <TableHead>Spec</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {taskSet.tasks.map((task) => (
                  <TableRow key={task.id}>
                    <TableCell><Badge variant="outline">{task.task_key}</Badge></TableCell>
                    <TableCell>{task.name}</TableCell>
                    <TableCell>{Array.isArray(task.spec.tools) ? task.spec.tools.join(", ") : "-"}</TableCell>
                    <TableCell>{Array.isArray(task.spec.evaluation) ? task.spec.evaluation.length : 0} evaluators</TableCell>
                    <TableCell><TaskSpec spec={task.spec} /></TableCell>
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
