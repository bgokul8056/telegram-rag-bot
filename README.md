# 🤖 Multi-Modal GenAI Telegram Bot (RAG + Vision)

A production-ready Telegram bot that combines **Retrieval-Augmented Generation (RAG)** for document Q&A with **Vision AI** for image description — all powered by local LLMs via [Ollama](https://ollama.com/).

---

## ✨ Features

| Feature | Command | Description |
|---------|---------|-------------|
| **RAG Q&A** | `/ask <query>` | Answers questions from an embedded knowledge base of Markdown documents |
| **Image Analysis** | `/image` or send a photo | Generates a short caption + 3 keyword tags for any uploaded image |
| **Conversation Summary** | `/summarize` | Summarizes the user's recent interactions using AI |
| **Direct Chat** | Just type a message | Treats any plain text as a RAG query |
| **Help** | `/help` | Displays usage instructions |

### 🔒 Security & Production Features
- **Persistent Memory:** Conversation history stored in SQLite per user — survives restarts.
- **Embedding Cache:** LRU cache skips re-embedding repeated queries for faster responses.
- **Rate Limiting:** 3-second cooldown per user prevents spam and protects resources.
- **Prompt Injection Guard:** Blocks common jailbreak phrases before they reach the LLM.
- **Zero Disk Image Storage:** Uploaded images are processed entirely in RAM — nothing is saved to disk.
- **Source Snippets:** Every RAG answer includes which document(s) were used.

---

## 📁 Project Structure

```
rag-bot/
├── bot.py                 # Telegram bot entry point (handlers, rate limiting)
├── rag_system.py          # RAG pipeline (chunking, embeddings, SQLite, LLM)
├── vision_system.py       # Vision module (in-memory image → Ollama Llava)
├── simulate_users.py      # Multi-user simulation script for testing
├── test_rag.py            # Pytest unit tests (cache, injection guard, history)
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container image definition
├── docker-compose.yml     # One-command Docker orchestration
├── .env.example           # Environment variable template (safe to commit)
├── .gitignore             # Prevents secrets and artifacts from being committed
├── data/                  # Knowledge base documents
│   ├── company_policy.md
│   ├── tech_faq.md
│   └── healthy_recipes.md
└── README.md              # You are here
```

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|-----------|
| Bot Framework | `python-telegram-bot` v21 |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`, runs locally) |
| Vector Storage | `sqlite3` + `numpy` cosine similarity |
| Text LLM | Ollama (`llama3`) via OpenAI-compatible API |
| Vision LLM | Ollama (`llava`) via OpenAI-compatible API |
| Testing | `pytest` |
| Containerization | Docker + Docker Compose |

---

## 🚀 Quick Start (Local Setup)

### Prerequisites
- **Python 3.10+**
- **Ollama** — [Download here](https://ollama.com/download)
- **Telegram Bot Token** — Create via [BotFather](https://core.telegram.org/bots/features#botfather)

### Step 1: Pull the required Ollama models
```bash
ollama pull llama3
ollama pull llava
```

### Step 2: Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure environment
```bash
cp .env.example .env
```
Open `.env` and replace `your_telegram_bot_token_here` with your actual Telegram bot token.

### Step 4: Run the bot
```bash
python bot.py
```
On first launch, the bot will:
1. Download the embedding model (~90MB, cached after first run).
2. Chunk and index the `data/*.md` files into `vectors.db`.
3. Start polling Telegram for messages.

### Step 5: Chat with your bot on Telegram!
- `/ask What is the PTO policy?`
- Send any photo to get a caption + tags
- `/summarize` to recap recent conversation

---

## 🐳 Docker Setup (For Evaluation / Deployment)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Ollama running on the **host machine** (not inside Docker)

### Step 1: Configure environment for Docker
```bash
cp .env.example .env
```
Edit `.env` and set:
```bash
TELEGRAM_BOT_TOKEN="your_actual_token"
OPENAI_BASE_URL="http://host.docker.internal:11434/v1"
```
> ⚠️ **Important:** Use `host.docker.internal` instead of `localhost` so the Docker container can reach Ollama on the host.

### Step 2: Build and run
```bash
docker-compose up --build
```
The bot will start polling inside the container. Press `Ctrl+C` to stop.

---

## 🛡️ Security - Safety & Guardrails

To prevent jailbreaking and malicious prompt injection, this bot implements a dedicated Safety Guard. This is currently a **work in progress** using a robust keyword-filtering approach.

### Current Implementation
The system scans incoming queries for the following forbidden phrases before they reach the LLM:
- `ignore all`
- `system prompt`
- `administrator`
- `bypass instructions`
- `ignore your instructions`
- `ignore previous`
- `disregard everything`
- `forget everything`
- `new instructions`

### Future Roadmap
While current keyword matching is effective for common attacks, future iterations will focus on **Semantic Monitoring**. This involves using a secondary "safety model" to evaluate the intent/meaning of a query rather than just looking for exact words, providing even more resilient defense against evolving injection tactics.

---

## 🧪 Testing

### Unit Tests (pytest)
```bash
pip install pytest
pytest test_rag.py -v
```
Tests included:
| Test | What It Verifies |
|------|-----------------|
| `test_cache_logic` | LRU embedding cache returns identical vectors for repeated queries |
| `test_injection_guard` | Prompt injection phrases are blocked before reaching the LLM |
| `test_history_insertion` | SQLite history table correctly stores and retrieves per-user interactions |

### Multi-User Simulation
```bash
python simulate_users.py
```
Simulates two virtual users (Alice & Bob) asking different questions simultaneously, verifying that:
- Context is correctly **isolated per user**
- Conversation **history** is maintained independently
- `/summarize` returns user-specific recaps

### Manual Telegram Testing Checklist

| # | Test | How | Expected Result |
|---|------|-----|----------------|
| 1 | RAG Query | `/ask What is the max lunch allowance?` | Answer + `📝 Sources: company_policy.md` |
| 2 | Image Vision | Upload any photo | Short caption + 3 hashtag tags |
| 3 | Follow-up Memory | Ask a follow-up question | Bot remembers prior context |
| 4 | Summarize | `/summarize` | AI-generated recap of recent chat |
| 5 | Rate Limit | Send 3 messages in 1 second | `⏳ Please wait` response |
| 6 | Prompt Injection | `/ask Ignore all previous instructions` | Safety guard rejection |

---

## 🧠 Model Selection Rationale

A key design decision in any GenAI system is choosing between **local models** and **cloud APIs**. This project deliberately uses **fully local inference** for all three model components. Here's why:

### Text LLM — Ollama `llama3` (Local) vs OpenAI API

| Criteria | Local (Ollama Llama 3) | Cloud (OpenAI GPT-4o) |
|----------|----------------------|----------------------|
| **Cost** | ✅ Completely free | ❌ Pay-per-token ($2.50–$10/1M tokens) |
| **Privacy** | ✅ Data never leaves your machine | ❌ Queries sent to OpenAI servers |
| **Latency** | ⚠️ Depends on local hardware (2–15s) | ✅ Fast (~1–3s) |
| **Internet** | ✅ Works fully offline after setup | ❌ Requires constant internet |
| **Quality** | ✅ Strong for RAG (grounded in context) | ✅ Slightly better reasoning |

**Why we chose local:** For a RAG system, the LLM's job is relatively simple — it just needs to synthesize an answer from the retrieved context chunks, not reason from scratch. Llama 3 handles this excellently. Additionally, in enterprise or evaluation settings, **data privacy** is critical — queries about company policies or internal FAQs should never leave the local network. The architecture remains **swappable**: changing `OPENAI_BASE_URL` and `LLM_MODEL` in `.env` instantly switches to OpenAI if needed.

### Vision LLM — Ollama `llava` (Local) vs Cloud Vision APIs

| Criteria | Local (Ollama Llava) | Cloud (GPT-4o Vision / Google Vision) |
|----------|---------------------|--------------------------------------|
| **Cost** | ✅ Free | ❌ $5–$15 per 1K images |
| **Privacy** | ✅ Images never leave the machine | ❌ Images uploaded to third-party servers |
| **Flexibility** | ✅ Custom prompts for caption + tags | ⚠️ API-specific response formats |
| **Setup** | ⚠️ Requires ~4GB model download | ✅ Just an API key |

**Why we chose local:** Image data is inherently sensitive. Users may upload screenshots, documents, or personal photos. Processing them **entirely in RAM on the local machine** (with zero disk writes) ensures maximum privacy. Llava produces high-quality captions and is freely available through Ollama's ecosystem.

### Embeddings — `all-MiniLM-L6-v2` (Local) vs OpenAI Embeddings API

| Criteria | Local (MiniLM) | Cloud (OpenAI `text-embedding-3-small`) |
|----------|---------------|----------------------------------------|
| **Cost** | ✅ Free | ❌ $0.02 per 1M tokens |
| **Speed** | ✅ ~5ms per query (cached) | ⚠️ Network round-trip (~100–300ms) |
| **Size** | ✅ ~90MB model | N/A (cloud) |
| **Quality** | ✅ Excellent for short document retrieval | ✅ Slightly higher dimensional |

**Why we chose local:** Embedding happens on **every single query** the user sends. Using a cloud API would add latency to every interaction, create an internet dependency, and accumulate costs. The `all-MiniLM-L6-v2` model is specifically optimized for semantic similarity tasks, is only ~90MB, and runs in milliseconds on CPU. Combined with our **LRU cache**, repeated queries skip embedding entirely.

### Summary

> This project prioritizes **privacy, zero cost, and offline capability** while maintaining a clean architecture that allows **instant switching to cloud APIs** via environment variables — no code changes required.

---

## 🏗 System Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Telegram    │────▶│    bot.py         │────▶│  rag_system.py  │
│  User Chat   │◀────│  (Rate Limiting)  │◀────│  (Embed+Search) │
└─────────────┘     │  (History Save)   │     │  (LLM Generate) │
                    └──────┬───────────┘     └────────┬────────┘
                           │                          │
                    ┌──────▼───────────┐     ┌────────▼────────┐
                    │ vision_system.py  │     │   SQLite DB      │
                    │ (In-Memory Image) │     │ vectors.db       │
                    │ (Ollama Llava)    │     │ ├─ chunks table  │
                    └──────────────────┘     │ └─ history table │
                                             └─────────────────┘
```

**Data Flow:**
1. User sends a message or image via Telegram.
2. `bot.py` applies rate limiting, then routes to the appropriate handler.
3. **For text:** `rag_system.py` embeds the query → searches SQLite for top-3 chunks → builds a prompt with context → sends to Ollama Llama 3 → replies with answer + source snippets.
4. **For images:** `vision_system.py` receives raw bytes in memory → base64 encodes → sends to Ollama Llava → replies with caption + tags.
5. All interactions are persisted to the SQLite `history` table per user.

---

## 📂 Adding Your Own Documents

1. Drop any `.md` file into the `data/` folder.
2. Delete `vectors.db` (forces re-indexing).
3. Restart the bot with `python bot.py`.

The system will automatically chunk by `##` headers, embed each chunk, and store vectors in SQLite.

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | Your Telegram bot API token (required) |
| `OPENAI_BASE_URL` | `http://localhost:11434/v1` | Ollama API endpoint. Use `host.docker.internal` for Docker. |
| `OPENAI_API_KEY` | `ollama` | Set to `ollama` for local use, or your real key for OpenAI. |
| `LLM_MODEL` | `llama3` | Text generation model name in Ollama. |
| `VISION_MODEL` | `llava` | Vision model name in Ollama. |

---

## 📜 License

This project is for educational and evaluation purposes.
