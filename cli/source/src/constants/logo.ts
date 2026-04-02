/**
 * Claw-ED Logo & Branding
 *
 * Terminal wordmark with ANSI colors for interactive mode.
 * Clean text for static output (--version, non-TTY).
 * Detailed visuals belong on the landing page, not in ASCII art.
 */

// ANSI codes
const GOLD = '\x1b[38;2;212;168;67m'
const GREEN = '\x1b[38;2;80;180;80m'
const DIM = '\x1b[2m'
const BOLD = '\x1b[1m'
const RESET = '\x1b[0m'

// Plain text logo for --version and non-TTY
export const LOGO_FULL = [
  '',
  '  \uD83C\uDF4E  C L A W - E D',
  '',
  '  Your AI co-teacher',
  '',
]

export const LOGO_COMPACT = [
  '\uD83C\uDF4E Claw-ED',
]

export const BRAND_TEXT = 'Claw-ED'
export const BRAND_TAGLINE = 'Your AI co-teacher'

export const LOGO_WITH_TEXT = [
  ...LOGO_FULL,
]

/**
 * Animated colored startup for interactive sessions.
 *
 * Simple, clean, professional. No ASCII art — just the brand
 * rendered in warm gold with a brief reveal animation.
 */
export async function animateLogo(
  _color: string = '',
  skipAnimation: boolean = false,
): Promise<void> {
  if (skipAnimation || !process.stdout.isTTY) {
    for (const line of LOGO_FULL) {
      console.log(line)
    }
    return
  }

  process.stdout.write('\x1b[?25l') // Hide cursor

  try {
    process.stdout.write('\n')
    await _sleep(200)

    // Apple emoji + brand name in gold
    process.stdout.write(`  ${BOLD}${GOLD}\uD83C\uDF4E  C L A W - E D${RESET}\n`)
    await _sleep(400)

    // Tagline fades in
    process.stdout.write(`${DIM}  Your AI co-teacher${RESET}\n`)
    await _sleep(300)

    process.stdout.write('\n')
  } finally {
    process.stdout.write('\x1b[?25h') // Show cursor
  }
}

function _sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export function getLogoLines(size: 'full' | 'compact' = 'full'): string[] {
  return size === 'full' ? [...LOGO_FULL] : [...LOGO_COMPACT]
}
