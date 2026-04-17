import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "KargaLLM",

  async setup() {
    app.ui.settings.addSetting({
      id: "KargaLLM.connection.base_url",
      name: "Base URL",
      category: ["Karga LLM", "Connection", "base_url"],
      type: "text",
      defaultValue: "http://127.0.0.1:1234",
      tooltip: "LM Studio default: http://127.0.0.1:1234 — Ollama default: http://127.0.0.1:11434",
    });
    app.ui.settings.addSetting({
      id: "KargaLLM.connection.timeout",
      name: "Request timeout (seconds)",
      category: ["Karga LLM", "Connection", "timeout"],
      type: "number",
      defaultValue: 120,
      attrs: { min: 10, max: 600, step: 10 },
    });
    app.ui.settings.addSetting({
      id: "KargaLLM.model.keep_alive",
      name: "Keep alive (Ollama only)",
      category: ["Karga LLM", "Model", "keep_alive"],
      type: "text",
      defaultValue: "5m",
      tooltip: "How long Ollama keeps the model in VRAM. e.g. 5m, 1h, 0 to unload immediately.",
    });
    app.ui.settings.addSetting({
      id: "KargaLLM.debug.log_requests",
      name: "Log requests to browser console",
      category: ["Karga LLM", "Debug", "log_requests"],
      type: "boolean",
      defaultValue: false,
    });

    console.log("[KargaLLM] loaded");
  }
});
