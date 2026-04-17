"""Prometheus-style metrics for monitoring.

Exposes a /metrics endpoint compatible with Prometheus scraping.
Uses simple in-memory counters (lightweight, no external dependency).

Cardinality discipline
----------------------
Unbounded labels are the usual way Prometheus setups die. Per-endpoint label
values (e.g. raw URL paths like `/v1/contacts/<uuid>`) explode the series
count until the scrape itself becomes the bottleneck. We enforce two guards:

  * A per-metric series cap (`MAX_SERIES_PER_METRIC`). New series past the
    cap are folded into a synthetic `{name}{label="__overflow__"}` bucket
    so the counter doesn't lose information but the cardinality stops
    growing.
  * Callers should use `normalize_path()` on any `path` label so
    `/v1/contacts/a1b2...` becomes `/v1/contacts/:id` at collection time.
"""

import re
import time
from collections import defaultdict
from typing import Any

import structlog

logger = structlog.get_logger()

# Guardrails — generous enough for a CRM fleet, tight enough to keep the
# in-memory dict from unbounded growth.
MAX_SERIES_PER_METRIC = 500
MAX_HISTOGRAM_SAMPLES = 1000

# Regexes used by `normalize_path`. UUIDs first (most common), then any
# all-digit segment, then long hex blobs. Order matters — apply broader
# rules last.
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
_INT_SEG_RE = re.compile(r"/\d+(?=/|$)")
_HEX_SEG_RE = re.compile(r"/[0-9a-f]{16,}(?=/|$)", re.IGNORECASE)


def normalize_path(path: str) -> str:
    """Replace high-cardinality URL segments with stable placeholders.

    Examples:
      /v1/contacts/a1b2c3d4-5e6f-7a8b-9c0d-112233445566  → /v1/contacts/:id
      /v1/contacts/12345                                  → /v1/contacts/:id
      /v1/webhooks/instagram/deadbeef00...                → /v1/webhooks/instagram/:id
    """
    out = _UUID_RE.sub(":id", path)
    out = _INT_SEG_RE.sub("/:id", out)
    out = _HEX_SEG_RE.sub("/:id", out)
    return out


class Metrics:
    """Simple in-memory metrics collector with cardinality caps."""

    def __init__(self):
        self._counters: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._gauges: dict[str, float] = defaultdict(float)
        self._start_time = time.time()
        # Per-metric name → count of distinct label sets seen. Cheap to
        # maintain and lets us reject new series once we hit the cap.
        self._series_count: dict[str, int] = defaultdict(int)
        self._dropped: dict[str, int] = defaultdict(int)

    def _capped_key(self, name: str, labels: dict | None) -> str:
        """Return the storage key, folding to `__overflow__` past the cap."""
        if not labels:
            return name
        key = self._label_key(name, labels)
        # Already-seen series always accepted.
        if key in self._counters or key in self._histograms or key in self._gauges:
            return key
        if self._series_count[name] >= MAX_SERIES_PER_METRIC:
            self._dropped[name] += 1
            return self._label_key(name, {"label": "__overflow__"})
        self._series_count[name] += 1
        return key

    def inc(self, name: str, value: float = 1.0, labels: dict | None = None):
        """Increment a counter."""
        key = self._capped_key(name, labels)
        self._counters[key] += value

    def observe(self, name: str, value: float, labels: dict | None = None):
        """Record a histogram observation."""
        key = self._capped_key(name, labels)
        self._histograms[key].append(value)
        if len(self._histograms[key]) > MAX_HISTOGRAM_SAMPLES:
            self._histograms[key] = self._histograms[key][-MAX_HISTOGRAM_SAMPLES:]

    def set_gauge(self, name: str, value: float, labels: dict | None = None):
        """Set a gauge value."""
        key = self._capped_key(name, labels)
        self._gauges[key] = value

    def get_all(self) -> dict[str, Any]:
        """Get all metrics as a dictionary."""
        result = {
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {},
        }
        for key, values in self._histograms.items():
            if values:
                sorted_v = sorted(values)
                n = len(sorted_v)
                result["histograms"][key] = {
                    "count": n,
                    "sum": round(sum(values), 4),
                    "avg": round(sum(values) / n, 4),
                    "p50": sorted_v[int(n * 0.5)],
                    "p95": sorted_v[int(n * 0.95)],
                    "p99": sorted_v[min(int(n * 0.99), n - 1)],
                    "max": sorted_v[-1],
                }
        return result

    def format_prometheus(self) -> str:
        """Format metrics in Prometheus text exposition format."""
        lines = []
        lines.append(f"# HELP uptime_seconds Time since application start")
        lines.append(f"uptime_seconds {round(time.time() - self._start_time, 2)}")

        for key, value in self._counters.items():
            lines.append(f"{key} {value}")

        for key, value in self._gauges.items():
            lines.append(f"{key} {value}")

        for key, values in self._histograms.items():
            if values:
                n = len(values)
                lines.append(f"{key}_count {n}")
                lines.append(f"{key}_sum {round(sum(values), 4)}")

        return "\n".join(lines) + "\n"

    def _label_key(self, name: str, labels: dict | None) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


# Global singleton
metrics = Metrics()
