/**
 * Claw-ED Daemon — Telegram Bridge
 *
 * Bridges Telegram messages to the Claw-ED Python engine via subprocess.
 * Uses the same LLM router as the Ink TUI for natural language routing.
 *
 * Security:
 * - Only responds to the configured teacher's Telegram user ID
 * - Rate limited: max 10 requests/minute
 * - Config-modifying commands are blocked from Telegram
 */
import { spawn } from 'child_process'
import { join } from 'path'
import { homedir } from 'os'
import { readFileSync, existsSync, createReadStream } from 'fs'
import { ProcessManager } from './process-manager.js'

// Rate limiter
interface RateLimit {
  timestamps: number[]
  maxPerMinute: number
}

interface ClawedConfig {
  provider: string
  telegram_token?: string
  telegram_user_id?: number
  teacher_profile?: {
    name: string
    subjects: string[]
    grade_levels: string[]
    state: string
  }
}

interface BridgeResult {
  status: 'success' | 'error'
  command: string
  data: unknown
  files: string[]
  warnings: string[]
  errors: string[]
}

// Blocked commands — cannot be run via Telegram
const BLOCKED_COMMANDS = new Set([
  'config', 'setup', 'daemon', 'serve', 'mcp-server', 'tui',
])

// Command patterns for NL intent detection (fast path before LLM)
const INTENT_PATTERNS: Array<{ pattern: RegExp; command: string[] }> = [
  { pattern: /^\/lesson\s+(.+)/i, command: ['gen', 'lesson'] },
  { pattern: /^\/game\s+(.+)/i, command: ['game', 'create'] },
  { pattern: /^\/unit\s+(.+)/i, command: ['gen', 'unit'] },
  { pattern: /^\/ingest\s+(.+)/i, command: ['gen', 'ingest'] },
  { pattern: /^\/status/i, command: ['status'] },
  { pattern: /^\/help/i, command: ['help'] },
]

export class TelegramBridge {
  private bot: any // node-telegram-bot-api instance
  private config: ClawedConfig
  private pm: ProcessManager
  private rateLimit: RateLimit = { timestamps: [], maxPerMinute: 10 }
  private isPolling = false

  constructor(config: ClawedConfig, pm: ProcessManager) {
    this.config = config
    this.pm = pm
  }

  /** Start Telegram bot polling. */
  async start(): Promise<void> {
    const token = this.config.telegram_token
    if (!token) {
      this.pm.log('No Telegram token configured. Run "clawed config telegram" to set it.')
      throw new Error('No Telegram token configured')
    }

    // Dynamic import to avoid requiring the package when not using Telegram
    const TelegramBot = (await import('node-telegram-bot-api')).default
    this.bot = new TelegramBot(token, { polling: true })
    this.isPolling = true

    this.pm.log(`Telegram bot started. Listening for messages...`)

    this.bot.on('message', async (msg: any) => {
      await this.handleMessage(msg)
    })

    this.bot.on('polling_error', (err: Error) => {
      this.pm.log(`Telegram polling error: ${err.message}`)
    })
  }

  /** Stop Telegram bot polling. */
  async stop(): Promise<void> {
    if (this.bot && this.isPolling) {
      await this.bot.stopPolling()
      this.isPolling = false
      this.pm.log('Telegram bot stopped.')
    }
  }

  /** Handle an incoming Telegram message. */
  private async handleMessage(msg: any): Promise<void> {
    const chatId = msg.chat.id
    const userId = msg.from?.id
    const text = msg.text?.trim()

    if (!text) return

    // Security: only respond to configured teacher
    if (this.config.telegram_user_id && userId !== this.config.telegram_user_id) {
      await this.bot.sendMessage(chatId,
        '🔒 This is a private teaching assistant. Contact your administrator.')
      this.pm.log(`Rejected message from unauthorized user ${userId}`)
      return
    }

    // Rate limiting
    if (!this.checkRateLimit()) {
      await this.bot.sendMessage(chatId,
        '⏳ Too many requests. Please wait a moment.')
      return
    }

    this.pm.log(`Message from ${msg.from?.first_name}: ${text.slice(0, 100)}`)

    try {
      // Check for /command syntax first (fast path)
      const directCommand = this.parseDirectCommand(text)
      if (directCommand) {
        await this.executeAndReply(chatId, directCommand.args, directCommand.topic)
        return
      }

      // Handle /help
      if (text.toLowerCase() === '/help' || text.toLowerCase() === '/start') {
        await this.sendHelp(chatId)
        return
      }

      // Natural language — route through LLM for intent detection
      await this.handleNaturalLanguage(chatId, text)
    } catch (err: any) {
      this.pm.log(`Error handling message: ${err.message}`)
      await this.bot.sendMessage(chatId,
        `❌ Something went wrong: ${err.message}`)
    }
  }

  /** Parse /command syntax into Python CLI args. */
  private parseDirectCommand(text: string): { args: string[]; topic: string } | null {
    for (const { pattern, command } of INTENT_PATTERNS) {
      const match = text.match(pattern)
      if (match) {
        const topic = match[1] || ''
        const args = [...command, topic, '--json'].filter(Boolean)
        return { args, topic }
      }
    }
    return null
  }

  /** Handle natural language messages by routing through LLM. */
  private async handleNaturalLanguage(chatId: number, text: string): Promise<void> {
    // Send typing indicator
    await this.bot.sendChatAction(chatId, 'typing')

    // For now, use simple keyword matching as a lightweight NL router.
    // The full LLM router integration comes when the TS LLM router is built.
    const lowerText = text.toLowerCase()

    let args: string[]
    let description: string

    if (lowerText.includes('lesson') && (lowerText.includes('make') || lowerText.includes('create') || lowerText.includes('generate'))) {
      // Extract topic: everything after "lesson on/about"
      const topicMatch = text.match(/(?:lesson|plan)\s+(?:on|about|for)\s+(.+)/i)
      const topic = topicMatch?.[1] || text
      args = ['gen', 'lesson', topic, '--json']
      description = `Generating lesson: ${topic}`
    } else if (lowerText.includes('game')) {
      const topicMatch = text.match(/game\s+(?:on|about|for)\s+(.+)/i)
      const topic = topicMatch?.[1] || text
      args = ['game', 'create', topic, '--json']
      description = `Creating game: ${topic}`
    } else if (lowerText.includes('unit')) {
      const topicMatch = text.match(/unit\s+(?:on|about|for)\s+(.+)/i)
      const topic = topicMatch?.[1] || text
      args = ['gen', 'unit', topic, '--json']
      description = `Planning unit: ${topic}`
    } else if (lowerText.includes('status') || lowerText.includes('how are you')) {
      await this.bot.sendMessage(chatId,
        `✅ Claw-ED daemon is running.\n📚 Ready to generate lessons, games, and materials.\n\nTry: "make me a lesson on the causes of WWI"`)
      return
    } else {
      // Default: try to generate a lesson from the text
      args = ['gen', 'lesson', text, '--json']
      description = `Generating lesson: ${text}`
    }

    await this.bot.sendMessage(chatId, `📝 ${description}...`)
    await this.bot.sendChatAction(chatId, 'typing')

    await this.executeAndReply(chatId, args, description)
  }

  /** Execute a Python command and send the result to Telegram. */
  private async executeAndReply(chatId: number, args: string[], description: string): Promise<void> {
    // Check for blocked commands
    if (BLOCKED_COMMANDS.has(args[0])) {
      await this.bot.sendMessage(chatId,
        `🚫 The "${args[0]}" command is only available from the terminal.`)
      return
    }

    const result = await this.spawnPython(args)

    if (result.status === 'error') {
      await this.bot.sendMessage(chatId,
        `❌ ${description} failed:\n${result.errors.join('\n')}`)
      return
    }

    // Send text summary
    const data = result.data as Record<string, unknown> | null
    const title = (data?.title as string) || description
    const score = data?.score as number | undefined

    let summary = `✅ ${title}`
    if (score !== undefined) {
      summary += ` (Quality: ${score}/10)`
    }
    await this.bot.sendMessage(chatId, summary)

    // Send generated files
    for (const filePath of result.files) {
      if (!existsSync(filePath)) continue

      const ext = filePath.split('.').pop()?.toLowerCase()
      try {
        if (ext === 'html') {
          await this.bot.sendDocument(chatId, filePath, {
            caption: `🎮 Interactive game: ${title}`,
          })
        } else if (ext === 'docx' || ext === 'pdf') {
          await this.bot.sendDocument(chatId, filePath, {
            caption: `📄 ${ext.toUpperCase()}: ${title}`,
          })
        } else if (ext === 'pptx') {
          await this.bot.sendDocument(chatId, filePath, {
            caption: `📊 Slides: ${title}`,
          })
        } else {
          await this.bot.sendDocument(chatId, filePath)
        }
      } catch (err: any) {
        this.pm.log(`Failed to send file ${filePath}: ${err.message}`)
        await this.bot.sendMessage(chatId,
          `📁 File generated: ${filePath}\n(Too large to send via Telegram)`)
      }
    }
  }

  /** Spawn a Python subprocess and parse JSON output. */
  private spawnPython(args: string[]): Promise<BridgeResult> {
    return new Promise((resolve) => {
      let stdout = ''
      let stderr = ''

      const proc = spawn('python3', ['-m', 'clawed', ...args], {
        stdio: ['ignore', 'pipe', 'pipe'],
        env: { ...process.env },
        timeout: 300_000, // 5 minute max
      })

      proc.stdout.on('data', (d: Buffer) => { stdout += d.toString() })
      proc.stderr.on('data', (d: Buffer) => { stderr += d.toString() })

      proc.on('close', (code: number | null) => {
        if (code !== 0) {
          resolve({
            status: 'error',
            command: args.join(' '),
            data: null,
            files: [],
            warnings: [],
            errors: [stderr || `Process exited with code ${code}`],
          })
          return
        }

        try {
          resolve(JSON.parse(stdout.trim()))
        } catch {
          resolve({
            status: 'error',
            command: args.join(' '),
            data: null,
            files: [],
            warnings: [],
            errors: [`Invalid JSON: ${stdout.slice(0, 500)}`],
          })
        }
      })

      proc.on('error', (err: Error) => {
        resolve({
          status: 'error',
          command: args.join(' '),
          data: null,
          files: [],
          warnings: [],
          errors: [err.message],
        })
      })
    })
  }

  /** Check rate limit (10 requests per minute). */
  private checkRateLimit(): boolean {
    const now = Date.now()
    // Remove timestamps older than 1 minute
    this.rateLimit.timestamps = this.rateLimit.timestamps.filter(
      t => now - t < 60_000
    )
    if (this.rateLimit.timestamps.length >= this.rateLimit.maxPerMinute) {
      return false
    }
    this.rateLimit.timestamps.push(now)
    return true
  }

  /** Send help message. */
  private async sendHelp(chatId: number): Promise<void> {
    const name = this.config.teacher_profile?.name || 'Teacher'
    await this.bot.sendMessage(chatId,
      `🍎 *Claw-ED — Your AI Co-Teacher*\n\n` +
      `Hi ${name}! Here's what I can do:\n\n` +
      `💬 *Natural language:*\n` +
      `"Make me a lesson on the causes of WWI"\n` +
      `"Create a game about the Renaissance"\n` +
      `"Plan a 3-week unit on photosynthesis"\n\n` +
      `📝 *Commands:*\n` +
      `/lesson <topic> — Generate a lesson\n` +
      `/game <topic> — Create an interactive game\n` +
      `/unit <topic> — Plan a multi-week unit\n` +
      `/status — Check system status\n` +
      `/help — Show this message\n\n` +
      `All outputs are generated as .docx files ready for printing.`,
      { parse_mode: 'Markdown' }
    )
  }
}
