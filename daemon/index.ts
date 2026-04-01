#!/usr/bin/env node
/**
 * Claw-ED Daemon Entry Point
 *
 * Usage:
 *   clawed daemon start    — Start background daemon with Telegram bot
 *   clawed daemon stop     — Stop the daemon
 *   clawed daemon status   — Show daemon status
 *   clawed daemon logs     — Tail daemon log
 *   clawed daemon logs -f  — Follow daemon log
 */
import { readFileSync, existsSync } from 'fs'
import { join } from 'path'
import { homedir } from 'os'
import { ProcessManager } from './process-manager.js'
import { TelegramBridge } from './telegram-bridge.js'

function loadConfig() {
  const configPath = join(homedir(), '.eduagent', 'config.json')
  if (!existsSync(configPath)) {
    return null
  }
  try {
    return JSON.parse(readFileSync(configPath, 'utf-8'))
  } catch {
    return null
  }
}

async function main(): Promise<void> {
  const cmd = process.argv[2] || 'help'
  const pm = new ProcessManager()

  switch (cmd) {
    case 'start': {
      // Check if already running
      if (pm.isRunning()) {
        console.log('Claw-ED daemon is already running.')
        pm.printStatus()
        return
      }

      // Load config
      const config = loadConfig()
      if (!config) {
        console.error('Claw-ED is not configured. Run "clawed setup" first.')
        process.exit(1)
      }

      if (!config.telegram_token) {
        console.error('No Telegram token configured.')
        console.error('Set it with: clawed config set-token --telegram YOUR_BOT_TOKEN')
        process.exit(1)
      }

      // Start daemon
      pm.writePid()
      pm.log('Daemon starting...')

      const bridge = new TelegramBridge(config, pm)

      // Graceful shutdown handlers
      const shutdown = async () => {
        pm.log('Daemon shutting down...')
        await bridge.stop()
        pm.removePid()
        pm.log('Daemon stopped.')
        process.exit(0)
      }

      process.on('SIGTERM', shutdown)
      process.on('SIGINT', shutdown)
      process.on('uncaughtException', (err) => {
        pm.log(`Uncaught exception: ${err.message}\n${err.stack}`)
      })
      process.on('unhandledRejection', (reason) => {
        pm.log(`Unhandled rejection: ${reason}`)
      })

      try {
        await bridge.start()
        console.log('Claw-ED daemon started. Telegram bot is online.')
        console.log(`Logs: ${pm.getLogPath()}`)

        // Keep process alive
        await new Promise(() => {})
      } catch (err: any) {
        pm.log(`Failed to start: ${err.message}`)
        pm.removePid()
        console.error(`Failed to start daemon: ${err.message}`)
        process.exit(1)
      }
      break
    }

    case 'stop': {
      pm.stop()
      break
    }

    case 'status': {
      pm.printStatus()
      break
    }

    case 'logs': {
      const follow = process.argv.includes('-f') || process.argv.includes('--follow')
      pm.tailLogs(follow)
      break
    }

    case 'install': {
      // Install as a system service
      const daemonPath = __filename
      const platform = process.platform

      if (platform === 'darwin') {
        pm.installLaunchd(daemonPath)
      } else if (platform === 'linux') {
        pm.installSystemd(daemonPath)
      } else {
        console.error(`Daemon service install not supported on ${platform}.`)
        console.error('Use WSL on Windows for full daemon support.')
        process.exit(1)
      }
      break
    }

    case 'uninstall': {
      const platform = process.platform
      if (platform === 'darwin') {
        pm.uninstallLaunchd()
      } else if (platform === 'linux') {
        pm.uninstallSystemd()
      }
      pm.stop()
      break
    }

    case 'help':
    default: {
      console.log(`
Claw-ED Daemon — Always-on teaching assistant

Usage:
  clawed daemon start      Start the daemon (Telegram bot goes online)
  clawed daemon stop       Stop the daemon
  clawed daemon status     Show daemon status and uptime
  clawed daemon logs       Show recent daemon logs
  clawed daemon logs -f    Follow daemon logs in real-time
  clawed daemon install    Install as system service (auto-start on boot)
  clawed daemon uninstall  Remove system service

The daemon keeps your Telegram bot online so you can request
lessons, games, and materials from your phone.
`)
      break
    }
  }
}

main().catch((err) => {
  console.error('Daemon error:', err.message)
  process.exit(1)
})
