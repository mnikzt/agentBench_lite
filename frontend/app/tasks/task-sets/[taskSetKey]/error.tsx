"use client";

import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export default function TaskSetError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <Alert>
      <AlertTitle>Task set could not be loaded</AlertTitle>
      <AlertDescription>{error.message || "Check that the backend is running and the task set key exists."}</AlertDescription>
      <Button className="mt-4" type="button" onClick={reset}>Try again</Button>
    </Alert>
  );
}
