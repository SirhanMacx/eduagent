/**
 * ClawedLogo - React/Ink component that renders the Claw-ED ASCII logo
 * with optional typewriter animation.
 */
import React, { useState, useEffect } from 'react'
import { Text, Box } from 'ink'
import { getLogoLines, BRAND_TEXT, BRAND_TAGLINE } from '../constants/logo.js'
import { getTheme } from '../utils/theme.js'

interface ClawedLogoProps {
  /** Which logo size to render */
  size?: 'full' | 'compact'
  /** Whether to animate the logo with a typewriter effect */
  animate?: boolean
  /** Delay between each line reveal in ms */
  lineDelay?: number
  /** Theme name to use for coloring */
  themeName?: 'dark' | 'light'
  /** Callback when animation completes */
  onAnimationComplete?: () => void
}

export function ClawedLogo({
  size = 'full',
  animate = false,
  lineDelay = 60,
  themeName = 'dark',
  onAnimationComplete,
}: ClawedLogoProps): React.ReactElement {
  const lines = getLogoLines(size)
  const theme = getTheme(themeName)
  const [visibleLines, setVisibleLines] = useState(animate ? 0 : lines.length)

  useEffect(() => {
    if (!animate) return

    if (visibleLines >= lines.length + 2) {
      // +2 for brand text and tagline
      onAnimationComplete?.()
      return
    }

    const timer = setTimeout(() => {
      setVisibleLines((prev: number) => prev + 1)
    }, lineDelay)

    return () => clearTimeout(timer)
  }, [animate, visibleLines, lines.length, lineDelay, onAnimationComplete])

  const goldColor = theme.claude // Warm Gold from theme
  const greenColor = theme.success // Deep Green from theme

  return (
    <Box flexDirection="column" alignItems="center">
      {lines.slice(0, Math.min(visibleLines, lines.length)).map((line, i) => (
        <Text key={i} color={goldColor}>
          {line}
        </Text>
      ))}
      {visibleLines > lines.length && (
        <Text color={goldColor} bold>
          {'\n       ' + BRAND_TEXT}
        </Text>
      )}
      {visibleLines > lines.length + 1 && (
        <Text color={greenColor} dimColor>
          {'    ' + BRAND_TAGLINE}
        </Text>
      )}
    </Box>
  )
}

export default ClawedLogo
