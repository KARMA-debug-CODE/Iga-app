"""Santa's model server: llama.cpp's llama-server running an open model on the school's own server.

Django talks to its OpenAI-compatible API (POST /v1/chat/completions) with the standard library only.
SANTA_URL points to it (empty = the model is not installed) and SANTA_API_KEY is the key both sides share.
Every problem is turned into one of the SantaError classes below, so callers can explain it plainly.
"""

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from django.conf import settings
from django.core.cache import cache

log = logging.getLogger(__name__)

HEALTH_KEY = "santa:health"
MAX_REPLY_BYTES = 1_000_000
# While a stream is open, llama-server sends a keep-alive line every 30 s, so a longer silence means trouble.
STREAM_READ_TIMEOUT = 75


class SantaError(Exception):
    """Santa's model could not answer. `code` says why, for the logs and the app."""

    code = "bad_reply"


class NotInstalled(SantaError):
    code = "not_installed"


class Loading(SantaError):
    """The model server is up but still loading the model (or downloading it on its first start)."""

    code = "loading"


class Unreachable(SantaError):
    code = "unreachable"


class Timeout(SantaError):
    code = "timeout"


class BadReply(SantaError):
    code = "bad_reply"


class ToolsRejected(BadReply):
    """The server refused a request that offered tools (its chat template may not support them)."""


class TooLong(BadReply):
    """The question with its context is longer than one of the model server's slots can hold."""

    code = "too_long"


@dataclass
class Reply:
    """One answer from the model: its text, any tool calls, why it stopped, and token counts."""

    content: str = ""
    tool_calls: list = field(default_factory=list)  # [{"id", "name", "arguments"}]
    finish_reason: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0


def installed():
    return bool(settings.SANTA_URL)


# The model server is an internal service: never send requests to it through an outbound proxy.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _url(path):
    return settings.SANTA_URL.rstrip("/") + path


def _headers():
    headers = {"Content-Type": "application/json"}
    if settings.SANTA_API_KEY:
        headers["Authorization"] = f"Bearer {settings.SANTA_API_KEY}"
    return headers


def remember_health(state, seconds=None):
    """Keep the model server's state for a few seconds, so status checks don't ask it on every page."""
    try:
        cache.set(HEALTH_KEY, state, seconds or (15 if state == "ready" else 5))
    except Exception:  # noqa: BLE001 - a cache outage must not break the tutor
        log.warning("Could not cache Santa's health", exc_info=True)


def cached_health():
    try:
        return cache.get(HEALTH_KEY)
    except Exception:  # noqa: BLE001
        return None


def health(timeout=3):
    """'ready', 'loading', 'unreachable' or 'not_installed'. GET /health answers 503 while the model loads."""
    if not installed():
        return "not_installed"
    state = cached_health()
    if state:
        return state
    try:
        with _opener.open(urllib.request.Request(_url("/health"), headers=_headers()), timeout=timeout):
            state = "ready"
    except urllib.error.HTTPError as exc:
        state = "loading" if exc.code == 503 else "unreachable"
    except (urllib.error.URLError, OSError, ValueError):
        state = "unreachable"
    remember_health(state)
    return state


def _error_details(exc):
    """(message, type) from llama-server's {"error": {"code", "message", "type"}} body."""
    try:
        body = json.loads(exc.read(65536).decode("utf-8", "replace"))
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            return str(error.get("message", "")), str(error.get("type", ""))
        return str(error or ""), ""
    except (ValueError, OSError, AttributeError):
        return "", ""


def _http_error(exc, offered_tools):
    message, kind = _error_details(exc)
    if kind == "exceed_context_size_error" or "context size" in message.lower():
        return TooLong(f"HTTP {exc.code}: {message}")
    if exc.code == 503:
        if "loading" in message.lower():
            remember_health("loading")
            return Loading(message)
        return Unreachable(f"HTTP 503: {message}")
    if exc.code in (401, 403):
        log.error("Santa's model server refused the API key: check that SANTA_API_KEY matches its LLAMA_API_KEY")
        return BadReply(f"HTTP {exc.code}: {message}")
    if offered_tools and exc.code in (400, 404, 422, 500, 501):
        return ToolsRejected(f"HTTP {exc.code}: {message}")
    return BadReply(f"HTTP {exc.code}: {message}")


def _open(payload, timeout):
    request = urllib.request.Request(
        _url("/v1/chat/completions"), data=json.dumps(payload).encode(), method="POST", headers=_headers()
    )
    try:
        return _opener.open(request, timeout=max(1.0, timeout))
    except urllib.error.HTTPError as exc:
        raise _http_error(exc, bool(payload.get("tools"))) from exc
    except TimeoutError as exc:
        raise Timeout(str(exc)) from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise Timeout(str(exc.reason)) from exc
        remember_health("unreachable")
        raise Unreachable(str(exc.reason)) from exc
    except (OSError, ValueError) as exc:
        remember_health("unreachable")
        raise Unreachable(str(exc)) from exc


# A reply that is valid JSON but not shaped like an answer (another service at SANTA_URL, a proxy's error
# page) raises one of these while it is read; they all mean BadReply.
SHAPE_ERRORS = (AttributeError, IndexError, KeyError, TypeError, ValueError)


def _text(value):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise TypeError(f"text expected, got {type(value).__name__}")
    return value


def _usage(reply, data):
    usage = data.get("usage") or {}
    reply.prompt_tokens += int(usage.get("prompt_tokens") or 0)
    reply.completion_tokens += int(usage.get("completion_tokens") or 0)


def _tool_calls(raw):
    calls = []
    for i, call in enumerate(raw or []):
        function = call.get("function") or {}
        arguments = function.get("arguments") or ""
        calls.append(
            {
                "id": _text(call.get("id")) or f"call_{i}",
                "name": _text(function.get("name")),
                "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments),
            }
        )
    return calls


def chat(payload, deadline):
    """Send a chat request and wait for the whole answer. Returns a Reply."""
    if not installed():
        raise NotInstalled
    try:
        with _open({**payload, "stream": False}, deadline - time.monotonic()) as response:
            data = json.loads(response.read(MAX_REPLY_BYTES).decode("utf-8"))
    except TimeoutError as exc:
        raise Timeout(str(exc)) from exc
    except (OSError, ValueError) as exc:
        raise BadReply(str(exc)) from exc
    if not isinstance(data, dict) or data.get("error") or not data.get("choices"):
        raise BadReply(f"unexpected reply: {str(data)[:200]}")
    try:
        choice = data["choices"][0]
        message = choice.get("message") or {}
        reply = Reply(
            content=_text(message.get("content")),
            tool_calls=_tool_calls(message.get("tool_calls")),
            finish_reason=_text(choice.get("finish_reason")),
        )
        _usage(reply, data)
    except SHAPE_ERRORS as exc:
        raise BadReply(f"unexpected reply: {str(data)[:200]}") from exc
    remember_health("ready")
    return reply


def chat_stream(payload, deadline):
    """Send a chat request and yield the answer's text as it arrives ("" for a keep-alive ping).

    llama-server sends Server-Sent Events: `data: {json}` lines with the text in choices[0].delta.content,
    comment lines starting with ":" to keep the connection open, and `data: [DONE]` at the end.
    Returns (as the generator's value) the finished Reply."""
    if not installed():
        raise NotInstalled
    reply = Reply()
    calls = {}  # tool calls arrive in pieces, by index
    request = {**payload, "stream": True, "stream_options": {"include_usage": True}}
    response = _open(request, min(deadline - time.monotonic(), STREAM_READ_TIMEOUT))
    try:
        while True:
            if time.monotonic() > deadline:
                raise Timeout("the answer took too long")
            try:
                line = response.readline(MAX_REPLY_BYTES)
            except TimeoutError as exc:
                raise Timeout(str(exc)) from exc
            except (OSError, ValueError) as exc:
                raise Unreachable(str(exc)) from exc
            if not line:
                if reply.finish_reason:
                    break  # finished, only the closing [DONE] is missing
                raise Unreachable("the connection closed before the answer ended")
            line = line.decode("utf-8", "replace").strip()
            if not line:
                continue
            if line.startswith(":"):
                yield ""
                continue
            if not line.startswith("data:"):
                continue  # "event:" or "id:" lines carry nothing Santa needs
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except ValueError as exc:
                raise BadReply(f"unreadable chunk: {data[:200]}") from exc
            if not isinstance(chunk, dict):
                raise BadReply(f"unexpected chunk: {data[:200]}")
            if chunk.get("error"):
                raise BadReply(f"error during the answer: {str(chunk['error'])[:200]}")
            try:
                text = _read_chunk(chunk, reply, calls)
            except SHAPE_ERRORS as exc:
                raise BadReply(f"unexpected chunk: {data[:200]}") from exc
            if text:
                reply.content += text
                yield text
    finally:
        response.close()  # also tells llama-server to stop writing if the student pressed Stop
    try:
        reply.tool_calls = _tool_calls([calls[i] for i in sorted(calls)])
    except SHAPE_ERRORS as exc:
        raise BadReply("unexpected tool calls") from exc
    remember_health("ready")
    return reply


def _read_chunk(chunk, reply, calls):
    """One streamed chunk: notes its token counts, tool-call pieces and finish reason, and returns its text."""
    _usage(reply, chunk)
    text = ""
    for choice in chunk.get("choices") or []:
        delta = choice.get("delta") or {}
        text += _text(delta.get("content"))
        for piece in delta.get("tool_calls") or []:
            index = piece.get("index", len(calls))
            if not isinstance(index, int):
                raise TypeError("a tool call's index must be a number")
            call = calls.setdefault(index, {"id": "", "function": {"name": "", "arguments": ""}})
            call["id"] = _text(piece.get("id")) or call["id"]
            function = piece.get("function") or {}
            call["function"]["name"] += _text(function.get("name"))
            call["function"]["arguments"] += _text(function.get("arguments"))
        if choice.get("finish_reason"):
            reply.finish_reason = _text(choice["finish_reason"])
    return text
