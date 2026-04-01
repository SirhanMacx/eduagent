import { execSync, spawn } from 'child_process'

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

let cachedPython: string | null = null

export function findPythonSync(): string | null {
  if (cachedPython) return cachedPython
  for (const name of ['python3', 'python']) {
    try {
      const path = execSync(`which ${name}`, { encoding: 'utf-8' }).trim()
      if (path) {
        cachedPython = path
        return path
      }
    } catch {
      continue
    }
  }
  return null
}

export const TIMEOUT_BY_COMMAND: Record<string, number> = {
  lesson: 120_000,
  unit: 180_000,
  game: 120_000,
  ingest: 300_000,
  train: 600_000,
  export: 60_000,
  standards: 5_000,
  persona: 5_000,
  review: 30_000,
  materials: 120_000,
  assess: 120_000,
  differentiate: 60_000,
  search: 10_000,
  students: 5_000,
}

export function spawnPython(
  args: string[],
  opts?: { timeout?: number },
): Promise<BridgeResult> {
  const python = findPythonSync()
  if (!python)
    return Promise.resolve({
      ...EMPTY_ERROR,
      errors: ['Python 3.10+ not found'],
    })

  const timeout = opts?.timeout ?? 120_000
  return new Promise(resolve => {
    let stdout = '',
      stderr = '',
      killed = false
    const proc = spawn(python, args, { stdio: ['ignore', 'pipe', 'pipe'] })
    const timer = setTimeout(() => {
      killed = true
      proc.kill('SIGTERM')
    }, timeout)

    proc.stdout.on('data', (d: Buffer) => {
      stdout += d.toString()
    })
    proc.stderr.on('data', (d: Buffer) => {
      stderr += d.toString()
    })
    proc.on('close', code => {
      clearTimeout(timer)
      if (killed) {
        resolve({
          ...EMPTY_ERROR,
          errors: [`Timed out after ${timeout}ms`],
        })
        return
      }
      if (code !== 0) {
        resolve({
          ...EMPTY_ERROR,
          errors: [stderr || `Exit code ${code}`],
        })
        return
      }
      try {
        resolve(JSON.parse(stdout.trim()))
      } catch {
        resolve({
          ...EMPTY_ERROR,
          errors: [`Invalid JSON: ${stdout.slice(0, 500)}`],
        })
      }
    })
    proc.on('error', err => {
      clearTimeout(timer)
      resolve({ ...EMPTY_ERROR, errors: [err.message] })
    })
  })
}
