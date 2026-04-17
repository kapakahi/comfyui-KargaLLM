"""
KargaLLM — Karga LLM Text Generator Options
=============================================
Packs all LLM sampling + behaviour settings into a single LLM_OPTIONS wire.
Connecting this to Karga LLM Text Generator is optional — defaults are used if not connected.
"""


class KargaLLMOptions:

    CATEGORY = "KargaLLM"
    RETURN_TYPES = ("LLM_OPTIONS", "STRING")
    RETURN_NAMES = ("options",     "thoughts")
    FUNCTION = "pack"
    OUTPUT_NODE = False
    DESCRIPTION = (
        "Bundles all LLM sampling and behaviour settings into a single wire. "
        "Optional — defaults are used if not connected to Karga LLM Text Generator. "
        "thoughts output carries the chain-of-thought trace when enable_thinking is ON."
    )

    # Store thoughts from last generation so we can output them
    _last_thoughts: str = ""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "system_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "placeholder": "Leave empty to use mode preset only...",
                        "tooltip": "Custom instruction for the LLM. append: adds after mode preset. replace: replaces mode preset entirely.",
                        "dynamicPrompts": False,
                        "rows": 5,
                    }
                ),
                "system_prompt_mode": (
                    ["append", "replace"],
                    {
                        "default": "append",
                        "tooltip": "append: mode preset + your text. replace: your text only (empty = no system prompt at all).",
                    }
                ),
                "enable_thinking": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "Enables chain-of-thought reasoning for compatible models. Outputs reasoning trace to the thoughts output.",
                    }
                ),
                "temperature": (
                    "FLOAT",
                    {
                        "default": 0.8, "min": 0.0, "max": 2.0, "step": 0.05,
                        "tooltip": "Controls randomness. Lower = more deterministic, higher = more creative.",
                    }
                ),
                "top_k": (
                    "INT",
                    {
                        "default": 40, "min": 0, "max": 200, "step": 1,
                        "tooltip": "Limits token selection to the top K most likely tokens. 0 = disabled.",
                    }
                ),
                "top_p": (
                    "FLOAT",
                    {
                        "default": 0.95, "min": 0.0, "max": 1.0, "step": 0.01,
                        "tooltip": "Nucleus sampling — only considers tokens up to this cumulative probability.",
                    }
                ),
                "min_p": (
                    "FLOAT",
                    {
                        "default": 0.05, "min": 0.0, "max": 1.0, "step": 0.01,
                        "tooltip": "Filters tokens below this probability relative to the top token.",
                    }
                ),
                "repeat_penalty": (
                    "FLOAT",
                    {
                        "default": 1.0, "min": 0.0, "max": 2.0, "step": 0.05,
                        "tooltip": "Penalises repeating tokens. 1.0 = no penalty. Increase if output is repetitive.",
                    }
                ),
                "use_model_defaults": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "When enabled, ignores all sampling parameters and uses the model's built-in defaults.",
                    }
                ),
                "timeout": (
                    "INT",
                    {
                        "default": 120, "min": 10, "max": 600, "step": 10,
                        "tooltip": "Seconds to wait for LLM response before giving up. Overrides the global DEFAULT_TIMEOUT in llm_api.py.",
                    }
                ),
                "timeout_skip": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "When enabled, if the LLM times out the node returns the raw user prompt instead of an empty string.",
                    }
                ),
                "verbose": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "Prints system prompt, user prompt, and full output to the ComfyUI console. Also enhances the status output string.",
                    }
                ),
                "stop_server_after": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "Ollama only — unloads the model from VRAM after generation.",
                    }
                ),
            }
        }

    def pack(self, system_prompt, system_prompt_mode, enable_thinking,
             temperature, top_k, top_p, min_p, repeat_penalty,
             use_model_defaults, timeout, timeout_skip, verbose, stop_server_after):

        options = {
            "system_prompt":       system_prompt,
            "system_prompt_mode":  system_prompt_mode,
            "enable_thinking":     enable_thinking,
            "temperature":         temperature,
            "top_k":               top_k,
            "top_p":               top_p,
            "min_p":               min_p,
            "repeat_penalty":      repeat_penalty,
            "use_model_defaults":  use_model_defaults,
            "timeout":             timeout,
            "timeout_skip":        timeout_skip,
            "verbose":             verbose,
            "stop_server_after":   stop_server_after,
        }

        # thoughts is populated by KargaLLMTextGen after generation
        # we pass back whatever was stored from the last run
        return (options, KargaLLMOptions._last_thoughts)

    @classmethod
    def set_thoughts(cls, thoughts: str):
        """Called by KargaLLMTextGen to store thoughts for output."""
        cls._last_thoughts = thoughts or ""
