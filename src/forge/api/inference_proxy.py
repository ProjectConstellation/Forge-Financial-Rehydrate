"""Forge-only inference gateway: atomic admission and durable usage before returning a response."""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse


def mount(app: Any, forge: Any, check: Any) -> None:
    @app.get("/api/agent/inference/v1/models")
    async def models(request: Request) -> Any:
        check(request)
        return {"object": "list", "data": [{"id": m, "object": "model", "owned_by": "deepseek"}
                                           for m in (forge.s.deepseek.model, forge.s.deepseek.deep_model)]}

    @app.post("/api/agent/inference/v1/chat/completions")
    async def completions(request: Request) -> Any:
        check(request)
        if getattr(forge, "brain", None) is None:
            raise HTTPException(503, "Forge inference unavailable")
        body = await request.json()
        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            raise HTTPException(422, "messages required")
        model = str(body.get("model") or forge.s.deepseek.model)
        if model not in (forge.s.deepseek.model, forge.s.deepseek.deep_model):
            raise HTTPException(422, "model not configured in Forge")
        # Only inspect role identifiers; never persist prompt text.
        text = json.dumps(messages, ensure_ascii=False)
        match = re.search(r"\[forge-role:([a-z_]+)\]", text)
        role = match.group(1) if match else "unattributed"
        objective = re.search(r"(?:workflow_id=|workflow=)(wf_[a-zA-Z0-9]+)", text)
        try:
            max_tokens = int(body.get("max_completion_tokens") or body.get("max_tokens") or 4000)
            if not 1 <= max_tokens <= 16000:
                raise ValueError()
        except (TypeError, ValueError):
            raise HTTPException(422, "max tokens outside bounded request range")
        try:
            result = await forge.brain.c.chat(
                messages, agent=f"hermes_{role}", purpose="hermes_gateway",
                deep=model == forge.s.deepseek.deep_model,
                effort=str(body.get("reasoning_effort") or "high"),
                tools=body.get("tools"), max_tokens=max_tokens,
                opportunity_id=objective.group(1) if objective else None,
                json_mode=(body.get("response_format") or {}).get("type") == "json_object")
        except RuntimeError as exc:
            # Budget failure is terminal for this request, not retryable transport failure.
            if "admission denied" in str(exc):
                raise HTTPException(402, "Autonomous inference budget unavailable; deterministic work continues")
            raise HTTPException(503, "Upstream inference failed; cost uncertainty retained")
        message = {"role": "assistant", **result.raw_message}
        data = {"id": result.call_id, "object": "chat.completion", "model": result.model,
                "choices": [{"index": 0, "message": message,
                             "finish_reason": "tool_calls" if result.tool_calls else "stop"}],
                "usage": result.usage}
        if not body.get("stream"):
            return data
        delta = dict(message)
        if delta.get("tool_calls"):
            delta["tool_calls"] = [{"index": i, **t} for i, t in enumerate(delta["tool_calls"])]
        chunk = {"id": result.call_id, "object": "chat.completion.chunk", "model": result.model,
                 "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
        final = {"id": result.call_id, "object": "chat.completion.chunk", "model": result.model,
                 "choices": [{"index": 0, "delta": {}, "finish_reason": data["choices"][0]["finish_reason"]}],
                 "usage": result.usage}
        return StreamingResponse(iter(["data: " + json.dumps(chunk) + "\n\n",
                                       "data: " + json.dumps(final) + "\n\n", "data: [DONE]\n\n"]),
                                 media_type="text/event-stream")
