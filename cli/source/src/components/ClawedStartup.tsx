/**
 * ClawedStartup - Startup sequence component for Claw-ED.
 * Shows: logo animation -> brand text -> tagline -> transitions to REPL.
 */
import React, { useState, useCallback } from 'react'
import { Box, Text } from 'ink'
import { ClawedLogo } from './ClawedLogo.js'

interface ClawedStartupProps {
  /** Theme name */
  themeName?: 'dark' | 'light'
  /** Called when startup animation completes */
  onComplete?: () => void
  /** Skip animation entirely */
  skipAnimation?: boolean
}

export function ClawedStartup({
  themeName = 'dark',
  onComplete,
  skipAnimation = false,
}: ClawedStartupProps): React.ReactElement | null {
  const [phase, setPhase] = useState<'logo' | 'done'>(
    skipAnimation ? 'done' : 'logo',
  )

  const handleAnimationComplete = useCallback(() => {
    // Brief pause after animation, then transition
    const timer = setTimeout(() => {
      setPhase('done')
      onComplete?.()
    }, 800)
    return () => clearTimeout(timer)
  }, [onComplete])

  if (skipAnimation || phase === 'done') {
    return null
  }

  return (
    <Box flexDirection="column" alignItems="center" paddingY={1}>
      <ClawedLogo
        size="full"
        animate={true}
        lineDelay={50}
        themeName={themeName}
        onAnimationComplete={handleAnimationComplete}
      />
      <Box marginTop={1}>
        <Text dimColor>Starting up...</Text>
      </Box>
    </Box>
  )
}

export default ClawedStartup
