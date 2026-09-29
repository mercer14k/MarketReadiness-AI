import { afterEach, describe, expect, it, vi } from "vitest";
import { dateLabel, percent, request, setToken } from "./api";
afterEach(() => {
  vi.unstubAllGlobals();
  setToken("");
});
describe("API boundary", () => {
  it("renders a traceable error without trusting response text as markup", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        json: async () => ({
          error: { message: "Invalid dataset", trace_id: "1234567890" },
        }),
      }),
    );
    await expect(request("/portfolio")).rejects.toThrow(
      "Invalid dataset · trace 12345678",
    );
  });
  it("uses bearer auth only when configured and an idempotency key for mutations", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ id: "scenario" }) });
    vi.stubGlobal("fetch", fetch);
    setToken("temporary-token");
    await request("/scenarios", { name: "Stress" }, true);
    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe("/api/v1/scenarios");
    expect(options.headers.Authorization).toBe("Bearer temporary-token");
    expect(options.headers["Idempotency-Key"]).toBeTruthy();
    expect(options.method).toBe("POST");
  });
  it("clearly marks unresolved dates", () => {
    expect(dateLabel(null)).toBe("Unresolved");
    expect(percent(85.0)).toBe("85%");
  });
});
