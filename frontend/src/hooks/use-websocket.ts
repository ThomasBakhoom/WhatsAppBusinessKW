"use client";

import { useEffect, useRef, useCallback } from "react";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 15000, 30000]; // exponential backoff, capped at 30s
const PING_INTERVAL = 25_000; // 25s — keeps the connection alive through proxies

export type WSEvent = {
  type: string;
  data: Record<string, unknown>;
};

type EventHandler = (event: WSEvent) => void;

/**
 * Auto-reconnecting WebSocket hook.
 *
 * Connects when the user has an access_token in localStorage.
 * Reconnects with exponential backoff on disconnect.
 * Sends a `ping` heartbeat every 25s to keep the connection alive
 * through load balancers that kill idle connections.
 *
 * Usage:
 *   const { lastEvent, connected } = useWebSocket();
 *   useEffect(() => { if (lastEvent?.type === "message.new") ... }, [lastEvent]);
 *
 * Or with a handler:
 *   useWebSocket({ onEvent: (e) => queryClient.invalidateQueries(["conversations"]) });
 */
export function useWebSocket(opts?: { onEvent?: EventHandler }) {
  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    const token =
      typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (!token) return; // not authenticated

    const ws = new WebSocket(`${WS_URL}?token=${token}`);
    wsRef.current = ws;

    ws.onopen = () => {
      attemptRef.current = 0; // reset backoff
      // Start heartbeat
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
      }, PING_INTERVAL);
    };

    ws.onmessage = (event) => {
      if (event.data === '{"type":"pong"}') return; // heartbeat ack
      try {
        const parsed: WSEvent = JSON.parse(event.data);
        opts?.onEvent?.(parsed);
      } catch {
        // Ignore unparseable frames
      }
    };

    ws.onclose = () => {
      // Clear heartbeat
      if (pingRef.current) {
        clearInterval(pingRef.current);
        pingRef.current = null;
      }
      if (!mountedRef.current) return;

      // Reconnect with backoff
      const delay =
        RECONNECT_DELAYS[
          Math.min(attemptRef.current, RECONNECT_DELAYS.length - 1)
        ];
      attemptRef.current += 1;
      setTimeout(connect, delay);
    };

    ws.onerror = () => {
      // onclose fires after onerror, so reconnect is handled there.
      ws.close();
    };
  }, [opts]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (pingRef.current) clearInterval(pingRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return {
    connected: wsRef.current?.readyState === WebSocket.OPEN,
  };
}
