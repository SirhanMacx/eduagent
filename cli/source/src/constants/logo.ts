/**
 * Claw-ED ASCII Logo — The Apple Lobster
 *
 * A red apple with green stem, white claw scratches, and gold lobster
 * arms/claws extending from the sides. Animated with color in terminal.
 */

// ANSI color codes
const R = '\x1b[38;2;220;50;47m'   // Red (apple body)
const G = '\x1b[38;2;80;180;80m'   // Green (stem/leaf)
const W = '\x1b[38;2;255;255;255m' // White (claw marks)
const Y = '\x1b[38;2;212;168;67m'  // Gold (claws/arms)
const C = '\x1b[38;2;100;200;220m' // Cyan (eyes)
const D = '\x1b[2m'                // Dim
const B = '\x1b[1m'                // Bold
const X = '\x1b[0m'                // Reset

// Block-art colored logo — pixel art style using █▀▄░ characters
function coloredLogo(): string[] {
  return [
    `               ${G}▄█▄${X}`,
    `            ${G}▄${R}██████${G}▄${X}`,
    `          ${R}▄██████████▄${X}`,
    `   ${Y}▄▄▄${X}   ${R}██${W}░░░${R}██████${X}   ${Y}▄▄▄${X}`,
    `  ${Y}█${C}o${Y}██${X}${Y}▄${R}██${W}░░░${R}███████${Y}▄${Y}██${C}o${Y}█${X}`,
    `  ${Y}█▄▄█${R}███${W}░░░${R}████████${Y}█▄▄█${X}`,
    `   ${Y}▀██${X}  ${R}████████████${X}  ${Y}██▀${X}`,
    `    ${Y}▀▀${X}   ${R}▀████████▀${X}   ${Y}▀▀${X}`,
    `            ${R}▀████▀${X}`,
  ]
}

// Plain text fallback (no ANSI, for non-TTY and --version on basic terminals)
export const LOGO_FULL = [
  '               .#.',
  '            .######.',
  '          .##########.',
  '   ___   ##///########   ___',
  '  |o##|.##///##########.|##o|',
  '  |____|##///###########|____|',
  '   .__   ############   __.',
  '    --    .########.    --',
  '            .####.',
]

// Compact (3 lines)
export const LOGO_COMPACT = [
  '  _  .##.  _',
  ' |o|##/##|o|',
  '  -  .##.  -',
]

// Brand text
export const BRAND_TEXT = 'Claw-ED'
export const BRAND_TAGLINE = 'Your AI co-teacher'

export const LOGO_WITH_TEXT = [
  ...LOGO_FULL,
  '',
  '      C L A W - E D',
  '     Your AI co-teacher',
]

/**
 * Animated, colorful logo reveal for interactive terminal startup.
 *
 * Phase 1: Apple body draws top-to-bottom (red + green stem)
 * Phase 2: Claw arms extend from the sides (gold, with snap animation)
 * Phase 3: Brand text appears
 */
export async function animateLogo(
  _color: string = '',
  skipAnimation: boolean = false,
): Promise<void> {
  if (skipAnimation || !process.stdout.isTTY) {
    for (const line of LOGO_WITH_TEXT) {
      console.log(line)
    }
    return
  }

  process.stdout.write('\x1b[?25l') // Hide cursor

  try {
    const lines = coloredLogo()

    // Phase 1: Draw stem (fast)
    process.stdout.write(lines[0] + '\n')
    await _sleep(120)
    process.stdout.write(lines[1] + '\n')
    await _sleep(120)

    // Phase 2: Apple body grows
    process.stdout.write(lines[2] + '\n')
    await _sleep(100)

    // Phase 3: Arms + claws extend (slightly slower for drama)
    for (let i = 3; i < 6; i++) {
      process.stdout.write(lines[i] + '\n')
      await _sleep(150)
    }

    // Phase 4: Legs
    for (let i = 6; i < lines.length; i++) {
      process.stdout.write(lines[i] + '\n')
      await _sleep(100)
    }

    // Phase 5: Claw snap! (redraw claw line with closed mouth)
    await _sleep(300)
    process.stdout.write('\x1b[5A') // Move up 5 lines
    const snapLine = `${Y} / ${C}o${Y} \\${X}${Y}----${R}|${X}    ${W}///${X}         ${R}|${X}${Y}----${Y}/ ${C}o${Y} \\${X}`
    process.stdout.write('\x1b[2K' + snapLine + '\n') // Clear line + redraw
    const closedLine = `${Y} \\_${B}=${Y}=_/${X}   ${R}|${X}    ${W}///${X}         ${R}|${X}   ${Y}\\_${B}=${Y}=_/${X}`
    process.stdout.write('\x1b[2K' + closedLine + '\n')
    await _sleep(200)

    // Snap back open
    process.stdout.write('\x1b[2A')
    process.stdout.write('\x1b[2K' + lines[4] + '\n')
    process.stdout.write('\x1b[2K' + lines[5] + '\n')
    process.stdout.write('\x1b[3B') // Move back down

    // Phase 6: Brand text
    await _sleep(300)
    process.stdout.write(`\n${B}${Y}      C L A W - E D${X}\n`)
    await _sleep(200)
    process.stdout.write(`${D}     Your AI co-teacher${X}\n`)
    await _sleep(400)
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
