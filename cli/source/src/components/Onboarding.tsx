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

type Provider = 'anthropic-oauth' | 'anthropic-key' | 'openai' | 'google' | 'ollama-local' | 'ollama-cloud';

export function Onboarding({ onDone }: Props): React.ReactNode {
  const [step, setStep] = useState<'welcome' | 'provider' | 'auth' | 'done'>('welcome');
  const [provider, setProvider] = useState<Provider | null>(null);
  const [theme, setTheme] = useTheme();
  const exitState = useExitOnCtrlCDWithKeybindings();
  const oauthEnabled = isAnthropicAuthEnabled();

  useEffect(() => {
    logEvent('tengu_began_setup', { oauthEnabled });
  }, [oauthEnabled]);

  // Step 1: Welcome — select to continue
  if (step === 'welcome') {
    return (
      <Box flexDirection="column" paddingX={1} gap={1}>
        <Box flexDirection="column" alignItems="center" paddingY={1}>
          <Text bold color="claude">{'\uD83C\uDF4E'} Welcome to Claw-ED</Text>
          <Text dimColor>Your AI co-teacher</Text>
        </Box>
        <Text>
          Claw-ED generates lessons, games, slides, and assessments{'\n'}
          in your teaching voice. Let&apos;s connect to an AI provider.
        </Text>
        <Select
          options={[{ label: '→ Get Started', value: 'start' }]}
          onChange={() => setStep('provider')}
          onCancel={() => {}}
        />
      </Box>
    );
  }

  // Step 2: Provider selection
  if (step === 'provider') {
    const options = [
      ...(oauthEnabled ? [{
        label: '🔑 Anthropic (Claude) — Sign in with OAuth',
        value: 'anthropic-oauth' as Provider,
      }] : []),
      {
        label: '🔑 Anthropic (Claude) — API key',
        value: 'anthropic-key' as Provider,
      },
      {
        label: '🔑 OpenAI (GPT) — API key',
        value: 'openai' as Provider,
      },
      {
        label: '🔑 Google (Gemini) — API key (free tier)',
        value: 'google' as Provider,
      },
      {
        label: '💻 Ollama — Local (free, runs on your computer)',
        value: 'ollama-local' as Provider,
      },
      {
        label: '☁️  Ollama Cloud — $20/month unlimited',
        value: 'ollama-cloud' as Provider,
      },
    ];

    return (
      <Box flexDirection="column" paddingX={1} gap={1}>
        <Text bold>Connect to an AI provider:</Text>
        <Select
          options={options}
          onChange={(value: string) => {
            setProvider(value as Provider);
            if (value === 'anthropic-oauth') {
              setStep('auth');
            } else {
              // For API key providers, go directly to done
              // The Python onboarding handles key collection
              setStep('done');
            }
          }}
          onCancel={() => {}}
        />
        <Text dimColor>
          {exitState.pending
            ? <>Press {exitState.keyName} again to exit</>
            : <>↑↓ to select · Enter to confirm</>
          }
        </Text>
      </Box>
    );
  }

  // Step 3: Auth (OAuth for Anthropic)
  if (step === 'auth' && provider === 'anthropic-oauth') {
    return (
      <Box flexDirection="column" paddingX={1}>
        <ConsoleOAuthFlow onDone={() => setStep('done')} />
      </Box>
    );
  }

  // Auto-advance when done
  useEffect(() => {
    if (step === 'done') {
      const timer = setTimeout(onDone, 2000);
      return () => clearTimeout(timer);
    }
  }, [step, onDone]);

  // Step 4: Done
  if (step === 'done') {
    const providerName = provider === 'anthropic-oauth' ? 'Anthropic (OAuth)'
      : provider === 'anthropic-key' ? 'Anthropic'
      : provider === 'openai' ? 'OpenAI'
      : provider === 'google' ? 'Google Gemini'
      : provider === 'ollama-local' ? 'Ollama (local)'
      : provider === 'ollama-cloud' ? 'Ollama Cloud'
      : 'AI provider';

    return (
      <Box flexDirection="column" paddingX={1} gap={1}>
        <Text color="green">✓ Connected to {providerName}</Text>
        <Text>
          Talk naturally to generate lessons. Try:{'\n'}
          <Text bold>&quot;Make me a lesson on the causes of WWI for 8th grade&quot;</Text>
        </Text>
        <Text dimColor>
          Tip: Run /help to see all commands
        </Text>
      </Box>
    );
  }

  // Fallback
  return <Box><Text>Setting up...</Text></Box>;
}

function SkippableStep({ skip, onSkip, children }: {
  skip: boolean;
  onSkip(): void;
  children: React.ReactNode;
}): React.ReactNode {
  useEffect(() => {
    if (skip) onSkip();
  }, [skip, onSkip]);
  return skip ? null : children;
}
