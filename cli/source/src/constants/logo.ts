/**
 * Claw-ED ASCII Logo
 *
 * A professional apple with claw marks, graduation cap, and diploma scroll.
 * Uses box-drawing characters for clean lines. No emoji.
 */

// Full logo (~18 lines) - for startup and splash screens
export const LOGO_FULL = [
  '          ___,,___',
  '         /  /__  \\',
  '        /  /  \\   |',
  '       /___|   |  |',
  '      .-""""""""-.',
  '     /    ____    \\',
  '    |   //    \\\\   |',
  '    |  ||      ||  |',
  '    |  || ,//, ||  |',
  '    |  || //// ||  |',
  '    |  ||////  ||  |',
  '    |   \\\\    //   |',
  '     \\    """"    /',
  '      `-........-\'',
  '     ___|||  |||___',
  '    /   ========   \\',
  '    \\___============/',
  '     ~~~~||||~~~~',
]

// Compact logo (~5 lines) - for status line and tight spaces
export const LOGO_COMPACT = [
  '  _,,_',
  ' / __ \\',
  '| //// |',
  ' \\____/',
  '  ||||',
]

// Text-only brand mark
export const BRAND_TEXT = 'Claw-ED'
export const BRAND_TAGLINE = 'Your AI co-teacher'

// Logo with integrated text
export const LOGO_WITH_TEXT = [
  ...LOGO_FULL,
  '',
  '       C L A W - E D',
  '    Your AI co-teacher',
]

/**
 * Animation frames for typewriter-style logo reveal.
 * Each frame is an array of lines to display.
 * Lines are revealed top-to-bottom with a slight delay.
 */
export function getLogoAnimationFrames(): string[][] {
  const frames: string[][] = []

  // Build up the logo line by line
  for (let i = 1; i <= LOGO_WITH_TEXT.length; i++) {
    frames.push(LOGO_WITH_TEXT.slice(0, i))
  }

  return frames
}

/**
 * Get logo lines colored with theme colors.
 * Returns raw strings - caller applies chalk/color.
 */
export function getLogoLines(size: 'full' | 'compact' = 'full'): string[] {
  return size === 'full' ? [...LOGO_FULL] : [...LOGO_COMPACT]
}
