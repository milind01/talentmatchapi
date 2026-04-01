# 🚀 Local Ollama Setup Guide

Replace OpenAI with **free local models** using Ollama and sentence-transformers.

## Quick Start (5 minutes)

### 1. Install Ollama

**macOS:**
```bash
# Download from https://ollama.ai or use Homebrew
brew install ollama
```

**Linux:**
```bash
curl https://ollama.ai/install.sh | sh
```

**Windows:**
- Download from https://ollama.ai/download

### 2. Start Ollama Server

```bash
ollama serve
```

This runs on `http://localhost:11434`

### 3. Pull a Model

In a new terminal:

```bash
# Fast & lightweight (7B params, ~4GB)
ollama pull mistral

# Alternative options:
ollama pull neural-chat      # 7B, optimized for chat
ollama pull dolphin-mixtral  # 7B MoE, high quality
ollama pull llama2           # 7B, good for instructions
ollama pull phi              # Tiny (2.7B), fast
```

### 4. Update Environment

```bash
# Copy .env.example to .env
cp .env.example .env

# Update these settings:
# OLLAMA_BASE_URL=http://localhost:11434
# LLM_MODEL=mistral
# EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### 5. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 6. Run DocAi

```bash
python -m uvicorn src.api.main:app --reload --port 8000
```

Visit: **http://localhost:8000/docs**

---

## Architecture

```
Your App
   ↓
Ollama (localhost:11434)
   ├─ LLM: Mistral, Llama2, Neural-Chat, etc.
   └─ (No OpenAI needed!)

Embeddings
   └─ sentence-transformers (runs locally, no API calls)

Vector DB
   └─ Pinecone/Weaviate/Qdrant (or local if you prefer)

Database
   └─ PostgreSQL (same as before)
```

---

## Model Recommendations

| Use Case | Model | Size | Speed | Quality |
|----------|-------|------|-------|---------|
| **Best All-Around** | mistral | 7B | Fast | ⭐⭐⭐⭐ |
| **Chat Optimized** | neural-chat | 7B | Fast | ⭐⭐⭐⭐ |
| **High Quality** | dolphin-mixtral | 7B MoE | Medium | ⭐⭐⭐⭐⭐ |
| **Documents** | llama2 | 7B | Fast | ⭐⭐⭐⭐ |
| **Ultra Fast** | phi | 2.7B | Very Fast | ⭐⭐⭐ |
| **Uncensored** | openhermes-2.5 | 7B | Fast | ⭐⭐⭐⭐ |

**Start with: `mistral`** (best balance)

---

## Docker Deployment

### Production with Docker

```yaml
# docker-compose.yml includes:
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434

  app:
    build: .
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - LLM_MODEL=mistral
```

Run:
```bash
docker-compose up -d
```

---

## Troubleshooting

### Ollama server not responding
```bash
# Check if running
curl http://localhost:11434/api/tags

# Restart
pkill ollama
ollama serve
```

### Model too slow
- Switch to smaller model: `phi` or `neural-chat`
- Increase RAM allocation
- Use GPU (if available)

### Memory issues
```bash
# Set memory limit for Ollama
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_NUM_THREAD=4
ollama serve
```

### GPU Acceleration (CUDA)
```bash
# For NVIDIA GPUs
# Download CUDA runtime and ensure drivers installed
ollama pull mistral  # Auto-downloads GPU support if available
```

---

## Features Now Available

✅ **LLM**: Ollama (local, free)
✅ **Embeddings**: sentence-transformers (local, free)
✅ **Fine-tuning**: LoRA or continued pre-training (planned)
✅ **No API costs**: 100% free
✅ **Offline mode**: Works without internet
✅ **Privacy**: All data stays on your machine
✅ **GPU support**: NVIDIA, AMD, Apple Silicon

---

## API Differences from OpenAI

### Before (OpenAI)
```python
from openai import OpenAI
client = OpenAI(api_key="sk-...")
response = client.chat.completions.create(...)
```

### Now (Ollama)
```python
from src.ai.llm_service import LLMService
llm = LLMService(base_url="http://localhost:11434", model="mistral")
response = await llm.generate(prompt="...")
```

---

## Monitoring Ollama

```bash
# Check running models
curl http://localhost:11434/api/tags

# Model info
ollama show mistral

# Benchmark
time ollama run mistral "What is 2+2?"
```

---

## Next Steps

1. ✅ Start `ollama serve`
2. ✅ Pull a model: `ollama pull mistral`
3. ✅ Run DocAi: `python -m uvicorn src.api.main:app --reload`
4. ✅ Test API: Visit http://localhost:8000/docs
5. ✅ Deploy to cloud with Docker

---

## Cost Comparison

| Setup | Monthly Cost | Privacy | Control |
|-------|--------------|---------|---------|
| **OpenAI** | $20-500+ | ❌ Cloud | ❌ Limited |
| **Ollama** | $0 | ✅ Local | ✅ Full |
| **Hybrid** | $0-50 | ✅ Mixed | ✅ High |

**You're saving thousands with Ollama!** 🎉

---

## Resources

- [Ollama Docs](https://ollama.ai)
- [Sentence-Transformers](https://www.sbert.net/)
- [Mistral Model](https://mistral.ai/)
- [LLM Comparison](https://huggingface.co/spaces/lmsys/chatbot-arena-leaderboard)
