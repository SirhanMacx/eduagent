# Setting Up Your EDUagent Telegram Bot

Get your personal AI teaching assistant right in Telegram — 5 minutes, no technical experience needed.

---

## Step 1: Create Your Bot with BotFather

1. Open Telegram and search for **@BotFather** (the official Telegram bot-maker)
2. Tap **Start** or send `/start`
3. Send `/newbot`
4. BotFather asks: **"What name do you want for your bot?"**
   - This is the display name students and colleagues will see
   - Suggestion: `Mr Smith's Teaching Assistant` or `Ms Garcia EDUagent`
5. BotFather asks: **"Choose a username for your bot"**
   - Must end in `bot` or `Bot`
   - Suggestion: `MrSmithTeacherBot` or `MsGarciaEduBot`
   - If taken, try adding your school initials: `MrSmithGNSBot`
6. BotFather replies with your **bot token** — a long string like:
   ```
   7123456789:AAHfiqks8w3nR4xzqGhK2m8gPqRze0gY1Xs
   ```
   **Copy this token.** You'll need it in the next step.

> **Keep your token secret.** Anyone with this token can control your bot. If it leaks, send `/revoke` to @BotFather to generate a new one.

---

## Step 2: Install EDUagent with Telegram Support

```bash
pip install "eduagent[telegram]"
```

This installs EDUagent plus the `python-telegram-bot` library.

If you already have EDUagent installed:
```bash
pip install "eduagent[telegram]" --upgrade
```

---

## Step 3: Save Your Token (One-Time Setup)

```bash
eduagent config set-token YOUR_BOT_TOKEN
```

Replace `YOUR_BOT_TOKEN` with the token from BotFather. For example:
```bash
eduagent config set-token 7123456789:AAHfiqks8w3nR4xzqGhK2m8gPqRze0gY1Xs
```

This saves the token to `~/.eduagent/config.json` so you never need to type it again.

---

## Step 4: Start the Bot

```bash
eduagent bot
```

That's it! You should see:

```
🎓 EDUagent bot is running. Press Ctrl+C to stop.
   Data directory: /Users/you/.eduagent
```

Now open Telegram, find your bot by its username, and send it a message!

---

## Step 5: Talk to Your Bot

Try sending these messages:

- `I teach 9th grade biology`
- `Plan a 2-week unit on cell division`
- `Write a lesson on mitosis`
- `Make a worksheet for today's lesson`
- `/help` to see everything it can do

---

## Alternative Ways to Pass the Token

You don't have to use `config set-token`. Pick whichever feels most natural:

| Method | Command |
|--------|---------|
| **Saved config** (recommended) | `eduagent config set-token TOKEN` then `eduagent bot` |
| **Command-line flag** | `eduagent bot --token TOKEN` |
| **Environment variable** | `export TELEGRAM_BOT_TOKEN=TOKEN` then `eduagent bot` |

The bot checks in this order: `--token` flag > `TELEGRAM_BOT_TOKEN` env var > saved config.

---

## Keeping the Bot Running

The bot stops when you close your terminal. To keep it running in the background:

**On Mac/Linux (simplest):**
```bash
nohup eduagent bot &
```

**Using screen:**
```bash
screen -S eduagent
eduagent bot
# Press Ctrl+A, then D to detach
# Reattach later: screen -r eduagent
```

**Using a systemd service (Linux servers):**
```ini
# /etc/systemd/system/eduagent-bot.service
[Unit]
Description=EDUagent Telegram Bot
After=network.target

[Service]
Type=simple
User=your-username
ExecStart=/usr/local/bin/eduagent bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable eduagent-bot
sudo systemctl start eduagent-bot
```

---

## Common Errors

### "No bot token found"

You didn't provide a token. Run:
```bash
eduagent config set-token YOUR_TOKEN
```

### "python-telegram-bot is required"

You installed EDUagent without Telegram support. Fix with:
```bash
pip install "eduagent[telegram]"
```

### "Conflict: terminated by other getUpdates request"

Another instance of your bot is already running. Only one process can poll for updates at a time. Stop the other instance first.

### "Unauthorized" or "401"

Your bot token is wrong or was revoked. Get a new one:
1. Message @BotFather
2. Send `/mybots`
3. Select your bot
4. Tap **API Token** > **Revoke current token**
5. Copy the new token and run `eduagent config set-token NEW_TOKEN`

### "Network is unreachable" or timeout errors

Check your internet connection. The bot needs to reach Telegram's servers at `api.telegram.org`.

### Bot responds but AI features fail

Your LLM API key isn't set. Configure one:
```bash
# Option A: Anthropic (Claude) — best quality
export ANTHROPIC_API_KEY=sk-ant-...

# Option B: OpenAI (GPT-4o)
export OPENAI_API_KEY=sk-...

# Option C: Ollama (free, local)
eduagent config set-model ollama
```

---

## FAQ

**Can students message my bot?**
Yes, but EDUagent treats every Telegram user as a separate teacher session. For student-facing features, use the student bot: tell your bot `start student bot for lesson 1` and share the class code with students.

**Can I run multiple bots?**
Yes — each bot needs its own token and its own `eduagent bot` process. Use `--data-dir` to keep their data separate:
```bash
eduagent bot --token TOKEN_A --data-dir ~/.eduagent-bio
eduagent bot --token TOKEN_B --data-dir ~/.eduagent-history
```

**Is my data sent to Telegram?**
Only the messages you send to the bot and the bot's responses travel through Telegram's servers. Your lesson plan files stay on your machine. Your LLM API calls go directly to your chosen provider (Anthropic, OpenAI, or Ollama).

**Can I customize my bot's profile picture?**
Yes! Message @BotFather, send `/mybots`, select your bot, tap **Edit Bot** > **Edit Botpic**, and upload a photo.

**Can I add my bot to a group chat?**
Not recommended — EDUagent is designed for 1-on-1 conversations with individual teachers.

---

*Need help? Open an issue at https://github.com/eduagent/eduagent/issues*
