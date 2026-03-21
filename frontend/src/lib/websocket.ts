// WebSocket client wrapper for FinClosePilot
import { WS_BASE } from "@/lib/api";
import type { WsEvent } from "@/lib/types";

type WsHandler = (event: WsEvent) => void;

export class PipelineWebSocket {
  private ws: WebSocket | null = null;
  private runId: string;
  private onMessage: WsHandler;
  private onStatusChange: (status: "CONNECTING" | "OPEN" | "CLOSED" | "ERROR") => void;

  constructor(
    runId: string,
    onMessage: WsHandler,
    onStatusChange: (s: "CONNECTING" | "OPEN" | "CLOSED" | "ERROR") => void
  ) {
    this.runId = runId;
    this.onMessage = onMessage;
    this.onStatusChange = onStatusChange;
  }

  connect(): void {
    this.onStatusChange("CONNECTING");
    this.ws = new WebSocket(`${WS_BASE}/${this.runId}`);

    this.ws.onopen = () => this.onStatusChange("OPEN");

    this.ws.onmessage = ({ data }) => {
      try {
        const parsed: WsEvent = JSON.parse(data);
        if (parsed.event === "PING") return; // ignore keep-alives
        this.onMessage(parsed);
      } catch {
        console.error("[WS] Failed to parse message", data);
      }
    };

    this.ws.onerror = () => this.onStatusChange("ERROR");
    this.ws.onclose = () => this.onStatusChange("CLOSED");
  }

  disconnect(): void {
    this.ws?.close();
    this.ws = null;
  }
}

/** Create and return a connected PipelineWebSocket instance */
export function connectToRun(
  runId: string,
  onMessage: WsHandler,
  onStatusChange: (s: "CONNECTING" | "OPEN" | "CLOSED" | "ERROR") => void
): PipelineWebSocket {
  const client = new PipelineWebSocket(runId, onMessage, onStatusChange);
  client.connect();
  return client;
}
