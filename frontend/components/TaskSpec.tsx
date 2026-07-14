"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

export function TaskSpec({ spec }: { spec: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="space-y-3">
      <Button type="button" variant="outline" size="sm" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
        {open ? "Hide spec" : "View spec"}
      </Button>
      {open ? <pre>{JSON.stringify(spec, null, 2)}</pre> : null}
    </div>
  );
}
