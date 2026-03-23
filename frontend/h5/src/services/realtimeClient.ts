import { getRealtimeMeta, pollEvents } from "./gameClient";

import type { PollBatch, RealtimeEvent, WsMetaPayload } from "@/types";

type RealtimeHandlers = {
  onReady?: (meta: WsMetaPayload) => void;
  onEvents?: (batch: PollBatch) => void;
  onError?: (error: unknown) => void;
};

export class RealtimeClient {
  private readonly handlers: RealtimeHandlers;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private cursor: string | undefined;
  private stopped = false;
  private meta: WsMetaPayload | null = null;

  constructor(handlers: RealtimeHandlers = {}) {
    this.handlers = handlers;
  }

  async start() {
    this.stopped = false;
    try {
      const response = await getRealtimeMeta();
      this.meta = response.payload;
      this.handlers.onReady?.(response.payload);

      // Current backend only guarantees poll fallback. Keep the client
      // transport-neutral so the future WS bridge only replaces this branch.
      if (response.payload.transports.poll.available) {
        await this.pollOnce();
      }
    } catch (error) {
      this.handlers.onError?.(error);
    }
  }

  stop() {
    this.stopped = true;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }

  private async pollOnce() {
    if (this.stopped || !this.meta) {
      return;
    }

    try {
      const response = await pollEvents(this.cursor);
      this.cursor = response.payload.cursor;
      this.handlers.onEvents?.(response.payload);
    } catch (error) {
      this.handlers.onError?.(error);
    } finally {
      if (!this.stopped) {
        this.timer = setTimeout(
          () => void this.pollOnce(),
          this.meta.transports.poll.interval_ms,
        );
      }
    }
  }
}

export function isRealtimeEvent(value: unknown): value is RealtimeEvent {
  return Boolean(
    value &&
      typeof value === "object" &&
      (value as RealtimeEvent).type === "event" &&
      typeof (value as RealtimeEvent).event === "string",
  );
}
