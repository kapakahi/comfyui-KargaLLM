"""
KargaNodes — LLM API wrapper
Supports LM Studio and Ollama via OpenAI-compatible endpoints.
"""
import requests
import time

# ============================================================================
# USER CONFIGURATION
# Edit this section to match your setup. Start from the top.
# ============================================================================


# ----------------------------------------------------------------------------
# CRITICAL — required for basic operation
# ----------------------------------------------------------------------------

# Your LLM server URL
# LM Studio default : http://127.0.0.1:1234
# Ollama default    : http://127.0.0.1:11434
# Remote machine    : http://192.168.1.x:PORT
DEFAULT_BASE_URL = "http://127.0.0.1:1234"

# API type — controls which endpoints are used
# "openai"  : /v1/chat/completions + /v1/models  (LM Studio, Ollama, any compat server)
# "ollama"  : /api/chat + /api/tags              (Ollama native API only)
API_TYPE = "openai"

# API key — leave empty if not required
# Required for : hosted OpenAI-compatible servers, Anthropic, etc.
# Not required : LM Studio, Ollama (local)
API_KEY = 


# ----------------------------------------------------------------------------
# IMPORTANT — affects reliability and performance
# ----------------------------------------------------------------------------

# How long to wait for a response before giving up (seconds)
# Increase if you have a slow machine or are running large models
# Note: this is the global default — per-run timeout is set in the Options node
DEFAULT_TIMEOUT = 120

# How many times to retry a failed request before giving up
# Set to 0 to disable retries
MAX_RETRIES = 2

# How long to wait between retries (seconds)
RETRY_DELAY = 3


# ----------------------------------------------------------------------------
# USEFUL — quality of life
# ----------------------------------------------------------------------------

# Connect to LLM server on ComfyUI startup to populate the model dropdown
# True  = fetch models when ComfyUI starts (server must already be running)
# False = skip startup connection, models load on first node execution (recommended for publishing)
CONNECT_ON_STARTUP = True

# Fallback model name if none is selected in the node
# Leave empty to show an error instead of silently falling back
DEFAULT_MODEL = ""

# Ollama only — how long to keep the model loaded in VRAM after a request
# "5m"  = 5 minutes
# "1h"  = 1 hour
# "0"   = unload immediately after each request (saves VRAM, slower)
# "-1"  = keep loaded forever until Ollama is restarted
OLLAMA_KEEP_ALIVE = "5m"

# Maximum image size in megapixels before auto-resizing
# Lower  = faster processing, less VRAM usage
# Higher = more detail preserved for vision models
# Recommended: 1.0 - 4.0
MAX_IMAGE_MEGAPIXELS = 2.0

# Verify SSL certificates for HTTPS connections
# Set to False if connecting to a remote server with a self-signed certificate
# Warning: setting False reduces security — only use on trusted networks
VERIFY_SSL = True


# ----------------------------------------------------------------------------
# ADVANCED — for power users
# ----------------------------------------------------------------------------

# Force JSON output format on every request
# True  = appends JSON-only instruction to every system prompt
# False = plain text output (default, recommended)
# Note: for most ComfyUI workflows this is not useful — leave False
FORCE_JSON_OUTPUT = False


# ----------------------------------------------------------------------------
# DEBUG — troubleshooting and development
# ----------------------------------------------------------------------------

# Print all requests and responses to the ComfyUI console
# Useful when setting up or diagnosing issues
# Leave False in normal use — generates a lot of output
VERBOSE_LOGGING = False

# HTTP proxy for requests (leave empty if not needed)
# Format: "http://user:pass@proxy.example.com:8080"
# Useful for: corporate networks, tunneling to remote servers
HTTP_PROXY = ""


# ============================================================================
# END OF USER CONFIGURATION — do not edit below this line
# ============================================================================


def _normalize_base(url: str) -> str:
    url = str(url).strip().rstrip("/")
    for suffix in ("/v1", "/api", "/api/tags", "/api/chat",
                   "/v1/chat/completions", "/v1/models"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
            break
    return url or DEFAULT_BASE_URL


def _build_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


def _build_proxies() -> dict | None:
    if HTTP_PROXY:
        return {"http": HTTP_PROXY, "https": HTTP_PROXY}
    return None


def _request_with_retry(method: str, url: str, **kwargs) -> requests.Response:
    kwargs.setdefault("headers", _build_headers())
    kwargs.setdefault("verify", VERIFY_SSL)
    proxies = _build_proxies()
    if proxies:
        kwargs["proxies"] = proxies

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            if VERBOSE_LOGGING and attempt > 0:
                print(f"[Karga LLM] Retry {attempt}/{MAX_RETRIES} → {url}")
            return requests.request(method, url, **kwargs)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                if VERBOSE_LOGGING:
                    print(f"[Karga LLM] Request failed ({e}), retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
    raise last_error


def _extract_error(response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            for key in ("error", "message"):
                val = payload.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
    except ValueError:
        pass
    text = (response.text or "").strip()
    return text[:300] if text else f"HTTP {response.status_code}"


def _extract_thinking(content: str, message: dict, enable_thinking: bool) -> str:
    if not enable_thinking:
        return ""
    thinking = message.get("reasoning_content", "").strip()
    if thinking:
        return thinking
    if "<think>" in content:
        import re
        match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
        if match:
            return match.group(1).strip()
    return ""


def _strip_think_tags(content: str) -> str:
    if "</think>" in content:
        return content[content.find("</think>") + 8:].strip()
    return content


def discover_models(base_url: str):
    base = _normalize_base(base_url)
    if API_TYPE == "ollama":
        url = f"{base}/api/tags"
        try:
            resp = _request_with_retry("GET", url, timeout=10)
            if resp.status_code == 200:
                data  = resp.json()
                names = [m["name"] for m in data.get("models", []) if "name" in m]
                if names:
                    return sorted(set(names), key=str.lower), f"Found {len(names)} model(s)."
                return [], "Ollama responded but no models found. Run 'ollama pull <model>'."
            return [], f"Ollama returned HTTP {resp.status_code}."
        except requests.exceptions.ConnectionError:
            return [], f"Could not connect to Ollama at {base}."
        except Exception as e:
            return [], f"Error: {e}"
    else:
        url = f"{base}/v1/models"
        try:
            resp = _request_with_retry("GET", url, timeout=10)
            if resp.status_code == 200:
                data  = resp.json()
                names = [
                    item.get("id", "").strip()
                    for item in data.get("data", [])
                    if isinstance(item, dict) and item.get("id", "").strip()
                ]
                if names:
                    return sorted(set(names), key=str.lower), f"Found {len(names)} model(s)."
                return [], "Server responded but no models found."
            return [], f"Server returned HTTP {resp.status_code}."
        except requests.exceptions.ConnectionError:
            return [], f"Could not connect to {base}. Is LM Studio / Ollama running?"
        except Exception as e:
            return [], f"Error: {e}"


def is_available(base_url: str) -> bool:
    base = _normalize_base(base_url)
    try:
        endpoint = f"{base}/api/tags" if API_TYPE == "ollama" else f"{base}/v1/models"
        return _request_with_retry("GET", endpoint, timeout=5).status_code == 200
    except Exception:
        return False


def generate_chat(
    base_url: str,
    model: str,
    messages: list,
    temperature: float = 0.8,
    top_k: int = 40,
    top_p: float = 0.95,
    min_p: float = 0.05,
    repeat_penalty: float = 1.0,
    context_size: int = 1024,
    seed: int = -1,
    enable_thinking: bool = False,
    use_model_defaults: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
):
    base           = _normalize_base(base_url)
    resolved_model = model or DEFAULT_MODEL
    if not resolved_model:
        return None, None, "no_model"

    if VERBOSE_LOGGING:
        print(f"[Karga LLM] POST → {base} | model: {resolved_model} | api_type: {API_TYPE}")
        print(f"[Karga LLM] Messages: {messages}")

    if API_TYPE == "ollama":
        return _generate_ollama_native(
            base, resolved_model, messages, temperature, top_k, top_p,
            min_p, repeat_penalty, context_size, seed, enable_thinking,
            use_model_defaults, timeout
        )
    else:
        return _generate_openai_compat(
            base, resolved_model, messages, temperature, top_k, top_p,
            min_p, repeat_penalty, context_size, seed, enable_thinking,
            use_model_defaults, timeout
        )


def _generate_openai_compat(base, model, messages, temperature, top_k, top_p,
                             min_p, repeat_penalty, context_size, seed,
                             enable_thinking, use_model_defaults, timeout):
    url     = f"{base}/v1/chat/completions"
    payload = {"model": model, "messages": messages, "stream": False}

    if seed is not None and seed >= 0:
        payload["seed"] = seed
    if enable_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": True}
    if OLLAMA_KEEP_ALIVE:
        payload["keep_alive"] = OLLAMA_KEEP_ALIVE
    if not use_model_defaults:
        payload["temperature"]    = temperature
        payload["top_k"]          = top_k
        payload["top_p"]          = top_p
        payload["min_p"]          = min_p
        payload["repeat_penalty"] = repeat_penalty
        payload["max_tokens"]     = context_size

    if FORCE_JSON_OUTPUT:
        payload["response_format"] = {"type": "json_object"}

    try:
        resp = _request_with_retry("POST", url, json=payload, timeout=timeout)
        if resp.status_code != 200:
            return None, None, f"http_error:{resp.status_code}"
        result   = resp.json()
        message  = result["choices"][0]["message"]
        content  = message.get("content", "").strip()
        thinking = _extract_thinking(content, message, enable_thinking)
        if thinking:
            content = _strip_think_tags(content)
        if VERBOSE_LOGGING:
            print(f"[Karga LLM] Output: {content}")
        return content, thinking, None
    except requests.exceptions.ConnectionError:
        return None, None, "connection_error"
    except requests.exceptions.Timeout:
        return None, None, "timeout"
    except (KeyError, IndexError):
        return None, None, "invalid_response"
    except Exception as e:
        return None, None, f"error:{e}"


def _generate_ollama_native(base, model, messages, temperature, top_k, top_p,
                             min_p, repeat_penalty, context_size, seed,
                             enable_thinking, use_model_defaults, timeout):
    url     = f"{base}/api/chat"
    payload = {"model": model, "messages": messages, "stream": False, "keep_alive": OLLAMA_KEEP_ALIVE}

    if enable_thinking:
        payload["think"] = True
    if not use_model_defaults:
        payload["options"] = {
            "temperature":    temperature,
            "top_k":          top_k,
            "top_p":          top_p,
            "min_p":          min_p,
            "repeat_penalty": repeat_penalty,
            "num_ctx":        context_size,
            "seed":           seed if seed >= 0 else -1,
        }
    if FORCE_JSON_OUTPUT:
        payload["format"] = "json"

    try:
        resp = _request_with_retry("POST", url, json=payload, timeout=timeout)
        if resp.status_code != 200:
            return None, None, f"http_error:{resp.status_code}"
        result   = resp.json()
        message  = result.get("message", {})
        content  = message.get("content", "").strip()
        thinking = message.get("thinking", "").strip()
        if VERBOSE_LOGGING:
            print(f"[Karga LLM] Output: {content}")
        return content, thinking, None
    except requests.exceptions.ConnectionError:
        return None, None, "connection_error"
    except requests.exceptions.Timeout:
        return None, None, "timeout"
    except (KeyError, IndexError):
        return None, None, "invalid_response"
    except Exception as e:
        return None, None, f"error:{e}"


def unload_model(base_url: str, model: str):
    base = _normalize_base(base_url)
    if API_TYPE == "ollama":
        url     = f"{base}/api/chat"
        payload = {"model": model, "keep_alive": 0, "messages": []}
    else:
        url     = f"{base}/api/generate"
        payload = {"model": model, "keep_alive": 0}
    try:
        resp = _request_with_retry("POST", url, json=payload, timeout=15)
        if resp.status_code == 200:
            return True, f"Model '{model}' unloaded from VRAM."
        return False, f"HTTP {resp.status_code} while unloading."
    except Exception as e:
        return False, f"Unload failed: {e}"
