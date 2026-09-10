"""Restart-safe, no-publish discovery intelligence worker."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.discovery.providers import CoinGeckoMarketProvider, GoogleTrendsProvider, ProviderResult, UnavailableProvider


@dataclass(frozen=True)
class DiscoveryWorkerConfig:
    state_file: Path = Path("data/local/discovery/worker_state.json")
    interval_seconds: int = 21600

    @classmethod
    def from_environment(cls) -> "DiscoveryWorkerConfig":
        return cls(
            state_file=Path(os.getenv("GAMEFI_DISCOVERY_WORKER_STATE_FILE", "data/local/discovery/worker_state.json")),
            interval_seconds=int(os.getenv("GAMEFI_DISCOVERY_WORKER_INTERVAL_SECONDS", "21600")),
        )


class DiscoveryWorker:
    def __init__(self, *, config: DiscoveryWorkerConfig | None = None) -> None:
        self.config = config or DiscoveryWorkerConfig.from_environment()

    def run_once(self) -> dict[str, object]:
        results = (
            GoogleTrendsProvider().probe(),
            CoinGeckoMarketProvider().query(),
            UnavailableProvider("youtube_data_api", "No authorized live API credentials configured.").probe(),
            UnavailableProvider("x_api", "No authorized live API credentials configured.").probe(),
        )
        now = datetime.now(UTC)
        payload: dict[str, object] = {
            "state_version": "discovery-worker-v1",
            "updated_at": now.isoformat(),
            "publish_performed": False,
            "providers": [_provider_payload(result) for result in results],
            "source_failures": [result.limitation for result in results if result.status == "BLOCKED" and result.limitation],
        }
        _atomic_write(self.config.state_file, payload)
        return payload

    def run_forever(self) -> None:
        if self.config.interval_seconds < 300:
            raise ValueError("discovery worker interval must be at least 300 seconds")
        while True:
            self.run_once()
            time.sleep(self.config.interval_seconds)


def _provider_payload(result: ProviderResult) -> dict[str, object]:
    return {
        "provider": result.provider,
        "status": result.status,
        "retrieved_at": result.retrieved_at.isoformat(),
        "signals": list(result.signals),
        "limitation": result.limitation,
    }


def _atomic_write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the fail-closed discovery intelligence worker.")
    parser.add_argument("--once", action="store_true", help="Run one provider cycle and exit.")
    args = parser.parse_args()
    worker = DiscoveryWorker()
    payload = worker.run_once() if args.once else worker.run_forever()
    if args.once:
        print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
