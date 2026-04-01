/**
 * Claw-ED v3 Configuration Reader
 *
 * Reads teacher configuration from ~/.eduagent/config.json and secrets
 * from ~/.eduagent/secrets.json. Also supports Claude Code OAuth tokens
 * from the secure storage layer for Anthropic provider auth.
 *
 * Auth chain (priority order):
 * 1. Environment variables (ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY)
 * 2. Claude Code OAuth tokens (~/.claude/.credentials.json) -- Anthropic only
 * 3. ~/.eduagent/secrets.json
 */

import { readFileSync, existsSync } from 'fs'
import { join } from 'path'
import { homedir } from 'os'

export interface TeacherProfile {
  name: string
  school: string
  subjects: string[]
  grade_levels: string[]
  state: string
}

export interface ClawedConfig {
  provider: string // "anthropic" | "openai" | "google" | "ollama"
  anthropic_model?: string
  openai_model?: string
  google_model?: string
  ollama_model?: string
  export_format?: string
  telegram_token?: string
  telegram_user_id?: number
  teacher_profile?: TeacherProfile
  tier_models?: Record<string, string>
}

interface SecretsFile {
  anthropic_api_key?: string
  openai_api_key?: string
  google_api_key?: string
  [key: string]: string | undefined
}

interface ClaudeCredentials {
  oauthAccessToken?: string
  accessToken?: string
  [key: string]: unknown
}

const EDUAGENT_DIR = join(homedir(), '.eduagent')
const CONFIG_PATH = join(EDUAGENT_DIR, 'config.json')
const SECRETS_PATH = join(EDUAGENT_DIR, 'secrets.json')
const CLAUDE_CREDENTIALS_PATH = join(homedir(), '.claude', '.credentials.json')

/**
 * Reads and returns a parsed JSON file, or null if it does not exist or is invalid.
 */
function readJsonFile<T>(filePath: string): T | null {
  if (!existsSync(filePath)) {
    return null
  }
  try {
    const raw = readFileSync(filePath, 'utf-8')
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

/**
 * Reads the Claw-ED teacher configuration from ~/.eduagent/config.json.
 * Returns a default config (provider: "anthropic") if the file is missing.
 */
export function readClawedConfig(): ClawedConfig {
  const config = readJsonFile<ClawedConfig>(CONFIG_PATH)
  if (!config) {
    return { provider: 'anthropic' }
  }
  // Normalize provider to lowercase
  if (config.provider) {
    config.provider = config.provider.toLowerCase()
  } else {
    config.provider = 'anthropic'
  }
  return config
}

/**
 * Reads Claude Code OAuth access token from ~/.claude/.credentials.json.
 * These tokens start with sk-ant-oat01- and use Bearer auth, not x-api-key.
 */
function readClaudeOAuthToken(): string | null {
  const creds = readJsonFile<ClaudeCredentials>(CLAUDE_CREDENTIALS_PATH)
  if (!creds) return null
  const token = creds.oauthAccessToken || creds.accessToken
  if (typeof token === 'string' && token.length > 0) {
    return token
  }
  return null
}

/**
 * Reads the secrets file at ~/.eduagent/secrets.json.
 */
function readSecrets(): SecretsFile | null {
  return readJsonFile<SecretsFile>(SECRETS_PATH)
}

/**
 * Resolves an API key for the given provider using the auth chain:
 *
 * 1. Environment variables
 * 2. Claude Code OAuth tokens (Anthropic only)
 * 3. ~/.eduagent/secrets.json
 *
 * Returns an object with the key and whether it is an OAuth token
 * (OAuth tokens require Bearer auth instead of x-api-key).
 */
export function readApiKey(provider: string): { key: string | null; isOAuth: boolean } {
  const providerLower = provider.toLowerCase()

  // --- Priority 1: Environment variables ---
  const envMap: Record<string, string> = {
    anthropic: 'ANTHROPIC_API_KEY',
    openai: 'OPENAI_API_KEY',
    google: 'GOOGLE_API_KEY',
  }

  const envVar = envMap[providerLower]
  if (envVar) {
    const envValue = process.env[envVar]
    if (envValue && envValue.length > 0) {
      return { key: envValue, isOAuth: false }
    }
  }

  // --- Priority 2: Claude Code OAuth tokens (Anthropic only) ---
  if (providerLower === 'anthropic') {
    const oauthToken = readClaudeOAuthToken()
    if (oauthToken) {
      return { key: oauthToken, isOAuth: true }
    }
  }

  // --- Priority 3: ~/.eduagent/secrets.json ---
  const secrets = readSecrets()
  if (secrets) {
    const secretsMap: Record<string, string> = {
      anthropic: 'anthropic_api_key',
      openai: 'openai_api_key',
      google: 'google_api_key',
    }
    const secretKey = secretsMap[providerLower]
    if (secretKey && secrets[secretKey]) {
      return { key: secrets[secretKey]!, isOAuth: false }
    }
  }

  // Ollama does not require an API key
  if (providerLower === 'ollama') {
    return { key: null, isOAuth: false }
  }

  return { key: null, isOAuth: false }
}

/**
 * Returns the model name to use for the configured provider.
 * Falls back to sensible defaults.
 */
export function getModelForProvider(config: ClawedConfig): string {
  const defaults: Record<string, string> = {
    anthropic: 'claude-sonnet-4-20250514',
    openai: 'gpt-4o',
    google: 'gemini-2.0-flash',
    ollama: 'llama3.1',
  }

  const modelMap: Record<string, string | undefined> = {
    anthropic: config.anthropic_model,
    openai: config.openai_model,
    google: config.google_model,
    ollama: config.ollama_model,
  }

  return modelMap[config.provider] || defaults[config.provider] || defaults.anthropic
}
