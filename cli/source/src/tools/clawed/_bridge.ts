import { execSync, spawn } from 'child_process'
import { platform } from 'os'

export interface BridgeResult {
  status: 'success' | 'error'
  command: string
  data: unknown
  files: string[]
  warnings: string[]
  errors: string[]
}

const EMPTY_ERROR: BridgeResult = {
  status: 'error',
  command: '',
  data: null,
  files: [],
  warnings: [],
  errors: [],
}

export interface PythonCmd {
  /** The executable path (e.g. "/usr/bin/python3" or "C:\\Python\\py.exe") */
  exe: string
  /** Extra args that go before any user args (e.g. ["-3"] for `py -3`) */
  prefixArgs: string[]
}

let cachedPython: PythonCmd | null = null

/**
 * Resolve a Python executable name to its full path, cross-platform.
 * Uses `where` on Windows and `which` on macOS/Linux.
 */
function resolvePythonPath(name: string): string | null {
  const isWin = platform() === 'win32'
  const cmd = isWin ? `where ${name}` : `which ${name} 2>/dev/null`
  try {
    const out = execSync(cmd, { encoding: 'utf-8', timeout: 3000 }).trim()
    if (!out) return null
    // `where` on Windows can return multiple lines; take the first
    return out.split(/\r?\n/)[0].trim() || null
  } catch {
    return null
  }
}

/**
 * Find a Python 3.10+ executable that has the `clawed` package installed.
 *
 * Returns a PythonCmd with the executable path and any prefix args needed
 * to invoke it (e.g. `py -3` on Windows), or null if none found.
 *
 * Search order:
 *   python3.12, python3.11, python3.10, python3,
 *   py -3 (Windows only),
 *   python
 */
export function findPythonSync(): PythonCmd | null {
  if (cachedPython) return cachedPython

  // Build candidate list: version-specific first, then generic.
  // On Windows, also try `py -3` (the Windows Python Launcher) and `python`
  // since Windows doesn't ship `python3`.
  const isWin = platform() === 'win32'
  const candidates: Array<{ name: string; prefixArgs?: string[] }> = [
    { name: 'python3.12' },
    { name: 'python3.11' },
    { name: 'python3.10' },
    { name: 'python3' },
  ]
  if (isWin) {
    // `py -3` invokes the Windows Python Launcher with Python 3
    candidates.push({ name: 'py', prefixArgs: ['-3'] })
  }
  candidates.push({ name: 'python' })

  for (const { name, prefixArgs } of candidates) {
    const exePath = resolvePythonPath(name)
    if (!exePath) continue

    const prefix = prefixArgs ?? []
    // Build a shell command string for execSync validation.
    // Quote the exe path in case it contains spaces (common on Windows).
    const parts = [`"${exePath}"`, ...prefix]
    const shellCmd = parts.join(' ')

    // Verify this Python is 3.10+ and has clawed installed
    try {
      execSync(
        `${shellCmd} -c "import sys; assert sys.version_info >= (3,10); import clawed"`,
        { timeout: 5000, stdio: 'ignore' },
      )
    } catch {
      continue // Wrong version or clawed not installed, try next
    }

    cachedPython = { exe: exePath, prefixArgs: prefix }
    return cachedPython
  }
  return null
}

// No timeouts — teachers have large curriculum folders and complex lessons.
// A 100 GB ingest or multi-agent lesson can take hours. Never kill their work.
export const TIMEOUT_BY_COMMAND: Record<string, number> = {
  lesson: 7_200_000,
  unit: 7_200_000,
  game: 7_200_000,
  simulate: 7_200_000,
  ingest: 0,          // No timeout — ingest everything
  train: 7_200_000,
  export: 7_200_000,
  standards: 30_000,
  persona: 7_200_000,
  review: 7_200_000,
  materials: 7_200_000,
  assess: 7_200_000,
  differentiate: 7_200_000,
  search: 30_000,
  students: 30_000,
}

export function spawnPython(
  args: string[],
  opts?: { timeout?: number },
): Promise<BridgeResult> {
  const python = findPythonSync()
  if (!python)
    return Promise.resolve({
      ...EMPTY_ERROR,
      errors: [
        'Python is required. Install from python.org, then run: pip install clawed',
      ],
    })

  const timeout = opts?.timeout ?? 120_000
  return new Promise(resolve => {
    let stdout = '',
      stderr = '',
      killed = false
    // Inject --python after '-m clawed' to force the Python CLI path.
    // Without it, the entry router detects Node.js and routes back to
    // the Ink TUI, creating infinite recursion.
    const fullArgs = [
      ...python.prefixArgs,
      ...args.slice(0, 2),
      '--python',
      ...args.slice(2),
    ]
    const proc = spawn(python.exe, fullArgs, { stdio: ['ignore', 'pipe', 'pipe'] })
    const timer = timeout > 0 ? setTimeout(() => {
      killed = true
      proc.kill('SIGTERM')
    }, timeout) : null

    proc.stdout.on('data', (d: Buffer) => {
      stdout += d.toString()
    })
    proc.stderr.on('data', (d: Buffer) => {
      stderr += d.toString()
    })
    proc.on('close', code => {
      if (timer) clearTimeout(timer)
      if (killed) {
        resolve({
          ...EMPTY_ERROR,
          errors: ['This is taking longer than expected. Please try again.'],
        })
        return
      }
      if (code !== 0) {
        // Hide Python tracebacks: extract only the last line (the actual error)
        let errorMsg = stderr || `Something went wrong (exit code ${code}).`
        if (errorMsg.includes('Traceback')) {
          const lines = errorMsg.trim().split('\n')
          errorMsg = lines[lines.length - 1].trim() || errorMsg
        }
        resolve({
          ...EMPTY_ERROR,
          errors: [errorMsg],
        })
        return
      }
      try {
        resolve(JSON.parse(stdout.trim()))
      } catch (_e) {
        resolve({
          ...EMPTY_ERROR,
          errors: ['Something went wrong. Please try again.'],
        })
      }
    })
    proc.on('error', err => {
      if (timer) clearTimeout(timer)
      resolve({ ...EMPTY_ERROR, errors: [err.message] })
    })
  })
}
