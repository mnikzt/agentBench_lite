"use client";

import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiPost, type BenchmarkRun } from "@/lib/api";

function splitCsv(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseRepeat(value: string) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? Math.min(20, Math.max(1, parsed)) : 1;
}

export function BenchmarkRunForm({ taskSetKey }: { taskSetKey: string }) {
  const router = useRouter();
  const [models, setModels] = useState("mock");
  const [prompts, setPrompts] = useState("baseline,tool_first");
  const [runtimes, setRuntimes] = useState("react");
  const [repeat, setRepeat] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const benchmark = await apiPost<BenchmarkRun>("/api/benchmarks/run", {
        task_set_key: taskSetKey,
        models: splitCsv(models),
        prompts: splitCsv(prompts),
        runtimes: splitCsv(runtimes),
        repeat,
      });
      router.push(`/benchmarks/${benchmark.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to start benchmark");
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Start Benchmark Run</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
          <Field label="Models" value={models} onChange={setModels} />
          <Field label="Prompts" value={prompts} onChange={setPrompts} />
          <Field label="Runtimes" value={runtimes} onChange={setRuntimes} />
          <div className="space-y-2">
            <Label htmlFor="repeat">Repeat</Label>
            <Input
              id="repeat"
              type="number"
              min={1}
              max={20}
              required
              value={repeat}
              onChange={(event) => setRepeat(parseRepeat(event.target.value))}
            />
          </div>
          <div className="md:col-span-2">
            <Button type="submit" disabled={pending}>
              {pending ? "Starting..." : "Start benchmark"}
            </Button>
            {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const id = label.toLowerCase();
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} value={value} onChange={(event) => onChange(event.target.value)} />
      <p className="text-xs text-muted-foreground">Comma separated</p>
    </div>
  );
}
