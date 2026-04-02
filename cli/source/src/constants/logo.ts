/**
 * Claw-ED ASCII Logo
 *
 * A clean apple silhouette with three claw scratches and a graduation cap.
 * Designed for terminal rendering — standard ASCII only, no emoji, no
 * box-drawing characters that might break on Windows.
 */

// Full logo (12 lines) — graduation cap, apple, claw marks
export const LOGO_FULL = [
  '       ._________.',
  '       |_________|',
  '            ||',
  '           /  \\',
  '        .-\'    \'-.',
  '      .\'          \'.',
  '     /    ///        \\',
  '    |     ///         |',
  '    |    ///          |',
  '     \\               /',
  '      \'.           .\'',
  '        \'-._____.-\'',
]

// Compact logo (5 lines) — for status bar or tight spaces
export const LOGO_COMPACT = [
  '      ||',
  '     /  \\',
  '    | // |',
  '     \\  /',
  '      \'\'',
]

// Brand text
export const BRAND_TEXT = 'Claw-ED'
export const BRAND_TAGLINE = 'Your AI co-teacher'

// Full logo with text below
export const LOGO_WITH_TEXT = [
  ...LOGO_FULL,
  '',
  '      C L A W - E D',
  '     Your AI co-teacher',
]

/**
 * Animate the logo in the terminal with a line-by-line reveal.
 *
 * Uses raw ANSI escape codes so it works in any modern terminal
 * without requiring the Ink renderer. Call before the REPL starts.
 *
 * @param color - ANSI color code string (e.g., '\x1b[33m' for gold)
 * @param skipAnimation - If true, prints instantly (for piped/non-TTY output)
 */
export async function animateLogo(
  color: string = '\x1b[38;2;212;168;67m',  // Warm gold RGB
  skipAnimation: boolean = false,
): Promise<void> {
  const reset = '\x1b[0m'
  const dim = '\x1b[2m'
  const bold = '\x1b[1m'

  if (skipAnimation || !process.stdout.isTTY) {
    // Non-interactive: print instantly, no ANSI
    for (const line of LOGO_WITH_TEXT) {
      console.log(line)
    }
    return
  }

  // Hide cursor during animation
  process.stdout.write('\x1b[?25l')

  try {
    // Phase 1: Draw logo line by line (80ms per line)
    for (const line of LOGO_FULL) {
      process.stdout.write(`${color}${line}${reset}\n`)
      await _sleep(80)
    }

    // Phase 2: Brief pause, then brand text fades in
    await _sleep(300)
    process.stdout.write(`\n${bold}${color}      C L A W - E D${reset}\n`)
    await _sleep(200)
    process.stdout.write(`${dim}     Your AI co-teacher${reset}\n`)
    await _sleep(400)

    // Phase 3: Clear and transition (cursor moves back up)
    process.stdout.write('\n')
  } finally {
    // Always restore cursor
    process.stdout.write('\x1b[?25h')
  }
}

function _sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Get logo lines for static rendering.
 */
export function getLogoLines(size: 'full' | 'compact' = 'full'): string[] {
  return size === 'full' ? [...LOGO_FULL] : [...LOGO_COMPACT]
}
