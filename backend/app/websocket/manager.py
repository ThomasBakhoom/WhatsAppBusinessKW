"""WebSocket connection manager with Redis pub/sub for cross-instance broadcasting.

WHY THIS EXISTS:
A single API pod can only hold ~thousands of WebSocket connections. Once
we scale horizontally, an event created on pod A must still reach a
client connected to pod B. Without a message broker, each pod only sees
its own local connections and broadcasts silently drop for clients on
other pods.

DESIGN:
  - Publishers call `broadcast_to_company(...)` or `send_to_user(...)`.
    These methods PUBLISH to a single Redis channel `kwgrowth:ws:events`.
  - Every API pod runs a long-lived subscriber (started in the lifespan).
    When a message arrives, the subscriber dispatches it to ALL locally
    connected sockets that match the target.
  - Publishing and local fan-out are therefore decoupled: the publisher
    never talks to sockets directly, it just writes to Redis. Each pod's
    subscriber handles its own local delivery.

This keeps the per-message path O(number_of_pods * local_sockets) rather
than O(total_sockets_everywhere), which is what you want.

Message envelope:
  {
    "target": "company" | "user",
    "company_id": "<uuid>",
    "user_id": "<uuid>"  # only when target == "user"
    "event": { ... arbitrary event body ... }
  }
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()

BROADCAST_CHANNEL = "kwgrowth:ws:events"


class ConnectionManager:
    """Manages local WebSocket connections + Redis pub/sub fan-out."""

    def __init__(self):
        # {company_id: {user_id: [websocket, ...]}}
        self._connections: dict[str, dict[str, list[WebSocket]]] = {}
        self._subscriber_task: asyncio.Task | None = None
        self._pubsub = None  # redis.asyncio.client.PubSub
        self._redis = None  # redis.asyncio.Redis
        self._running = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the Redis subscriber loop. Idempotent; safe to call once."""
        if self._running:
            return
        try:
            from app.core.redis import get_redis

            self._redis = await get_redis()
            self._pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
            await self._pubsub.subscribe(BROADCAST_CHANNEL)
            self._running = True
            self._subscriber_task = asyncio.create_task(self._consume_loop())
            logger.info("ws_subscriber_started", channel=BROADCAST_CHANNEL)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "ws_subscriber_start_failed",
                error=str(exc),
                hint="WebSocket broadcasts will only reach THIS pod until Redis recovers.",
            )

    async def stop(self) -> None:
        """Cancel the subscriber loop and release Redis resources."""
        self._running = False
        if self._subscriber_task is not None:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except (asyncio.CancelledError, Exception):
                pass
            self._subscriber_task = None
        if self._pubsub is not None:
            try:
                await self._pubsub.unsubscribe(BROADCAST_CHANNEL)
                await self._pubsub.close()
            except Exception:  # pragma: no cover - best effort
                pass
            self._pubsub = None
        logger.info("ws_subscriber_stopped")

    async def _consume_loop(self) -> None:
        """Background task: read pub/sub messages and dispatch locally."""
        assert self._pubsub is not None
        try:
            while self._running:
                try:
                    message = await self._pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                except Exception as exc:  # pragma: no cover - network hiccup
                    logger.warning("ws_pubsub_read_failed", error=str(exc))
                    await asyncio.sleep(0.5)
                    continue

                if message is None or message.get("type") != "message":
                    continue

                try:
                    envelope = json.loads(message["data"])
                except Exception:
                    logger.warning("ws_pubsub_bad_envelope")
                    continue

                await self._dispatch_local(envelope)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("ws_consume_loop_crashed", error=str(exc))

    async def _dispatch_local(self, envelope: dict[str, Any]) -> None:
        """Send an envelope to all matching locally-connected sockets."""
        target = envelope.get("target")
        company_id = envelope.get("company_id")
        event = envelope.get("event")

        if not target or not company_id or event is None:
            return

        data = json.dumps(event)

        if target == "company":
            await self._send_to_all_in_company(company_id, data)
        elif target == "user":
            user_id = envelope.get("user_id")
            if user_id:
                await self._send_to_user_sockets(company_id, user_id, data)

    # ── Local registry ────────────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, company_id: UUID, user_id: UUID):
        await websocket.accept()
        cid = str(company_id)
        uid = str(user_id)
        self._connections.setdefault(cid, {}).setdefault(uid, []).append(websocket)
        logger.info("ws_connected", company_id=cid, user_id=uid)

    def disconnect(self, websocket: WebSocket, company_id: UUID, user_id: UUID):
        cid = str(company_id)
        uid = str(user_id)
        if cid in self._connections and uid in self._connections[cid]:
            self._connections[cid][uid] = [
                ws for ws in self._connections[cid][uid] if ws is not websocket
            ]
            if not self._connections[cid][uid]:
                del self._connections[cid][uid]
            if not self._connections[cid]:
                del self._connections[cid]
        logger.info("ws_disconnected", company_id=cid, user_id=uid)

    def get_online_users(self, company_id: UUID) -> list[str]:
        cid = str(company_id)
        return list(self._connections.get(cid, {}).keys())

    # ── Publish (cross-instance) ──────────────────────────────────────────────

    async def broadcast_to_company(self, company_id: UUID, event: dict) -> None:
        """Publish an event to every user in a company across all pods."""
        await self._publish({
            "target": "company",
            "company_id": str(company_id),
            "event": event,
        })

    async def send_to_user(
        self, company_id: UUID, user_id: UUID, event: dict
    ) -> None:
        """Publish an event to a specific user across all pods."""
        await self._publish({
            "target": "user",
            "company_id": str(company_id),
            "user_id": str(user_id),
            "event": event,
        })

    async def _publish(self, envelope: dict) -> None:
        """Write the envelope to Redis pub/sub.

        Falls back to local-only dispatch if Redis is unavailable, so an
        outage doesn't silently swallow in-pod broadcasts.
        """
        try:
            from app.core.redis import get_redis

            redis = self._redis or await get_redis()
            await redis.publish(BROADCAST_CHANNEL, json.dumps(envelope))
        except Exception as exc:
            logger.warning(
                "ws_publish_fallback_to_local",
                error=str(exc),
            )
            await self._dispatch_local(envelope)

    # ── Local delivery (called by subscriber + fallback) ──────────────────────

    async def _send_to_all_in_company(self, cid: str, data: str) -> None:
        if cid not in self._connections:
            return
        dead: list[tuple[str, WebSocket]] = []
        for uid, sockets in list(self._connections[cid].items()):
            for ws in sockets:
                try:
                    await ws.send_text(data)
                except Exception:
                    dead.append((uid, ws))
        self._prune_dead(cid, dead)

    async def _send_to_user_sockets(self, cid: str, uid: str, data: str) -> None:
        if cid not in self._connections or uid not in self._connections[cid]:
            return
        dead: list[tuple[str, WebSocket]] = []
        for ws in list(self._connections[cid][uid]):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append((uid, ws))
        self._prune_dead(cid, dead)

    def _prune_dead(self, cid: str, dead: list[tuple[str, WebSocket]]) -> None:
        for uid, ws in dead:
            if cid in self._connections and uid in self._connections[cid]:
                self._connections[cid][uid] = [
                    s for s in self._connections[cid][uid] if s is not ws
                ]
                if not self._connections[cid][uid]:
                    del self._connections[cid][uid]
        if cid in self._connections and not self._connections[cid]:
            del self._connections[cid]


# Global singleton
ws_manager = ConnectionManager()
