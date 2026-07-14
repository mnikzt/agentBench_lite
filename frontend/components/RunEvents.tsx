"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE_URL } from "@/lib/api";

type EventItem = {
  id: number;
  type: string;
  payload: Record<string, unknown>;
};

export function RunEvents({ runId }: { runId: string }) {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const source = new EventSource(`${API_BASE_URL}/api/runs/${runId}/events`);
    const appendEvent = (data: string) => {
      try {
        const event = JSON.parse(data) as EventItem;
        setEvents((current) => [...current, event].slice(-20));
        setError(null);
      } catch {
        setError("Received an invalid SSE payload.");
      }
    };
    source.onmessage = (message) => {
      appendEvent(message.data);
    };
    source.onerror = () => {
      if (source.readyState === EventSource.CLOSED) {
        setError("Event stream disconnected.");
        source.close();
      }
    };
    const eventTypes = [
      "run_started",
      "step_started",
      "tool_called",
      "tool_result",
      "run_failed",
      "run_finished",
      "evaluation_finished",
    ];
    for (const eventType of eventTypes) {
      source.addEventListener(eventType, (message) => {
        appendEvent((message as MessageEvent).data);
      });
    }
    return () => source.close();
  }, [runId]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Live SSE Events</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {error ? <p role="alert" className="text-sm text-muted-foreground">{error}</p> : null}
        {events.length === 0 ? <p className="text-sm text-muted-foreground">Waiting for events...</p> : null}
        {events.map((event) => (
          <div key={`${event.id}-${event.type}`} className="rounded-lg border border-border p-3">
            <Badge variant="secondary">{event.type}</Badge>
            <pre className="mt-3">{JSON.stringify(event.payload, null, 2)}</pre>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
