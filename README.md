# comfyui-KargaLLM

A lightweight, standalone ComfyUI node for LLM-powered text and prompt generation.
Connects to any OpenAI-compatible local LLM server — LM Studio, Ollama, or any compat endpoint.

---



---

## Features

- **Karga LLM Text Generator** — generates or enhances text using a local LLM
- **Karga LLM Text Generator Options** — bundles all sampling settings into a single wire
- Built-in SPST bypass — toggle or wire a BOOLEAN to enable/disable generation
- Automatic image gate — vision inputs ignored when mode does not require them
- Timeout skip — falls back to raw user prompt on timeout, keeps pipeline flowing
- Status output — connect to a text preview node for live feedback
- Extensible modes — add your own in `modes.py`, no other files need to change
- Zero external node pack dependencies

---

## Installation

**Option A — Manual**
```
cd ComfyUI/custom_nodes
git clone https://github.com/kapakahi/comfyui-KargaLLM
```

**Option B — Drop in**
Download the zip and extract `comfyui-KargaLLM` into `ComfyUI/custom_nodes/`.

No pip installs required — only uses `requests` which ships with ComfyUI.

---

## Configuration

Open `llm_api.py` and edit the user config block at the top:

```python
# LM Studio default
DEFAULT_BASE_URL = "http://127.0.0.1:1234"

# Ollama default
DEFAULT_BASE_URL = "http://127.0.0.1:11434"

# API type
API_TYPE = "openai"   # LM Studio, Ollama compat, any OpenAI-compat server
API_TYPE = "ollama"   # Ollama native API only

# Connect on startup (False = safe default, models load on first run)
CONNECT_ON_STARTUP = False
```

---

## Nodes

### Karga LLM Text Generator

| Input | Type | Description |
|---|---|---|
| LLM_Prompt | STRING | User prompt sent to the LLM |
| LLM_Model | COMBO | Model fetched live from your server |
| mode | COMBO | Task preset — defined in modes.py |
| seed | INT | Generation seed |
| context_size | INT | Max tokens (prompt + output), default 512 |
| enable_llm | BOOLEAN | SPST switch — OFF skips generation entirely |
| options | LLM_OPTIONS | Connect Options node for full control (optional) |
| Image_1 | IMAGE | Primary image for vision modes (optional) |
| Image_2 | IMAGE | Secondary image for vision modes (optional) |

| Output | Type | Description |
|---|---|---|
| generated_text | STRING | LLM output |
| thoughts | STRING | Chain-of-thought trace (when enable_thinking is ON) |
| status | STRING | Human-readable feedback — connect to a text preview node |

---

### Karga LLM Text Generator Options

| Input | Default | Description |
|---|---|---|
| system_prompt | "" | Custom system prompt (empty = use mode preset) |
| system_prompt_mode | append | append: preset + your text / replace: your text only |
| enable_thinking | false | Chain-of-thought for compatible models |
| temperature | 0.8 | Sampling randomness |
| top_k | 40 | Top-K sampling |
| top_p | 0.95 | Nucleus sampling |
| min_p | 0.05 | Min-P sampling |
| repeat_penalty | 1.0 | Repetition penalty |
| use_model_defaults | false | Ignore sampling params, use model defaults |
| timeout | 120 | Seconds before giving up |
| timeout_skip | false | Return raw user prompt on timeout instead of empty string |
| verbose | false | Enhanced console + status output |
| stop_server_after | false | Ollama only — unload model from VRAM after generation |

---

## Adding Modes

Open `modes.py` and add a new entry to the `MODES` dict:

```python
"My Custom Mode": {
    "requires_image": False,
    "system_prompt": "You are a...",
},
```

Restart ComfyUI — your mode appears in the dropdown automatically.

---

## Compatibility

| Server | Models | Generation | Unload VRAM |
|---|---|---|---|
| LM Studio | ✅ | ✅ | ❌ |
| Ollama | ✅ | ✅ | ✅ |
| Any OpenAI-compat | ✅ | ✅ | ❌ |

---

## License

MIT
