let token = "";
export function setToken(value: string) {
  token = value;
}
export async function request<T>(
  path: string,
  body?: unknown,
  mutation = false,
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(mutation ? { "Idempotency-Key": crypto.randomUUID() } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      message = `${data.error?.message || message}${data.error?.trace_id ? ` · trace ${data.error.trace_id.slice(0, 8)}` : ""}`;
    } catch {
      /* proxy/network response may not be JSON */
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
export function saveFile(name: string, content: string, type = "text/plain") {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export async function exportCSV() {
  const response = await fetch("/api/v1/exports/readiness.csv", {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) throw new Error("Export failed");
  saveFile("market-readiness.csv", await response.text(), "text/csv");
}
export const dateLabel = (value: string | null) =>
  value
    ? new Date(`${value}T12:00:00`).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      })
    : "Unresolved";
export const materialNames: Record<string, string> = {
  duct: "HDPE conduit",
  vault: "Handhole vault",
  fiber: "144-count fiber",
  splice: "Splice enclosure",
  olt: "Optical line terminal",
  ont: "Network terminal",
};
export const materialUnits: Record<string, string> = {
  duct: "m",
  fiber: "m",
  vault: "ea",
  splice: "ea",
  olt: "ea",
  ont: "ea",
};
export const percent = (value: number) => `${Number(value.toFixed(1))}%`;
