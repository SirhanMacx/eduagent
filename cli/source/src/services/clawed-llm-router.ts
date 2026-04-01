/**
 * Claw-ED v3 Multi-Provider LLM Router
 *
 * Routes chat and tool_use calls to the teacher's configured LLM provider.
 * Supports Anthropic (via bundled SDK), OpenAI, Google Gemini, and Ollama
 * through a unified ChatResponse interface.
 *
 * Provider implementations:
 * - Anthropic: Uses @anthropic-ai/sdk (bundled in Claude Code source)
 * - OpenAI: Raw fetch to api.openai.com (no extra dependency)
 * - Google: Raw fetch to generativelanguage.googleapis.com
 * - Ollama: Raw fetch to localhost:11434
 */

import Anthropic from '@anthropic-ai/sdk'
import {
  type ClawedConfig,
  readApiKey,
  getModelForProvider,
} from './clawed-config.js'

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ToolDefinition {
  name: string
  description: string
  input_schema: Record<string, unknown>
}

export interface ToolCall {
  id: string
  name: string
  input: Record<string, unknown>
}

export interface ChatResponse {
  text: string
  toolCalls: ToolCall[]
  stopReason: string
}

// ---------------------------------------------------------------------------
// Retry helper with exponential backoff for rate limits
// ---------------------------------------------------------------------------

async function withRetry<T>(fn: () => Promise<T>, maxRetries = 3): Promise<T> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn()
    } catch (e: any) {
      const status = e.status ?? e.code ?? e.statusCode
      if (status === 429 && i < maxRetries - 1) {
        const delay = Math.min(1000 * 2 ** i, 30000)
        await new Promise((r) => setTimeout(r, delay))
        continue
      }
      throw e
    }
  }
  throw new Error('Max retries exceeded')
}

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------

export class ClawedLLMRouter {
  private config: ClawedConfig
  private model: string

  constructor(config: ClawedConfig) {
    this.config = config
    this.model = getModelForProvider(config)
  }

  /**
   * Send a chat request to the configured provider.
   * Optionally include tool definitions for tool_use / function-calling.
   */
  async chat(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
  ): Promise<ChatResponse> {
    const provider = this.config.provider.toLowerCase()

    switch (provider) {
      case 'anthropic':
        return this.chatAnthropic(messages, tools)
      case 'openai':
        return this.chatOpenAI(messages, tools)
      case 'google':
        return this.chatGoogle(messages, tools)
      case 'ollama':
        return this.chatOllama(messages, tools)
      default:
        throw new Error(
          `Unsupported provider "${provider}". Supported: anthropic, openai, google, ollama`,
        )
    }
  }

  // -------------------------------------------------------------------------
  // Anthropic — uses the bundled @anthropic-ai/sdk
  // -------------------------------------------------------------------------

  private async chatAnthropic(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
  ): Promise<ChatResponse> {
    const { key, isOAuth } = readApiKey('anthropic')
    if (!key) {
      throw new Error(
        'No Anthropic API key found. Set ANTHROPIC_API_KEY, log in with Claude Code, or add anthropic_api_key to ~/.eduagent/secrets.json',
      )
    }

    // OAuth tokens (sk-ant-oat01-*) need a custom auth header.
    // The SDK supports passing authToken for Bearer auth.
    const clientOpts: Record<string, unknown> = {}
    if (isOAuth) {
      // The Anthropic SDK accepts authToken for Bearer-style auth
      clientOpts.authToken = key
    } else {
      clientOpts.apiKey = key
    }

    const client = new Anthropic(clientOpts as any)

    // Separate system messages from the conversation
    const systemMessages = messages.filter((m) => m.role === 'system')
    const conversationMessages = messages.filter((m) => m.role !== 'system')

    const systemText =
      systemMessages.length > 0
        ? systemMessages.map((m) => m.content).join('\n\n')
        : undefined

    const anthropicMessages = conversationMessages.map((m) => ({
      role: m.role as 'user' | 'assistant',
      content: m.content,
    }))

    // Build tool definitions in Anthropic format
    const anthropicTools = tools?.map((t) => ({
      name: t.name,
      description: t.description,
      input_schema: t.input_schema,
    }))

    const requestParams: Record<string, unknown> = {
      model: this.model,
      max_tokens: 4096,
      messages: anthropicMessages,
    }
    if (systemText) requestParams.system = systemText
    if (anthropicTools && anthropicTools.length > 0) {
      requestParams.tools = anthropicTools
    }

    const response = await withRetry(() =>
      client.messages.create(requestParams as any),
    )

    // Parse response content blocks
    let text = ''
    const toolCalls: ToolCall[] = []

    for (const block of (response as any).content) {
      if (block.type === 'text') {
        text += block.text
      } else if (block.type === 'tool_use') {
        toolCalls.push({
          id: block.id,
          name: block.name,
          input: block.input as Record<string, unknown>,
        })
      }
    }

    return {
      text,
      toolCalls,
      stopReason: (response as any).stop_reason || 'end_turn',
    }
  }

  // -------------------------------------------------------------------------
  // OpenAI — raw fetch to api.openai.com
  // -------------------------------------------------------------------------

  private async chatOpenAI(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
  ): Promise<ChatResponse> {
    const { key } = readApiKey('openai')
    if (!key) {
      throw new Error(
        'No OpenAI API key found. Set OPENAI_API_KEY or add openai_api_key to ~/.eduagent/secrets.json',
      )
    }

    // Convert tools to OpenAI function-calling format
    const openaiTools = tools?.map((t) => ({
      type: 'function' as const,
      function: {
        name: t.name,
        description: t.description,
        parameters: t.input_schema,
      },
    }))

    const body: Record<string, unknown> = {
      model: this.model,
      messages: messages.map((m) => ({
        role: m.role,
        content: m.content,
      })),
    }
    if (openaiTools && openaiTools.length > 0) {
      body.tools = openaiTools
    }

    const response = await withRetry(async () => {
      const res = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${key}`,
        },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err: any = new Error(`OpenAI API error: ${res.status} ${res.statusText}`)
        err.status = res.status
        const text = await res.text().catch(() => '')
        err.body = text
        throw err
      }
      return res.json()
    })

    const choice = response.choices?.[0]
    if (!choice) {
      return { text: '', toolCalls: [], stopReason: 'error' }
    }

    const toolCalls: ToolCall[] = []
    if (choice.message?.tool_calls) {
      for (const tc of choice.message.tool_calls) {
        if (tc.type === 'function') {
          let parsedArgs: Record<string, unknown> = {}
          try {
            parsedArgs = JSON.parse(tc.function.arguments)
          } catch {
            parsedArgs = { _raw: tc.function.arguments }
          }
          toolCalls.push({
            id: tc.id,
            name: tc.function.name,
            input: parsedArgs,
          })
        }
      }
    }

    return {
      text: choice.message?.content || '',
      toolCalls,
      stopReason: choice.finish_reason || 'stop',
    }
  }

  // -------------------------------------------------------------------------
  // Google Gemini — raw fetch to generativelanguage.googleapis.com
  // -------------------------------------------------------------------------

  private async chatGoogle(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
  ): Promise<ChatResponse> {
    const { key } = readApiKey('google')
    if (!key) {
      throw new Error(
        'No Google API key found. Set GOOGLE_API_KEY or add google_api_key to ~/.eduagent/secrets.json',
      )
    }

    // Convert messages to Gemini format
    // Gemini uses "user" and "model" roles; system instructions go in a separate field
    const systemMessages = messages.filter((m) => m.role === 'system')
    const conversationMessages = messages.filter((m) => m.role !== 'system')

    const geminiContents = conversationMessages.map((m) => ({
      role: m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: m.content }],
    }))

    const body: Record<string, unknown> = {
      contents: geminiContents,
    }

    // System instruction
    if (systemMessages.length > 0) {
      body.systemInstruction = {
        parts: [{ text: systemMessages.map((m) => m.content).join('\n\n') }],
      }
    }

    // Tools in Gemini format
    if (tools && tools.length > 0) {
      body.tools = [
        {
          functionDeclarations: tools.map((t) => ({
            name: t.name,
            description: t.description,
            parameters: t.input_schema,
          })),
        },
      ]
    }

    const url = `https://generativelanguage.googleapis.com/v1beta/models/${this.model}:generateContent?key=${key}`

    const response = await withRetry(async () => {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err: any = new Error(`Google API error: ${res.status} ${res.statusText}`)
        err.status = res.status
        const text = await res.text().catch(() => '')
        err.body = text
        throw err
      }
      return res.json()
    })

    // Parse Gemini response
    const candidate = response.candidates?.[0]
    if (!candidate) {
      return { text: '', toolCalls: [], stopReason: 'error' }
    }

    let text = ''
    const toolCalls: ToolCall[] = []

    for (const part of candidate.content?.parts || []) {
      if (part.text) {
        text += part.text
      } else if (part.functionCall) {
        toolCalls.push({
          id: `gemini-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          name: part.functionCall.name,
          input: (part.functionCall.args as Record<string, unknown>) || {},
        })
      }
    }

    return {
      text,
      toolCalls,
      stopReason: candidate.finishReason || 'STOP',
    }
  }

  // -------------------------------------------------------------------------
  // Ollama — raw fetch to localhost:11434
  // -------------------------------------------------------------------------

  private async chatOllama(
    messages: ChatMessage[],
    tools?: ToolDefinition[],
  ): Promise<ChatResponse> {
    const ollamaUrl =
      process.env.OLLAMA_HOST || 'http://localhost:11434'

    // Ollama chat format is similar to OpenAI
    const body: Record<string, unknown> = {
      model: this.model,
      messages: messages.map((m) => ({
        role: m.role,
        content: m.content,
      })),
      stream: false,
    }

    // Ollama tool support requires v0.3.0+
    if (tools && tools.length > 0) {
      body.tools = tools.map((t) => ({
        type: 'function',
        function: {
          name: t.name,
          description: t.description,
          parameters: t.input_schema,
        },
      }))
    }

    const response = await withRetry(async () => {
      let res: Response
      try {
        res = await fetch(`${ollamaUrl}/api/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
      } catch (connErr: any) {
        throw new Error(
          `Cannot connect to Ollama at ${ollamaUrl}. Is Ollama running? Error: ${connErr.message}`,
        )
      }
      if (!res.ok) {
        const err: any = new Error(`Ollama API error: ${res.status} ${res.statusText}`)
        err.status = res.status
        const text = await res.text().catch(() => '')
        err.body = text
        // Detect tool_use failures from older Ollama versions
        if (
          tools &&
          tools.length > 0 &&
          (text.includes('does not support tools') ||
            text.includes('unknown field'))
        ) {
          throw new Error(
            'Ollama tool_use requires version 0.3.0 or later. Please update Ollama: https://ollama.ai/download',
          )
        }
        throw err
      }
      return res.json()
    })

    const toolCalls: ToolCall[] = []
    if (response.message?.tool_calls) {
      for (const tc of response.message.tool_calls) {
        toolCalls.push({
          id: `ollama-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          name: tc.function?.name || 'unknown',
          input: (tc.function?.arguments as Record<string, unknown>) || {},
        })
      }
    }

    return {
      text: response.message?.content || '',
      toolCalls,
      stopReason: response.done ? 'stop' : 'length',
    }
  }
}
