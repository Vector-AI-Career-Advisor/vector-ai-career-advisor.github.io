#!/usr/bin/env bash
# Install Ollama (if absent) and pull the extraction model.
# Model weights land in ~/.ollama/models/ — never inside this repo.
set -euo pipefail

if ! command -v ollama &>/dev/null; then
    echo "Ollama not found — installing..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama already installed: $(ollama --version)"
fi

MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"
echo "Pulling model: $MODEL  (stored in ~/.ollama/models/)"
ollama pull "$MODEL"

echo "Done. Start the server with: ollama serve"
