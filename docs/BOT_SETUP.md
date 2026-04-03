# Setting Up Your Claw-ED Telegram Bot

Get Ed -- your personal AI teaching assistant -- right in Telegram. Five minutes, no technical experience needed.

---

## Step 1: Create Your Bot with BotFather

1. Open Telegram and search for **@BotFather** (the official Telegram bot-maker)
2. Tap **Start** or send `/start`
3. Send `/newbot`
4. BotFather asks: **"What name do you want for your bot?"**
   - This is the display name students and colleagues will see
   - Suggestion: `Mr Smith's Teaching Assistant` or `Ms Garcia Claw-ED`
5. BotFather asks: **"Choose a username for your bot"**
   - Must end in `bot` or `Bot`
   - Suggestion: `MrSmithTeacherBot` or `MsGarciaClawEDBot`
   - If taken, try adding your school initials: `MrSmithGNSBot`
6. BotFather replies with your **bot token** -- a long string like:
   ```
   7123456789:AAHfiqks8w3nR4xzqGhK2m8gPqRze0gY1Xs
   ```
   **Copy this token.** You will need it in the next step.

> **Keep your token secret.** Anyone with this token can control your bot. If it leaks, send `/revoke` to @BotFather to generate a new one.

---

## Step 2: Install Claw-ED

```bash
pip install clawed
```

If you already have Claw-ED installed:
```bash
pip install clawed --upgrade
```

---

## Step 3: Save Your Token (One-Time Setup)

```bash
clawed config set-token YOUR_BOT_TOKEN
```

Replace `YOUR_BOT_TOKEN` with the token from BotFather. For example:
```bash
clawed config set-token 7123456789:AAHfiqks8w3nR4xzqGhK2m8gPqRze0gY1Xs
```

This saves the token to your config so you never need to type it again.

---

## Step 4: Start Using Ed

Once your token is saved, **Ed starts the Telegram bot automatically** every time you run `clawed`. There is no separate step to launch the bot -- he handles it himself.

```bash
clawed
```

Ed detects your saved Telegram token, checks that no bot instance is already running, and spawns the bot as a background daemon. You will see Ed's normal terminal interface, and your Telegram bot will be live simultaneously.

Now open Telegram, find your bot by its username, and send it a message.

### Manual start (if needed)

If you want to start the bot without the terminal TUI, you can run it directly:

```bash
clawed bot
```

---

## How Background Auto-Start Works

Ed manages the Telegram bot as a background daemon so you never have to think about it:

1. **On every `clawed` launch**, Ed checks for a saved Telegram bot token in your config, environment variable, or keyring.
2. **If a token exists**, he checks `~/.eduagent/bot.lock` for a running bot process (by PID).
3. **If no bot is running**, he spawns `python -m clawed bot` as a fully detached background process. On macOS/Linux this uses `start_new_session=True`; on Windows it uses `CREATE_NO_WINDOW`.
4. **If a bot is already running**, he skips the spawn. No duplicates.
5. **If the lock file is stale** (the PID is dead), Ed cleans it up and starts a fresh instance.

The bot runs silently in the background until you shut down your machine or explicitly stop it. You do not need to keep a terminal window open.

To manually stop the bot:
```bash
clawed bot --kill
```

---

## Step 5: Talk to Ed

Try sending these messages in Telegram:

- `I teach 9th grade biology`
- `Plan a 2-week unit on cell division`
- `Write a lesson on mitosis`
- `Make a worksheet for today's lesson`
- `/help` to see everything Ed can do

---

## Alternative Ways to Pass the Token

You do not have to use `config set-token`. Pick whichever feels most natural:

| Method | Command |
|--------|---------|
| **Saved config** (recommended) | `clawed config set-token TOKEN` then `clawed` |
| **Command-line flag** | `clawed bot --token TOKEN` |
| **Environment variable** | `export TELEGRAM_BOT_TOKEN=TOKEN` then `clawed` |

Ed checks in this order: `--token` flag > `TELEGRAM_BOT_TOKEN` env var > saved config.

---

## Common Errors

### "No bot token found"

You have not provided a token. Run:
```bash
clawed config set-token YOUR_TOKEN
```

### "Conflict: terminated by other getUpdates request"

Another instance of the bot is already running. Only one process can poll for updates at a time. Stop the other instance first with `clawed bot --kill`.

### "Unauthorized" or "401"

Your bot token is wrong or was revoked. Get a new one:
1. Message @BotFather
2. Send `/mybots`
3. Select your bot
4. Tap **API Token** > **Revoke current token**
5. Copy the new token and run `clawed config set-token NEW_TOKEN`

### "Network is unreachable" or timeout errors

Check your internet connection. Ed needs to reach Telegram's servers at `api.telegram.org`.

### Bot responds but AI features fail

Your LLM API key is not set. Run `clawed setup` to configure one, or set it directly:
```bash
# Option A: Anthropic (Claude)
export ANTHROPIC_API_KEY=sk-ant-...

# Option B: OpenAI (GPT-5.4)
export OPENAI_API_KEY=sk-...

# Option C: Ollama (cloud or local)
clawed config set-model ollama
```

---

## FAQ

**Can students message my bot?**
Yes, but Ed treats every Telegram user as a separate teacher session. For student-facing features, use the student bot: tell Ed `start student bot for lesson 1` and share the class code with students.

**Can I run multiple bots?**
Yes -- each bot needs its own token and its own `clawed bot` process. Use `--data-dir` to keep their data separate:
```bash
clawed bot --token TOKEN_A --data-dir ~/.clawed-bio
clawed bot --token TOKEN_B --data-dir ~/.clawed-history
```

**Is my data sent to Telegram?**
Only the messages you send to the bot and Ed's responses travel through Telegram's servers. Your lesson plan files stay on your machine. LLM API calls go directly to your chosen provider (Anthropic, OpenAI, Google, or Ollama).

**Can I customize my bot's profile picture?**
Yes. Message @BotFather, send `/mybots`, select your bot, tap **Edit Bot** > **Edit Botpic**, and upload a photo.

**Can I add my bot to a group chat?**
Not recommended -- Ed is designed for 1-on-1 conversations with individual teachers.

**Does the bot keep running when I close the terminal?**
Yes. Ed runs the bot as a background daemon that persists independently of your terminal session. He will keep running until you restart your machine or explicitly stop him with `clawed bot --kill`.

---

*Need help? Open an issue at https://github.com/SirhanMacx/Claw-ED/issues*
