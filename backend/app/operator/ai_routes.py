"""Protected operator diagnostics for optional AI providers."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.ai.nvidia import (
    NvidiaNimClient,
    NvidiaNimConfig,
    NvidiaNimConfigurationError,
    NvidiaNimRequestError,
)
from app.operator.routes import NOINDEX_HEADERS, require_operator

router = APIRouter(prefix="/operator/ai", include_in_schema=False)


@router.get("/nvidia/smoke")
def nvidia_smoke(_operator: str = Depends(require_operator)) -> JSONResponse:
    """Run a tiny authenticated NVIDIA completion without persisting content."""

    try:
        config = NvidiaNimConfig.from_env()
        with NvidiaNimClient(config) as client:
            result = client.smoke_test()
    except NvidiaNimConfigurationError as exc:
        return JSONResponse(
            {
                "ok": False,
                "provider": "nvidia_nim",
                "error": "configuration_error",
                "detail": str(exc),
            },
            status_code=503,
            headers=NOINDEX_HEADERS,
        )
    except NvidiaNimRequestError as exc:
        return JSONResponse(
            {
                "ok": False,
                "provider": "nvidia_nim",
                "error": "provider_request_failed",
                "status_code": exc.status_code,
                "retryable": exc.retryable,
            },
            status_code=502,
            headers=NOINDEX_HEADERS,
        )

    return JSONResponse(
        {
            "ok": True,
            "provider": "nvidia_nim",
            "model": result.model,
            "finish_reason": result.finish_reason,
            "total_tokens": result.total_tokens,
            "response_match": result.text.strip() == "NVIDIA_NIM_OK",
        },
        headers=NOINDEX_HEADERS,
    )
