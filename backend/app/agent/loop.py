"""The while-loop agent orchestrator — LLM decides tools, we execute them."""

import json
from collections.abc import AsyncGenerator

from google import genai
from google.genai import types

from app.agent.classifier import Intent, classify, OFF_TOPIC_MESSAGE, OTHER_APPLIANCE_MESSAGE
from app.agent.system_prompt import SYSTEM_PROMPT
from app.config import GEMINI_API_KEY, GEMINI_MODEL, MAX_AGENT_ITERATIONS
from app.tools.registry import execute_tool, get_tool_declarations

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


async def run_agent(
    messages: list[dict],
    session_id: str,
) -> AsyncGenerator[dict, None]:
    """Run the agent loop. Yields SSE event dicts.

    Event types:
      status         → tool execution status
      product_card   → full part data for rich card rendering
      compatibility_result → yes/no badge
      diagnosis      → causes + recommended parts
      text_delta     → streamed LLM text tokens
      suggestions    → quick-reply options after answer
      error          → recoverable error message
      done           → stream complete
    """
    # Classify the latest user message
    latest_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            latest_message = msg.get("content", "")
            break

    intent = classify(latest_message)

    # Handle off-topic/other-appliance without LLM call
    if intent == Intent.OFF_TOPIC:
        yield {"event": "text_delta", "data": OFF_TOPIC_MESSAGE}
        yield {"event": "done", "data": ""}
        return

    if intent == Intent.OTHER_APPLIANCE:
        yield {"event": "text_delta", "data": OTHER_APPLIANCE_MESSAGE}
        yield {"event": "done", "data": ""}
        return

    # Build Gemini message format
    gemini_contents = _build_contents(messages)
    tools = get_tool_declarations()

    iterations = 0
    while iterations < MAX_AGENT_ITERATIONS:
        iterations += 1

        try:
            response = _get_client().models.generate_content(
                model=GEMINI_MODEL,
                contents=gemini_contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=tools,
                    temperature=0.3,
                ),
            )
        except Exception as e:
            yield {"event": "error", "data": f"LLM error: {str(e)}"}
            yield {"event": "done", "data": ""}
            return

        # Check for tool calls
        has_tool_calls = False
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    has_tool_calls = True
                    break

        if not has_tool_calls:
            # Text response — extract and yield
            text = ""
            if response.candidates and response.candidates[0].content:
                for part in response.candidates[0].content.parts:
                    if part.text:
                        text += part.text

            if text:
                yield {"event": "text_delta", "data": text}

            yield {"event": "done", "data": ""}
            return

        # Process tool calls
        tool_results = []
        for part in response.candidates[0].content.parts:
            if not part.function_call:
                continue

            call = part.function_call
            tool_name = call.name
            tool_args = dict(call.args) if call.args else {}

            yield {"event": "status", "data": f"Running {tool_name}..."}

            # Execute tool
            result = execute_tool(tool_name, tool_args)

            # Emit structured events for specific tool results
            for evt in _emit_structured_events(tool_name, result):
                yield evt

            tool_results.append(types.Part(function_response=types.FunctionResponse(
                name=tool_name,
                response=result,
            )))

        # Append assistant message (with tool calls) + tool results to conversation
        gemini_contents.append(response.candidates[0].content)
        gemini_contents.append(types.Content(
            role="user",
            parts=tool_results,
        ))

    # Max iterations reached
    yield {"event": "error", "data": "I needed too many steps to answer that. Could you try rephrasing?"}
    yield {"event": "done", "data": ""}


def _build_contents(messages: list[dict]) -> list[types.Content]:
    """Convert our message format to Gemini Content objects."""
    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Map roles
        if role == "assistant":
            gemini_role = "model"
        else:
            gemini_role = "user"

        contents.append(types.Content(
            role=gemini_role,
            parts=[types.Part(text=content)],
        ))
    return contents


def _emit_structured_events(tool_name: str, result: dict) -> list[dict]:
    """Emit structured SSE events based on tool results."""
    events = []

    if tool_name == "get_product_details" and result.get("found"):
        events.append({
            "event": "product_card",
            "data": json.dumps({
                "ps_number": result.get("ps_number", ""),
                "name": result.get("name", ""),
                "brand": result.get("brand", ""),
                "price": result.get("price", ""),
                "rating": result.get("rating", ""),
                "review_count": result.get("review_count", ""),
                "in_stock": result.get("in_stock", False),
                "image_url": result.get("image_url", ""),
                "source_url": result.get("source_url", ""),
                "installation_difficulty": result.get("installation_difficulty", ""),
            }),
        })

    elif tool_name == "search_parts":
        for part in result.get("parts", [])[:3]:
            events.append({
                "event": "product_card",
                "data": json.dumps(part),
            })

    elif tool_name == "check_compatibility":
        events.append({
            "event": "compatibility_result",
            "data": json.dumps({
                "compatible": result.get("compatible"),
                "confidence": result.get("confidence", ""),
                "part_number": result.get("part_number", ""),
                "model_number": result.get("model_number", ""),
                "message": result.get("message", ""),
            }),
        })

    elif tool_name == "diagnose_symptom" and result.get("found"):
        events.append({
            "event": "diagnosis",
            "data": json.dumps({
                "symptom": result.get("matched_symptom", ""),
                "causes": result.get("causes", []),
                "recommended_parts": result.get("recommended_parts", []),
                "follow_up_questions": result.get("follow_up_questions", []),
            }),
        })

    return events
