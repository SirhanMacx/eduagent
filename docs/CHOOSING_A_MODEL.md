# Choosing a Model

Ed is the tool -- he needs an AI brain to do the thinking. Think of it like a car: Ed is the car, and the AI is the engine. **You pick the engine and pay for it directly.** Nothing goes through our servers.

There are four options, each with different tradeoffs between quality, speed, and convenience.

---

## Option 1 -- Anthropic Claude (best quality, pay per use)

Claude is widely considered the best AI for writing and nuanced instruction. Two models to choose from:

- **Claude Sonnet 4.6** -- excellent quality, more affordable. Great for daily lesson planning.
- **Claude Opus 4.6** -- the smartest available. Noticeably better output for complex units and differentiation.

**Setup:**
1. Go to [console.anthropic.com](https://console.anthropic.com) and create an account
2. Add a credit card (pay-per-use billing)
3. Click **API Keys** in the left sidebar, then **Create Key**, and copy it
4. In Terminal: `export ANTHROPIC_API_KEY=sk-ant-your-key-here`

---

## Option 2 -- OpenAI GPT-5.4 (professional grade, pay per use)

The company behind ChatGPT. GPT-5.4 is highly capable and produces professional-quality output.

**Setup:**
1. Go to [platform.openai.com](https://platform.openai.com) and create an account
2. Add a credit card under **Billing**
3. Click **API Keys**, then **Create new secret key**, and copy it
4. In Terminal: `export OPENAI_API_KEY=sk-your-key-here`

---

## Option 3 -- Google Gemini (fast and capable, pay per use)

Google's Gemini models are fast and strong on structured content. Two models to choose from:

- **Gemini 2.5 Flash** -- fast and affordable. Good for daily use when speed matters.
- **Gemini 2.5 Pro** -- stronger reasoning. Better for complex unit plans and differentiated materials.

**Setup:**
1. Go to [aistudio.google.com](https://aistudio.google.com) and sign in with your Google account
2. Click **Get API Key**, then **Create API Key**, and copy it
3. In Terminal: `export GOOGLE_API_KEY=your-key-here`
4. Then: `clawed config set-model google`

---

## Option 4 -- Ollama Cloud with MiniMax M2.7 (flat rate)

Ollama is a platform that gives you access to powerful AI for a flat monthly fee -- no surprise bills. MiniMax M2.7 is an excellent model for education: smart, fast, and great at learning your teaching voice.

**Setup:**
1. Go to [ollama.com](https://ollama.com) and create a free account
2. There is some free usage to try it before committing
3. Upgrade to a paid plan for unlimited use
4. Find your API key: log in, click your profile icon (top right), then **Settings**, then **API Keys**, then **Generate**
5. In Terminal: `export OLLAMA_API_KEY=your-key-here` then `clawed config set-model ollama`

**Best value for most teachers.** Flat rate, no surprises, and MiniMax M2.7 is excellent at capturing your specific teaching style.

---

## Option 5 -- Local model on your own computer (free, limited quality)

You can run a small AI model entirely on your computer -- free, no internet needed. The catch: local models are significantly less intelligent than cloud options. They often struggle to capture your teaching voice or write naturally. Most teachers will be disappointed with the results.

If you want to try anyway, Ed works well with the **Gemma 4** series:

| Your computer | Recommended model | Command to install |
|--------------|-------------------|--------------------|
| Basic laptop (8GB RAM) | Gemma 4 4B | `ollama pull gemma4:4b` |
| Modern Mac or PC (16GB RAM) | Gemma 4 12B | `ollama pull gemma4:12b` |
| High-end workstation (32GB+ RAM) | Gemma 4 27B | `ollama pull gemma4:27b` |

Then run: `clawed config set-model ollama`

> Start with Option 4 (Ollama Cloud) if cost is your concern -- a flat-rate cloud model is far better than a free local model.

---

## Bottom line

Most teachers should start with **Option 4 (Ollama Cloud)**. Flat rate, great quality, no surprises. If you want the best possible output regardless of cost, use **Option 1 with Claude Sonnet 4.6**. If Ed is struggling with a particular task, you can always switch models with `clawed config set-model`.

---

Ready to get started? Head back to the [README quickstart](../README.md#-getting-started).
