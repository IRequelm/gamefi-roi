"""Operator CLI for NVIDIA NIM connectivity and manual completions."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from app.ai.nvidia import (
    ChatMessage,
    NvidiaNimClient,
    NvidiaNimConfig,
    NvidiaNimConfigurationError,
    NvidiaNimRequestError,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GamCryp NVIDIA NIM operator utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "smoke",
        help="Run a tiny completion to verify NVIDIA_API_KEY and endpoint access.",
    )

    complete = subparsers.add_parser(
        "complete",
        help="Run an operator-triggered text completion. Nothing is published or stored.",
    )
    complete.add_argument("--prompt", required=True)
    complete.add_argument("--system")
    complete.add_argument("--model")
    complete.add_argument("--temperature", type=float, default=0.2)
    complete.add_argument("--max-tokens", type=int)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = NvidiaNimConfig.from_env()
        with NvidiaNimClient(config) as client:
            if args.command == "smoke":
                result = client.smoke_test()
            else:
                messages: list[ChatMessage] = []
                if args.system:
                    messages.append(ChatMessage(role="system", content=args.system))
                messages.append(ChatMessage(role="user", content=args.prompt))
                result = client.complete(
                    messages,
                    model=args.model,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                )
    except (NvidiaNimConfigurationError, NvidiaNimRequestError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "provider": "nvidia_nim",
                "model": result.model,
                "finish_reason": result.finish_reason,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
                "text": result.text,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
