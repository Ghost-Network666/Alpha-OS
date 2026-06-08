import { describe, expect, it } from "vitest";
import { buildWsUrl, parseBootstrapWsUrl } from "./ws";

describe("buildWsUrl", () => {
  it("converts http base to ws /ws/state path", () => {
    expect(buildWsUrl("http://127.0.0.1:8080")).toBe(
      "ws://127.0.0.1:8080/ws/state"
    );
  });

  it("appends token query param when provided", () => {
    expect(buildWsUrl("http://127.0.0.1:8080", "abc token")).toBe(
      "ws://127.0.0.1:8080/ws/state?token=abc%20token"
    );
  });

  it("preserves existing ws_url path", () => {
    expect(buildWsUrl("ws://127.0.0.1:8080/ws/state", "t")).toBe(
      "ws://127.0.0.1:8080/ws/state?token=t"
    );
  });
});

describe("parseBootstrapWsUrl", () => {
  it("prefers explicit ws_url from bootstrap", () => {
    expect(
      parseBootstrapWsUrl({
        ws_url: "ws://127.0.0.1:8080/ws/state?token=x",
        api_url: "http://127.0.0.1:8080",
      })
    ).toBe("ws://127.0.0.1:8080/ws/state?token=x");
  });

  it("falls back to api_url", () => {
    expect(parseBootstrapWsUrl({ api_url: "http://127.0.0.1:9090" })).toBe(
      "ws://127.0.0.1:9090/ws/state"
    );
  });

  it("throws when bootstrap is incomplete", () => {
    expect(() => parseBootstrapWsUrl({})).toThrow(/missing ws_url/i);
  });
});