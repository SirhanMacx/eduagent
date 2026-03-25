"""Claw-ED conversational agent -- LLM with tool use.

The agent loop:
  1. Send message + tool definitions to LLM
  2. If LLM returns tool_calls -> execute tools, feed results back
  3. If LLM returns text -> return it
  4. Repeat (max 5 iterations to prevent infinite loops)

Works with Anthropic (native tool use), OpenAI (function calling),
and Ollama (when model supports tools, falls back to prompt-based).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from clawed.models import AppConfig, LLMProvider
from clawed.tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

_MAX_TOOL_ITERATIONS = 5


async def run_agent(
    message: str,
    system: str,
    teacher_id: str = "",
    config: AppConfig | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
) -> str:
    """Run the conversational agent with tool use.

    Returns the final text response after any tool calls are resolved.
    """
    config = config or AppConfig.load()

    messages: list[dict[str, Any]] = list(conversation_history or [])
    messages.append({"role": "user", "content": message})

    for _iteration in range(_MAX_TOOL_ITERATIONS):
        # Try native tool calling first
        if config.provider in (LLMProvider.ANTHROPIC, LLMProvider.OPENAI):
            response = await _call_with_native_tools(messages, system, config)
        else:
            # Ollama -- try native tools, fall back to prompt-based
            response = await _call_with_ollama_tools(messages, system, config)

        # If the response is plain text (no tool calls), we're done
        if response["type"] == "text":
            return response["content"]

        # Execute tool calls
        if response["type"] == "tool_calls":
            for tool_call in response["tool_calls"]:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("arguments", {})
                logger.info("Agent calling tool: %s(%s)", tool_name, tool_args)

                result = await execute_tool(tool_name, tool_args, teacher_id)

                # Add the assistant's tool call and the result to the conversation
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", tool_name),
                    "content": result,
                })
            continue

    # Exhausted iterations -- return a fallback
    return "I tried to help but hit my iteration limit. Could you rephrase your request?"


async def _call_with_native_tools(
    messages: list[dict[str, Any]], system: str, config: AppConfig
) -> dict[str, Any]:
    """Call Anthropic or OpenAI with native tool support."""
    if config.provider == LLMProvider.ANTHROPIC:
        return await _anthropic_with_tools(messages, system, config)
    else:
        return await _openai_with_tools(messages, system, config)


async def _anthropic_with_tools(
    messages: list[dict[str, Any]], system: str, config: AppConfig
) -> dict[str, Any]:
    """Call Anthropic API with tool use."""
    import httpx

    from clawed.config import get_api_key

    api_key = get_api_key("anthropic")
    if not api_key:
        raise ValueError("No Anthropic API key configured")

    # Convert tool definitions to Anthropic format
    tools = []
    for t in TOOL_DEFINITIONS:
        f = t["function"]
        tools.append({
            "name": f["name"],
            "description": f["description"],
            "input_schema": f["parameters"],
        })

    # Convert messages to Anthropic format
    anthropic_messages: list[dict[str, Any]] = []
    for m in messages:
        if m["role"] == "tool":
            anthropic_messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": m.get("tool_call_id", ""),
                    "content": m["content"],
                }],
            })
        elif m["role"] == "assistant" and m.get("tool_calls"):
            tc = m["tool_calls"][0]
            anthropic_messages.append({
                "role": "assistant",
                "content": [{
                    "type": "tool_use",
                    "id": tc.get("id", tc["name"]),
                    "name": tc["name"],
                    "input": tc.get("arguments", {}),
                }],
            })
        elif m.get("content"):
            anthropic_messages.append({"role": m["role"], "content": m["content"]})

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": config.anthropic_model,
                "max_tokens": 4096,
                "system": system,
                "tools": tools,
                "messages": anthropic_messages,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    # Check if the response contains tool use
    for block in data.get("content", []):
        if block.get("type") == "tool_use":
            return {
                "type": "tool_calls",
                "tool_calls": [{
                    "id": block["id"],
                    "name": block["name"],
                    "arguments": block.get("input", {}),
                }],
            }
        if block.get("type") == "text":
            return {"type": "text", "content": block["text"]}

    return {"type": "text", "content": data.get("content", [{}])[0].get("text", "")}


async def _openai_with_tools(
    messages: list[dict[str, Any]], system: str, config: AppConfig
) -> dict[str, Any]:
    """Call OpenAI API with function calling."""
    import httpx

    from clawed.config import get_api_key

    api_key = get_api_key("openai")
    if not api_key:
        raise ValueError("No OpenAI API key configured")

    # Build messages with system
    oai_messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in messages:
        if m["role"] == "tool":
            oai_messages.append({
                "role": "tool",
                "tool_call_id": m.get("tool_call_id", ""),
                "content": m["content"],
            })
        elif m["role"] == "assistant" and m.get("tool_calls"):
            tc = m["tool_calls"][0]
            oai_messages.append({
                "role": "assistant",
                "tool_calls": [{
                    "id": tc.get("id", tc["name"]),
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc.get("arguments", {})),
                    },
                }],
            })
        elif m.get("content"):
            oai_messages.append({"role": m["role"], "content": m["content"]})

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.openai_model,
                "messages": oai_messages,
                "tools": TOOL_DEFINITIONS,
                "temperature": 0.7,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    choice = data["choices"][0]
    msg = choice["message"]

    if msg.get("tool_calls"):
        tc = msg["tool_calls"][0]
        return {
            "type": "tool_calls",
            "tool_calls": [{
                "id": tc["id"],
                "name": tc["function"]["name"],
                "arguments": json.loads(tc["function"]["arguments"]),
            }],
        }

    return {"type": "text", "content": msg.get("content", "")}


async def _call_with_ollama_tools(
    messages: list[dict[str, Any]], system: str, config: AppConfig
) -> dict[str, Any]:
    """Call Ollama with tool support (native if available, prompt-based fallback)."""
    import httpx

    from clawed.config import get_api_key

    base_url = config.ollama_base_url.rstrip("/")
    api_key = get_api_key("ollama")

    # Use OpenAI-compatible endpoint which supports tools
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Determine endpoint
    if "api.ollama.com" in base_url or "ollama.com" in base_url:
        url = f"{base_url}/chat/completions"
    else:
        url = f"{base_url}/v1/chat/completions"

    oai_messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for m in messages:
        if m["role"] == "tool":
            oai_messages.append({
                "role": "tool",
                "tool_call_id": m.get("tool_call_id", ""),
                "content": m["content"],
            })
        elif m["role"] == "assistant" and m.get("tool_calls"):
            tc = m["tool_calls"][0]
            oai_messages.append({
                "role": "assistant",
                "tool_calls": [{
                    "id": tc.get("id", tc["name"]),
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc.get("arguments", {})),
                    },
                }],
            })
        elif m.get("content"):
            oai_messages.append({"role": m["role"], "content": m["content"]})

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                url,
                headers=headers,
                json={
                    "model": config.ollama_model,
                    "messages": oai_messages,
                    "tools": TOOL_DEFINITIONS,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        msg = choice["message"]

        if msg.get("tool_calls"):
            tc = msg["tool_calls"][0]
            fn_args = tc["function"]["arguments"]
            return {
                "type": "tool_calls",
                "tool_calls": [{
                    "id": tc.get("id", tc["function"]["name"]),
                    "name": tc["function"]["name"],
                    "arguments": json.loads(fn_args) if isinstance(fn_args, str) else fn_args,
                }],
            }

        return {"type": "text", "content": msg.get("content", "")}

    except Exception as e:
        # Fallback: no tool support, just chat without tools
        logger.debug("Ollama tool call failed (%s), falling back to plain chat", e)
        return await _ollama_plain_chat(messages, system, config)


async def _ollama_plain_chat(
    messages: list[dict[str, Any]], system: str, config: AppConfig
) -> dict[str, Any]:
    """Plain Ollama chat without tools (fallback)."""
    from clawed.llm import LLMClient
    from clawed.model_router import route

    routed_config = route("quick_answer", config)
    client = LLMClient(routed_config)

    # Flatten messages to a prompt
    prompt = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in messages if m.get("content")
    )
    response = await client.generate(prompt=prompt, system=system, temperature=0.7, max_tokens=800)
    return {"type": "text", "content": response}
