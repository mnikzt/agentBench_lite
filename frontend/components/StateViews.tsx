import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <Card>
      <CardContent className="py-10 text-center">
        <h3 className="font-medium">{title}</h3>
        {description ? <p className="mt-2 text-sm text-muted-foreground">{description}</p> : null}
      </CardContent>
    </Card>
  );
}

export function ErrorState({ title = "Unable to load data", description }: { title?: string; description?: string }) {
  return (
    <Alert className="border-destructive/30">
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{description ?? "Check that the backend API is running."}</AlertDescription>
    </Alert>
  );
}

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
      {label}
    </div>
  );
}
