"""
LiteLLM Proxy Endpoint.

Provides an Anthropic-compatible messages API endpoint that forwards
requests to LiteLLM for multi-provider model inference support.
"""

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter()


def remove_cache_control(obj: Any) -> Any:
    """
    Recursively remove all cache_control fields from a data structure.

    This is needed for non-Claude models that don't support prompt caching.

    Args:
        obj: The object to process (dict, list, or primitive)

    Returns:
        The object with all cache_control fields removed
    """
    if isinstance(obj, dict):
        # Create a new dict without cache_control
        return {
            k: remove_cache_control(v) for k, v in obj.items() if k != "cache_control"
        }
    elif isinstance(obj, list):
        # Process each item in the list
        return [remove_cache_control(item) for item in obj]
    else:
        # Return primitives as-is
        return obj


@router.post("/v1/messages")
async def litellm_messages_proxy(request: Request):
    """
    LiteLLM proxy endpoint for Anthropic-compatible messages API.

    This endpoint forwards requests to LiteLLM for model inference,
    allowing the SDK client to use this server as ANTHROPIC_BASE_URL.

    Supports:
    - Streaming responses
    - Multiple model providers via LiteLLM
    - Compatible with Anthropic Messages API format
    - Automatic removal of cache_control for non-Claude models
    """
    try:
        # Try to import litellm
        try:
            import litellm
            litellm.success_callback = ["langfuse"] 
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="LiteLLM is not installed. Install with: pip install litellm",
            )

        body = await request.json()

        # Check if model is a Claude model
        model = body.get("model", "")
        is_claude_model = "claude" in model.lower()

        # Remove cache_control if not a Claude model
        if not is_claude_model:
            body = remove_cache_control(body)

        # Check if streaming is requested
        is_streaming = body.get("stream", False)

        if is_streaming:
            # Streaming response
            async def generate_stream():
                try:
                    # Forward to LiteLLM with streaming
                    response = await litellm.litellm.anthropic.messages.acreate(**body)

                    async for chunk in response:
                        # Forward raw chunk in SSE format
                        if hasattr(chunk, "model_dump_json"):
                            # Pydantic model
                            yield f"data: {chunk.model_dump_json()}\n\n"
                        elif hasattr(chunk, "json"):
                            # Dict-like with json method
                            yield f"data: {chunk.json()}\n\n"
                        else:
                            # Plain dict
                            yield f"data: {json.dumps(chunk)}\n\n"

                except Exception as e:
                    error_data = {
                        "error": {"message": str(e), "type": type(e).__name__}
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
            )
        else:
            # Non-streaming response
            try:
                response = await litellm.litellm.anthropic.messages.acreate(**body)

                # Convert response to dict
                if hasattr(response, "model_dump"):
                    return response.model_dump()
                elif hasattr(response, "dict"):
                    return response.dict()
                else:
                    return response

            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail={"error": {"message": str(e), "type": type(e).__name__}},
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": str(e), "type": type(e).__name__}},
        )
