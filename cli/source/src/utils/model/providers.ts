import { readFileSync } from 'fs'
import { join } from 'path'
import { homedir } from 'os'
import type { AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS } from '../../services/analytics/index.js'
import { isEnvTruthy } from '../envUtils.js'

export type APIProvider = 'firstParty' | 'bedrock' | 'vertex' | 'foundry'

/**
 * Claw-ED multi-provider types. These providers route through the Python
 * bridge instead of the Anthropic SDK.
 */
export type ClawedProvider = 'ollama' | 'openai' | 'google'

/** All providers (Anthropic SDK + Python-bridged). */
export type AnyProvider = APIProvider | ClawedProvider

/** Display names for provider selector UI. */
export const CLAWED_PROVIDER_INFO: Record<ClawedProvider, { name: string; description: string }> = {
  ollama: { name: 'Ollama', description: 'Local or cloud Ollama (free / $20/mo)' },
  openai: { name: 'OpenAI', description: 'GPT-4o and newer models' },
  google: { name: 'Google Gemini', description: 'Gemini 2.5 Flash and Pro' },
}

/** Default models per non-Anthropic provider. */
export const CLAWED_PROVIDER_DEFAULT_MODELS: Record<ClawedProvider, string> = {
  ollama: 'minimax-m2.7:cloud',
  openai: 'gpt-4o',
  google: 'gemini-2.5-flash',
}

let _cachedClawedProvider: AnyProvider | null = null

/**
 * Read the provider field from ~/.eduagent/config.json.
 * Returns null if the file doesn't exist or provider isn't set.
 */
export function getClawedConfigProvider(): ClawedProvider | null {
  if (_cachedClawedProvider !== null) {
    if (_cachedClawedProvider === 'firstParty' || _cachedClawedProvider === 'bedrock' ||
        _cachedClawedProvider === 'vertex' || _cachedClawedProvider === 'foundry') {
      return null // Anthropic-family provider
    }
    return _cachedClawedProvider as ClawedProvider
  }
  try {
    const configPath = process.env.EDUAGENT_DATA_DIR
      ? join(process.env.EDUAGENT_DATA_DIR, 'config.json')
      : join(homedir(), '.eduagent', 'config.json')
    const raw = readFileSync(configPath, 'utf-8')
    const config = JSON.parse(raw) as { provider?: string }
    const p = config.provider
    if (p === 'ollama' || p === 'openai' || p === 'google') {
      _cachedClawedProvider = p
      return p
    }
  } catch {
    // Config doesn't exist or is invalid — fall through
  }
  return null
}

/** True when the active provider routes through the Python bridge. */
export function isClawedBridgeProvider(): boolean {
  return getClawedConfigProvider() !== null
}

/** Reset the cached provider (used when config changes at runtime). */
export function clearClawedProviderCache(): void {
  _cachedClawedProvider = null
}

export function getAPIProvider(): APIProvider {
  return isEnvTruthy(process.env.CLAUDE_CODE_USE_BEDROCK)
    ? 'bedrock'
    : isEnvTruthy(process.env.CLAUDE_CODE_USE_VERTEX)
      ? 'vertex'
      : isEnvTruthy(process.env.CLAUDE_CODE_USE_FOUNDRY)
        ? 'foundry'
        : 'firstParty'
}

export function getAPIProviderForStatsig(): AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS {
  return getAPIProvider() as AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS
}

/**
 * Check if ANTHROPIC_BASE_URL is a first-party Anthropic API URL.
 * Returns true if not set (default API) or points to api.anthropic.com
 * (or api-staging.anthropic.com for ant users).
 */
export function isFirstPartyAnthropicBaseUrl(): boolean {
  const baseUrl = process.env.ANTHROPIC_BASE_URL
  if (!baseUrl) {
    return true
  }
  try {
    const host = new URL(baseUrl).host
    const allowedHosts = ['api.anthropic.com']
    if (process.env.USER_TYPE === 'ant') {
      allowedHosts.push('api-staging.anthropic.com')
    }
    return allowedHosts.includes(host)
  } catch {
    return false
  }
}
