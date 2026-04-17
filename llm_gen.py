"""
KargaLLM — Karga LLM Text Generator
======================================
LLM-powered text/prompt generator. Fully standalone, zero external dependencies.
Modes defined in modes.py. Options node is optional.
"""
from __future__ import annotations
import time
from .llm_api import (
    discover_models, generate_chat, unload_model,
    DEFAULT_BASE_URL, DEFAULT_TIMEOUT, CONNECT_ON_STARTUP
)
from .modes import get_mode_names, get_mode
from .llm_options import KargaLLMOptions


def _get_setting(key: str, default):
    try:
        from server import PromptServer
        um = getattr(PromptServer.instance, "user_manager", None)
        if um and hasattr(um, "settings"):
            val = um.settings.get(key)
            if val is not None:
                return val
    except Exception:
        pass
    return default


def _base_url() -> str:
    return _get_setting("KargaLLM.connection.base_url", DEFAULT_BASE_URL)


def _fetch_models() -> list[str]:
    models, msg = discover_models(_base_url())
    if not models:
        print(f"[Karga LLM] Model discovery: {msg}")
        return ["(run node to load models)"]
    return models


def _build_status(verbose: bool, icon: str, parts: list[str]) -> str:
    if verbose:
        return f"{icon} " + " · ".join(parts)
    return f"{icon} " + " · ".join(parts[:2])


class KargaLLMTextGen:

    CATEGORY = "KargaLLM"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("generated_text", "status")
    FUNCTION = "generate"
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Generates or enhances text using a local LLM (LM Studio or Ollama). "
        "Connect Karga LLM Text Generator Options for full control, or run standalone with defaults. "
        "enable_llm is a built-in SPST switch — toggle on node or wire a BOOLEAN to control externally. "
        "thoughts output is on the Options node when enable_thinking is ON."
    )

    @classmethod
    def INPUT_TYPES(cls):
        models     = _fetch_models() if CONNECT_ON_STARTUP else ["(run node to load models)"]
        mode_names = get_mode_names()
        return {
            "required": {
                "LLM_Prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "placeholder": "Enter prompt...",
                        "tooltip": "The user prompt sent to the LLM.",
                        "dynamicPrompts": False,
                        "rows": 5,
                    }
                ),
                "LLM_Model": (
                    models,
                    {
                        "tooltip": (
                            "Model fetched from your LLM server. "
                            "Set CONNECT_ON_STARTUP = True in llm_api.py to populate on startup, "
                            "or run the node once to load models."
                        ),
                    }
                ),
                "mode": (
                    mode_names,
                    {
                        "default": mode_names[0],
                        "tooltip": "Sets the task and system prompt preset. Add new modes in modes.py.",
                    }
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0, "min": 0, "max": 0xFFFFFFFF,
                        "control_after_generate": True,
                        "tooltip": "Seed for reproducible generation.",
                    }
                ),
                "context_size": (
                    "INT",
                    {
                        "default": 512, "min": 64, "max": 131072, "step": 64,
                        "tooltip": "Maximum tokens the model can process (prompt + output combined).",
                    }
                ),
                "enable_llm": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "SPST switch — OFF returns empty string immediately with no API call. Wire a BOOLEAN for external control.",
                    }
                ),
            },
            "optional": {
                "options": (
                    "LLM_OPTIONS",
                    {
                        "tooltip": "Connect Karga LLM Text Generator Options to customise sampling and behaviour. Defaults used if not connected.",
                    }
                ),
                "Image_1": (
                    "IMAGE",
                    {
                        "tooltip": "Primary image for vision models. Ignored automatically when mode does not require an image.",
                    }
                ),
                "Image_2": (
                    "IMAGE",
                    {
                        "tooltip": "Secondary image for vision models. Ignored automatically when mode does not require an image.",
                    }
                ),
            }
        }

    def generate(self, LLM_Prompt, LLM_Model, mode, seed, context_size,
                 enable_llm, options=None, Image_1=None, Image_2=None):

        # --- SPST open circuit ---
        if not enable_llm:
            status = _build_status(False, "—", ["Disabled", "enable_llm = False"])
            KargaLLMOptions.set_thoughts("")
            return ("", status)

        # --- Unpack options ---
        options        = options or {}
        custom_sys     = options.get("system_prompt", "").strip()
        sp_mode        = options.get("system_prompt_mode", "append")
        enable_thinking= options.get("enable_thinking", False)
        temperature    = options.get("temperature", 0.8)
        top_k          = options.get("top_k", 40)
        top_p          = options.get("top_p", 0.95)
        min_p          = options.get("min_p", 0.05)
        repeat_penalty = options.get("repeat_penalty", 1.0)
        use_defaults   = options.get("use_model_defaults", False)
        timeout        = options.get("timeout", DEFAULT_TIMEOUT)
        timeout_skip   = options.get("timeout_skip", False)
        verbose        = options.get("verbose", False)
        stop_after     = options.get("stop_server_after", False)

        # --- Resolve mode ---
        mode_config    = get_mode(mode)
        mode_preset    = mode_config["system_prompt"]
        requires_image = mode_config["requires_image"]

        # --- Image SPST — gated by requires_image flag ---
        if requires_image:
            images = [img for img in [Image_1, Image_2] if img is not None]
            if not images:
                print(f"[Karga LLM] Warning: mode '{mode}' works best with an image connected.")
        else:
            images = []
            if Image_1 is not None or Image_2 is not None:
                print(f"[Karga LLM] Mode '{mode}' does not use images — inputs ignored.")

        # --- Resolve system prompt ---
        if sp_mode == "replace":
            system_prompt = custom_sys
        elif custom_sys:
            system_prompt = mode_preset + "\n\n" + custom_sys
        else:
            system_prompt = mode_preset

        # --- Build user content ---
        user_content = []
        for img_tensor in images:
            b64 = self._tensor_to_b64(img_tensor)
            if b64:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"}
                })

        prompt_text = LLM_Prompt.strip()
        user_content.append({"type": "text", "text": prompt_text})

        if len(user_content) == 1:
            user_message = {"role": "user", "content": prompt_text}
        else:
            user_message = {"role": "user", "content": user_content}

        messages = [
            {"role": "system", "content": system_prompt},
            user_message,
        ]

        # --- Verbose console logging ---
        if verbose:
            print(f"[Karga LLM] {'=' * 50}")
            print(f"[Karga LLM] Model:        {LLM_Model}")
            print(f"[Karga LLM] Mode:         {mode}")
            print(f"[Karga LLM] SP mode:      {sp_mode}")
            print(f"[Karga LLM] Seed:         {seed}")
            print(f"[Karga LLM] Context:      {context_size}")
            print(f"[Karga LLM] Timeout:      {timeout}s")
            print(f"[Karga LLM] Images sent:  {len(images)}")
            print(f"[Karga LLM] Thinking:     {enable_thinking}")
            print(f"[Karga LLM] --- System Prompt ---")
            print(system_prompt)
            print(f"[Karga LLM] --- User Prompt ---")
            print(prompt_text)

        # --- Generate ---
        t_start = time.time()

        output, thinking, error = generate_chat(
            base_url           = _base_url(),
            model              = LLM_Model,
            messages           = messages,
            temperature        = temperature,
            top_k              = top_k,
            top_p              = top_p,
            min_p              = min_p,
            repeat_penalty     = repeat_penalty,
            context_size       = context_size,
            seed               = seed,
            enable_thinking    = enable_thinking,
            use_model_defaults = use_defaults,
            timeout            = timeout,
        )

        elapsed = time.time() - t_start

        # Store thoughts in Options node for output
        KargaLLMOptions.set_thoughts(thinking or "")

        # --- Handle errors ---
        if error:
            KargaLLMOptions.set_thoughts("")
            if error == "timeout":
                if timeout_skip:
                    print(f"[Karga LLM] Timeout after {timeout}s — returning user prompt.")
                    status = _build_status(verbose, "⚠", [
                        "Timeout · returning user prompt",
                        mode, LLM_Model,
                        f"seed:{seed}", f"{elapsed:.1f}s", f"timeout:{timeout}s",
                    ])
                    return (LLM_Prompt, status)
                else:
                    status = _build_status(verbose, "⚠", [
                        "Timeout", mode, LLM_Model,
                        f"seed:{seed}", f"{elapsed:.1f}s", f"timeout:{timeout}s",
                    ])
                    print(f"[Karga LLM] Timeout after {timeout}s.")
                    return ("", status)

            elif error == "connection_error":
                status = _build_status(verbose, "✗", [
                    "Failed · could not connect", mode, LLM_Model, _base_url(),
                ])
                print(f"[Karga LLM] Connection failed → {_base_url()}")
                return ("", status)

            elif error == "no_model":
                status = _build_status(verbose, "✗", [
                    "No model selected", mode,
                    "check LLM_Model or DEFAULT_MODEL in llm_api.py",
                ])
                print(f"[Karga LLM] No model selected.")
                return ("", status)

            elif error == "invalid_response":
                status = _build_status(verbose, "✗", [
                    "Failed · invalid response", mode, LLM_Model,
                ])
                print(f"[Karga LLM] Invalid response from server.")
                return ("", status)

            else:
                status = _build_status(verbose, "✗", [
                    f"Failed · {error}", mode, LLM_Model,
                ])
                print(f"[Karga LLM] Error: {error}")
                return ("", status)

        # --- Success ---
        if verbose:
            if thinking:
                print(f"[Karga LLM] --- Thoughts ---")
                print(thinking)
            print(f"[Karga LLM] --- Output ---")
            print(output)
            print(f"[Karga LLM] {'=' * 50}")

        # --- Unload model (Ollama only) ---
        if stop_after:
            ok, msg = unload_model(_base_url(), LLM_Model)
            print(f"[Karga LLM] Unload: {msg}")

        # --- Build success status ---
        parts = ["Done", mode, LLM_Model, f"seed:{seed}", f"{elapsed:.1f}s"]
        if images:
            parts.append(f"images:{len(images)}")
        if enable_thinking and thinking:
            parts.append("thinking:on")

        status = _build_status(verbose, "✓", parts)
        print(f"[Karga LLM] {status}")

        return (output or "", status)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _tensor_to_b64(self, tensor) -> str | None:
        """Convert ComfyUI IMAGE tensor to base64 PNG. No resizing."""
        try:
            import base64, io
            import numpy as np
            from PIL import Image

            img_np  = tensor[0].cpu().numpy()
            img_np  = (img_np * 255).clip(0, 255).astype(np.uint8)
            pil_img = Image.fromarray(img_np)
            buf     = io.BytesIO()
            pil_img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"[Karga LLM] Image encoding failed: {e}")
            return None
