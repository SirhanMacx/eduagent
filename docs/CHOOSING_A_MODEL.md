# Choosing a Model

Claw-ED is the tool — it needs an AI brain to do the thinking. Think of it like a car: Claw-ED is the car, and the AI is the engine. **You pick the engine and pay for it directly.** Nothing goes through our servers.

There are four options, each with different tradeoffs between cost, quality, and convenience.

---

## Option 1 — Anthropic Claude (best quality, pay per use)

Claude is widely considered the best AI for writing and nuanced instruction. Two models to choose from:

- **Claude Sonnet 4.6** — excellent quality, more affordable. Great for daily lesson planning.
- **Claude Opus 4.6** — the smartest available. Noticeably better output, noticeably more expensive.

**Setup:**
1. Go to [console.anthropic.com](https://console.anthropic.com) and create an account
2. Add a credit card (you only pay for what you use — no subscription)
3. Click **API Keys** in the left sidebar → **Create Key** → copy it
4. In Terminal: `export ANTHROPIC_API_KEY=sk-ant-your-key-here`

> Cost depends entirely on how much you use it. Light use (a few lessons a week): **$10–30/month**. Heavy daily use: **$100–200/month**. Opus 4.6 is roughly 5x more expensive than Sonnet — only worth it if output quality is your top priority.

---

## Option 2 — OpenAI GPT-5.4 (professional grade, pay per use)

The company behind ChatGPT. GPT-5.4 is highly capable and produces professional-quality output.

**Setup:**
1. Go to [platform.openai.com](https://platform.openai.com) and create an account
2. Add a credit card under **Billing**
3. Click **API Keys** → **Create new secret key** → copy it
4. In Terminal: `export OPENAI_API_KEY=sk-your-key-here`

> GPT-5.4 is powerful but the cost adds up fast. Light use: **$10–30/month**. Heavy daily use: **$100–200/month**. No monthly cap — you pay for every token.

---

## Option 3 — Ollama Cloud with MiniMax M2.7 (~$20/month flat rate)

Ollama is a platform that gives you access to powerful AI for a flat monthly fee — no surprise bills. MiniMax M2.7 is an excellent model for education: smart, fast, and great at learning your teaching voice.

**Setup:**
1. Go to [ollama.com](https://ollama.com) and create a free account
2. There is some free usage to try it before committing
3. Upgrade to the **$20/month** plan for unlimited use
4. Find your API key: log in → click your profile icon (top right) → **Settings** → **API Keys** → **Generate**
5. In Terminal: `export OLLAMA_API_KEY=your-key-here` then `clawed config set-model ollama`

> **Best value for most teachers.** Flat rate, no surprises, and MiniMax M2.7 is excellent at capturing your specific teaching style.

---

## Option 4 — Local model on your own computer (not recommended)

You can run a small AI model entirely on your computer — free, no internet needed. The catch: local models are significantly less intelligent than cloud options. They often struggle to capture your teaching voice or write naturally. Most teachers will be disappointed with the results.

If you want to try anyway, we recommend the **Qwen 3.5 series**:

| Your computer | Recommended model | Command to install |
|--------------|-------------------|--------------------|
| Basic laptop (8GB RAM) | Qwen 3.5 4B | `ollama pull qwen3.5:4b` |
| Modern Mac or PC (16GB RAM) | Qwen 3.5 9B | `ollama pull qwen3.5:9b` |
| High-end workstation (32GB+ RAM) | Qwen 3.5 32B | `ollama pull qwen3.5:32b` |

Then run: `clawed config set-model ollama`

> Start with Option 3 if cost is your concern — $20/month for cloud is far better than a free local model.

---

## Bottom line

Most teachers should start with **Option 3 (Ollama Cloud, $20/month)**. Flat rate, great quality, no surprises. If you want the best possible output regardless of cost, use **Option 1 with Claude Sonnet 4.6**.

---

Ready to get started? Head back to the [README quickstart](../README.md#-getting-started).
