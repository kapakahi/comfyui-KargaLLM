"""
KargaLLM
=========
Standalone ComfyUI node pack for LLM-powered text and prompt generation.
Supports LM Studio and Ollama via OpenAI-compatible endpoints.
Zero external node pack dependencies.
"""
from .llm_options import KargaLLMOptions
from .llm_gen     import KargaLLMTextGen

NODE_CLASS_MAPPINGS = {
    "KargaLLMOptions":  KargaLLMOptions,
    "KargaLLMTextGen":  KargaLLMTextGen,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "KargaLLMOptions":  "Karga LLM Text Generator Options",
    "KargaLLMTextGen":  "Karga LLM Text Generator",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
