import React, { useEffect, useState } from 'react';
import { logEvent } from 'src/services/analytics/index.js';
import { useExitOnCtrlCDWithKeybindings } from '../hooks/useExitOnCtrlCDWithKeybindings.js';
import { Box, Text, useTheme } from '../ink.js';
import { isAnthropicAuthEnabled } from '../utils/auth.js';
import { ConsoleOAuthFlow } from './ConsoleOAuthFlow.js';
import { Select } from './CustomSelect/select.js';

type Props = {
  onDone(): void;
};

type DetectedProvider = {
  name: string;
  type: string;
  ready: boolean;
  detail: string;
};

/**
 * Detect all available AI provider connections.
 * Checks OAuth tokens, env vars, running services.
 */
function detectProviders(): DetectedProvider[] {
  const found: DetectedProvider[] = [];

  // Anthropic OAuth (Claude Code / Codex)
  if (isAnthropicAuthEnabled()) {
    found.push({
      name: 'Anthropic (OAuth)',
      type: 'anthropic-oauth',
      ready: true,
      detail: 'Claude Code credentials detected',
    });
  }

  // Anthropic API key
  if (process.env.ANTHROPIC_API_KEY) {
    found.push({
      name: 'Anthropic (API key)',
      type: 'anthropic-key',
      ready: true,
      detail: `Key: ${process.env.ANTHROPIC_API_KEY.substring(0, 12)}...`,
    });
  }

  // OpenAI
  if (process.env.OPENAI_API_KEY) {
    found.push({
      name: 'OpenAI (GPT)',
      type: 'openai',
      ready: true,
      detail: `Key: ${process.env.OPENAI_API_KEY.substring(0, 12)}...`,
    });
  }

  // Google
  if (process.env.GOOGLE_API_KEY || process.env.GEMINI_API_KEY) {
    found.push({
      name: 'Google (Gemini)',
      type: 'google',
      ready: true,
      detail: 'API key from environment',
    });
  }

  // Codex OAuth
  if (process.env.CODEX_API_KEY || process.env.CODEX_OAUTH_TOKEN) {
    found.push({
      name: 'Codex',
      type: 'codex',
      ready: true,
      detail: 'Codex credentials detected',
    });
  }

  // Antigravity
  if (process.env.ANTIGRAVITY_API_KEY || process.env.ANTIGRAVITY_SDK_KEY) {
    found.push({
      name: 'Antigravity',
      type: 'antigravity',
      ready: true,
      detail: 'Antigravity SDK configured',
    });
  }

  return found;
}

export function Onboarding({ onDone }: Props): React.ReactNode {
  const [step, setStep] = useState<'detect' | 'confirm' | 'select' | 'auth' | 'done'>('detect');
  const [detected, setDetected] = useState<DetectedProvider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [_theme, _setTheme] = useTheme();
  const exitState = useExitOnCtrlCDWithKeybindings();

  useEffect(() => {
    logEvent('tengu_began_setup', { oauthEnabled: isAnthropicAuthEnabled() });
  }, []);

  // Auto-detect on mount
  useEffect(() => {
    if (step === 'detect') {
      const found = detectProviders();
      setDetected(found);
      if (found.length > 0) {
        setStep('confirm');
      } else {
        setStep('select');
      }
    }
  }, [step]);

  // Auto-advance when done
  useEffect(() => {
    if (step === 'done') {
      const timer = setTimeout(onDone, 1500);
      return () => clearTimeout(timer);
    }
  }, [step, onDone]);

  // Step 1: Detecting...
  if (step === 'detect') {
    return (
      <Box flexDirection="column" paddingX={1} gap={1}>
        <Text bold color="claude">{'\uD83C\uDF4E'} Claw-ED</Text>
        <Text dimColor>Detecting available AI providers...</Text>
      </Box>
    );
  }

  // Step 2: Found providers — confirm or choose different
  if (step === 'confirm') {
    const best = detected[0];
    const confirmOptions = [
      {
        label: `\u2713 Use ${best.name} (recommended)`,
        value: 'use-detected',
      },
      ...detected.slice(1).map((d) => ({
        label: `  Use ${d.name} instead`,
        value: d.type,
      })),
      {
        label: '  Configure a different provider...',
        value: 'other',
      },
    ];

    return (
      <Box flexDirection="column" paddingX={1} gap={1}>
        <Box flexDirection="column" paddingY={1}>
          <Text bold color="claude">{'\uD83C\uDF4E'} Welcome to Claw-ED</Text>
          <Text dimColor>Your AI co-teacher</Text>
        </Box>

        <Text bold>Found {detected.length} available connection{detected.length > 1 ? 's' : ''}:</Text>
        {detected.map((d, i) => (
          <Text key={i}>  <Text color="green">{'\u2713'}</Text> {d.name} <Text dimColor>— {d.detail}</Text></Text>
        ))}

        <Box marginTop={1}>
          <Select
            options={confirmOptions}
            onChange={(value: string) => {
              if (value === 'use-detected') {
                setSelectedProvider(best.type);
                if (best.type === 'anthropic-oauth') {
                  setStep('auth');
                } else {
                  setStep('done');
                }
              } else if (value === 'other') {
                setStep('select');
              } else {
                setSelectedProvider(value);
                setStep('done');
              }
            }}
            onCancel={() => {}}
          />
        </Box>
        <Text dimColor>
          {exitState.pending
            ? <>Press {exitState.keyName} again to exit</>
            : <>{'\u2191\u2193'} to select {'\u00B7'} Enter to confirm</>
          }
        </Text>
      </Box>
    );
  }

  // Step 3: Manual provider selection (nothing detected or user wants different)
  if (step === 'select') {
    const allProviders = [
      { label: '\uD83D\uDD11 Anthropic (Claude) — OAuth sign-in', value: 'anthropic-oauth' },
      { label: '\uD83D\uDD11 Anthropic (Claude) — API key', value: 'anthropic-key' },
      { label: '\uD83D\uDD11 OpenAI (GPT) — API key', value: 'openai' },
      { label: '\uD83D\uDD11 Google (Gemini) — API key (free tier available)', value: 'google' },
      { label: '\uD83D\uDD11 Codex — OAuth or API key', value: 'codex' },
      { label: '\uD83D\uDD11 Antigravity — SDK / API key', value: 'antigravity' },
      { label: '\uD83D\uDCBB Ollama — Local (free, runs on your computer)', value: 'ollama-local' },
      { label: '\u2601\uFE0F  Ollama Cloud — unlimited for $20/month', value: 'ollama-cloud' },
      { label: '\uD83D\uDD27 Other — custom API endpoint', value: 'custom' },
    ];

    return (
      <Box flexDirection="column" paddingX={1} gap={1}>
        <Box flexDirection="column" paddingY={1}>
          <Text bold color="claude">{'\uD83C\uDF4E'} Welcome to Claw-ED</Text>
          <Text dimColor>Your AI co-teacher</Text>
        </Box>

        <Text bold>Select an AI provider:</Text>
        <Select
          options={allProviders}
          onChange={(value: string) => {
            setSelectedProvider(value);
            if (value === 'anthropic-oauth') {
              setStep('auth');
            } else {
              setStep('done');
            }
          }}
          onCancel={() => {}}
        />
        <Text dimColor>
          {exitState.pending
            ? <>Press {exitState.keyName} again to exit</>
            : <>{'\u2191\u2193'} to select {'\u00B7'} Enter to confirm</>
          }
        </Text>
      </Box>
    );
  }

  // Step 4: OAuth flow
  if (step === 'auth') {
    return (
      <Box flexDirection="column" paddingX={1}>
        <ConsoleOAuthFlow onDone={() => setStep('done')} />
      </Box>
    );
  }

  // Step 5: Done
  if (step === 'done') {
    const providerNames: Record<string, string> = {
      'anthropic-oauth': 'Anthropic (OAuth)',
      'anthropic-key': 'Anthropic',
      'openai': 'OpenAI',
      'google': 'Google Gemini',
      'codex': 'Codex',
      'antigravity': 'Antigravity',
      'ollama-local': 'Ollama (local)',
      'ollama-cloud': 'Ollama Cloud',
      'custom': 'Custom provider',
    };
    const name = selectedProvider ? providerNames[selectedProvider] || selectedProvider : 'AI provider';

    return (
      <Box flexDirection="column" paddingX={1} gap={1}>
        <Text color="green">{'\u2713'} Connected to {name}</Text>
        <Text>
          Talk naturally to generate lessons:{'\n'}
          <Text bold>{'\u201C'}Make me a lesson on the causes of WWI for 8th grade{'\u201D'}</Text>
        </Text>
        <Text dimColor>
          Tip: Say {'\u201C'}set up Telegram{'\u201D'} to connect your phone{'\n'}
          Tip: Say {'\u201C'}ingest my files at ~/Documents{'\u201D'} to learn your voice
        </Text>
      </Box>
    );
  }

  return <Box><Text>Setting up...</Text></Box>;
}
