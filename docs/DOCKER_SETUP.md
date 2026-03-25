# Running Claw-ED with Docker

This guide gets Claw-ED running on your computer with zero Python knowledge. You'll need about 10 minutes.

## What you'll end up with

- A web dashboard at http://localhost:8000 where you can chat, generate lessons, and manage your materials
- Optionally, a Telegram bot you can message from your phone

## Step 1: Install Docker Desktop

Download and install Docker Desktop for your computer:

- **Mac:** https://www.docker.com/products/docker-desktop/ — click "Download for Mac", open the `.dmg`, drag to Applications
- **Windows:** https://www.docker.com/products/docker-desktop/ — click "Download for Windows", run the installer
- **Linux:** https://docs.docker.com/engine/install/

Open Docker Desktop after installing. You'll see a whale icon in your menu bar — that means it's running.

## Step 2: Get your API keys

You need two things:

### An LLM API key (pick one)

This is how Claw-ED talks to an AI model to generate your lessons.

| Option | Cost | How to get it |
|--------|------|---------------|
| **Ollama Cloud** — recommended | $20/month flat rate | Go to https://ollama.com, create account, grab API key from Settings |
| **Anthropic (Claude)** | ~$0.01-0.05 per lesson | Go to https://console.anthropic.com/, create account, go to API Keys, create a key starting with `sk-ant-` |
| **OpenAI (GPT-4o)** | ~$0.01-0.05 per lesson | Go to https://platform.openai.com/, create account, go to API Keys |

### A Telegram bot token (optional)

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Pick a name (e.g., "My Teaching Assistant")
4. Pick a username (e.g., "mrs_smith_teacher_bot")
5. BotFather gives you a token — copy it

## Step 3: Set up the files

Open your terminal (Mac: search "Terminal" in Spotlight, Windows: search "PowerShell").

Create a folder and download the config:

```bash
mkdir clawed && cd clawed
```

Create a file called `.env` in this folder. You can use any text editor. Put this in it:

```
# Paste your API key here (pick one):
ANTHROPIC_API_KEY=sk-ant-your-key-here
# OPENAI_API_KEY=sk-your-key-here
# OLLAMA_URL=http://host.docker.internal:11434

# Paste your Telegram bot token here (optional):
# TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
```

Replace the placeholder values with your real keys. Lines starting with `#` are ignored.

Now create a file called `docker-compose.yml` in the same folder with this content:

```yaml
services:
  web:
    image: ghcr.io/sirhanmacx/clawed:latest
    ports:
      - "8000:8000"
    env_file: .env
    environment:
      - EDUAGENT_DATA_DIR=/data
    volumes:
      - clawed-data:/data
      - ./materials:/materials:ro
    restart: unless-stopped

volumes:
  clawed-data:
```

Your folder should now look like:

```
clawed/
  .env
  docker-compose.yml
  materials/          (optional — put your lesson plans here)
```

## Step 4: Start it up

In your terminal, from the `clawed` folder:

```bash
docker compose up -d
```

That's it. The first time takes a few minutes to download everything.

Check that it's running:

```bash
docker compose ps
```

You should see `web` with status "Up".

## Step 5: Use it

- **Web dashboard:** Open http://localhost:8000 in your browser — new users see the onboarding wizard
- **Telegram (optional):** Uncomment the `TELEGRAM_BOT_TOKEN` line in `.env`, then run `docker compose exec web clawed bot`

## Loading your lesson plans

Put your files (PDFs, Word docs, PowerPoints) in the `materials/` folder, then run:

```bash
docker compose exec web clawed ingest /materials
```

Claw-ED reads your files and learns your teaching style.

## Common tasks

**Stop Claw-ED:**
```bash
docker compose down
```

**Restart after changing `.env`:**
```bash
docker compose down && docker compose up -d
```

**See what's happening (logs):**
```bash
docker compose logs -f
```

**Update to latest version:**
```bash
docker compose pull && docker compose up -d
```

## Using Ollama (free, local AI)

If you don't want to pay for API keys, you can run Ollama on your machine:

1. Install Ollama: https://ollama.com
2. Pull a model: `ollama pull llama3.2`
3. In your `.env`, comment out the API key lines and uncomment:
   ```
   OLLAMA_URL=http://host.docker.internal:11434
   ```
4. Restart: `docker compose down && docker compose up -d`

## Troubleshooting

**"Cannot connect to the Docker daemon"**
→ Open Docker Desktop. Wait for the whale icon to appear in your menu bar.

**"port 8000 already in use"**
→ Something else is using that port. Change `"8000:8000"` to `"8001:8000"` in `docker-compose.yml`, then access at http://localhost:8001.

**Bot isn't responding on Telegram**
→ Check your token is correct in `.env`. Run `docker compose logs web` to see errors.

**"API key invalid"**
→ Double-check your key in `.env`. Make sure there are no extra spaces. Restart with `docker compose down && docker compose up -d`.
