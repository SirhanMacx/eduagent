/**
 * Python bridge client for non-Anthropic providers (OpenAI, Google, Ollama).
 *
 * When the active provider in ~/.eduagent/config.json is not Anthropic,
 * this module spawns `python3 -m clawed.bridge chat` and pipes messages
 * through stdin/stdout as JSON.
 *
 * Reuses findPythonSync() from the existing _bridge.ts infrastructure.
 */
import { spawn } from 'child_process'
import { findPythonSync } from '../../tools/clawed/_bridge.js'
import {
  getClawedConfigProvider,
  CLAWED_PROVIDER_DEFAULT_MODELS,
  type ClawedProvider,
} from '../../utils/model/providers.js'

export interface BridgeChatRequest {
  messages: Array<{ role: string; content: string | unknown[] }>
  system?: string
  provider?: string
  model?: string
  max_tokens?: number
  temperature?: number
}

export interface BridgeChatResponse {
  status: 'success' | 'error'
  content: string
  model: string
  usage: { input_tokens: number; output_tokens: number }
  error: string | null
}

const BRIDGE_TIMEOUT = 300_000 // 5 minutes — LLM calls can be slow

/**
 * Send a chat request through the Python bridge.
 * Throws on timeout or Python errors.
 */
export function bridgeChat(
  request: BridgeChatRequest,
  opts?: { timeout?: number; signal?: AbortSignal },
): Promise<BridgeChatResponse> {
  const python = findPythonSync()
  if (!python) {
    return Promise.resolve({
      status: 'error',
      content: '',
      model: request.model || '',
      usage: { input_tokens: 0, output_tokens: 0 },
      error:
        'Python is required. Install from python.org, then run: pip install clawed',
    })
  }

  const timeout = opts?.timeout ?? BRIDGE_TIMEOUT
  const signal = opts?.signal

  return new Promise((resolve) => {
    let stdout = ''
    let stderr = ''
    let killed = false

    const proc = spawn(
      python.exe,
      [...python.prefixArgs, '-m', 'clawed.bridge', 'chat', '--stdin'],
      { stdio: ['pipe', 'pipe', 'pipe'] },
    )

    const timer = setTimeout(() => {
      killed = true
      proc.kill('SIGTERM')
    }, timeout)

    // Handle abort signal
    if (signal) {
      const onAbort = () => {
        killed = true
        proc.kill('SIGTERM')
        clearTimeout(timer)
      }
      signal.addEventListener('abort', onAbort, { once: true })
      proc.on('close', () => signal.removeEventListener('abort', onAbort))
    }

    proc.stdout.on('data', (d: Buffer) => {
      stdout += d.toString()
    })
    proc.stderr.on('data', (d: Buffer) => {
      stderr += d.toString()
    })

    // Write the request to stdin and close it
    const payload = JSON.stringify(request)
    proc.stdin.write(payload, () => {
      proc.stdin.end()
    })

    proc.on('close', (code) => {
      clearTimeout(timer)
      if (killed) {
        resolve({
          status: 'error',
          content: '',
          model: request.model || '',
          usage: { input_tokens: 0, output_tokens: 0 },
          error: signal?.aborted
            ? 'Request aborted'
            : 'This is taking longer than expected. Please try again.',
        })
        return
      }
      if (code !== 0) {
        resolve({
          status: 'error',
          content: '',
          model: request.model || '',
          usage: { input_tokens: 0, output_tokens: 0 },
          error: (() => {
            let msg = stderr || `Something went wrong (exit code ${code}).`
            if (msg.includes('Traceback')) {
              const lines = msg.trim().split('\n')
              msg = lines[lines.length - 1].trim() || msg
            }
            return msg
          })(),
        })
        return
      }
      try {
        resolve(JSON.parse(stdout.trim()))
      } catch {
        resolve({
          status: 'error',
          content: '',
          model: request.model || '',
          usage: { input_tokens: 0, output_tokens: 0 },
          error: 'Something went wrong. Please try again.',
        })
      }
    })

    proc.on('error', (err) => {
      clearTimeout(timer)
      resolve({
        status: 'error',
        content: '',
        model: request.model || '',
        usage: { input_tokens: 0, output_tokens: 0 },
        error: err.message,
      })
    })
  })
}

/**
 * Build a BridgeChatRequest from the provider config and messages.
 */
export function buildBridgeRequest(
  provider: ClawedProvider,
  model: string,
  messages: Array<{ role: string; content: string }>,
  systemPrompt?: string,
): BridgeChatRequest {
  return {
    messages,
    system: systemPrompt || '',
    provider,
    model: model || CLAWED_PROVIDER_DEFAULT_MODELS[provider],
  }
}
