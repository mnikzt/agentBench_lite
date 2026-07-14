"use client";

import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export default function BenchmarkError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <Alert>
      <AlertTitle>Benchmark could not be loaded</AlertTitle>
      <AlertDescription>{error.message || "Check that the backend is running and the benchmark id exists."}</AlertDescription>
      <Button className="mt-4" type="button" onClick={reset}>Try again</Button>
    </Alert>
  );
}
