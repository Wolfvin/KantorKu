#!/usr/bin/env node

/**
 * Kantorku CLI - Interactive Command Line Interface for Kantorku AI Office
 *
 * A comprehensive CLI tool for managing and interacting with the Kantorku
 * AI-powered office framework.
 */

import { Command } from 'commander';
import chalk from 'chalk';
import boxen from 'boxen';
import { setupCommand } from './commands/setup';
import { chatCommand } from './commands/chat';
import { serveCommand } from './commands/serve';
import { devCommand } from './commands/dev';
import {
  workerListCommand,
  workerShowCommand,
  workerStartCommand,
  workerStopCommand,
} from './commands/workers';
import { statusCommand } from './commands/status';
import { initCommand } from './commands/init';

// ============================================================
// ASCII Art Banner
// ============================================================

const BANNER = `
  ╔╦╗┌─┐┌─┐┬  ┬┌─┐┌┐┌ ╦ ╦┌─┐┬─┐┬┌─
   ║ │ ││ ││  │├┤ │││ ║║║├┤ ├┬┘├┴┐
   ╩ └─┘└─┘┴─┘┴└─┘┘└┘ ╚╩╝└─┘┴└─┴ └─
`;

function showBanner(): void {
  console.log(
    boxen(
      chalk.cyan(BANNER) +
      chalk.white.bold('  AI-Powered Office Framework') + '\n' +
      chalk.gray('  v1.0.0') + '  ' + chalk.gray('│') + '  ' +
      chalk.cyan('kantorku.dev'),
      {
        padding: { top: 0, bottom: 1, left: 2, right: 2 },
        margin: 0,
        borderStyle: 'round',
        borderColor: 'cyan',
        float: 'left',
      }
    )
  );
  console.log('');
}

// ============================================================
// CLI Program Setup
// ============================================================

const program = new Command();

program
  .name('kantorku')
  .description('Interactive CLI for Kantorku - AI-Powered Office Framework')
  .version('1.0.0')
  .hook('preAction', () => {
    // Show banner for all commands except help
    const args = process.argv.slice(2);
    if (args.length > 0 && args[0] !== '--help' && args[0] !== '-h') {
      showBanner();
    }
  });

// ──────────────────────────────────────────────────────────────
// kantorku init - Scaffold new project
// ──────────────────────────────────────────────────────────────
program
  .command('init')
  .description('Scaffold a new Kantorku project')
  .option('-n, --name <name>', 'Project name')
  .option('-t, --template <template>', 'Template (basic, full, custom)')
  .option('-p, --provider <provider>', 'Default LLM provider')
  .action(async (options) => {
    try {
      await initCommand(options);
    } catch (error) {
      console.error(chalk.red(`\n  Error: ${(error as Error).message}\n`));
      process.exit(1);
    }
  });

// ──────────────────────────────────────────────────────────────
// kantorku setup - Interactive API key configuration
// ──────────────────────────────────────────────────────────────
program
  .command('setup')
  .description('Interactive setup wizard for API keys and configuration')
  .action(async () => {
    try {
      await setupCommand();
    } catch (error) {
      console.error(chalk.red(`\n  Error: ${(error as Error).message}\n`));
      process.exit(1);
    }
  });

// ──────────────────────────────────────────────────────────────
// kantorku chat - Interactive chat with the office
// ──────────────────────────────────────────────────────────────
program
  .command('chat')
  .description('Interactive chat with the Conductor/Manager')
  .option('-w, --websocket', 'Use WebSocket connection')
  .option('--worker <workerId>', 'Direct message to a specific worker')
  .action(async (options) => {
    try {
      await chatCommand({
        websocket: options.websocket,
        worker: options.worker,
      });
    } catch (error) {
      console.error(chalk.red(`\n  Error: ${(error as Error).message}\n`));
      process.exit(1);
    }
  });

// ──────────────────────────────────────────────────────────────
// kantorku serve - Start Python backend
// ──────────────────────────────────────────────────────────────
program
  .command('serve')
  .description('Start the Kantorku Python backend server')
  .option('-p, --port <port>', 'Port to run on', parseInt)
  .option('-h, --host <host>', 'Host to bind to')
  .option('-w, --workers <count>', 'Number of worker slots', parseInt)
  .option('--no-reload', 'Disable auto-reload')
  .action(async (options) => {
    try {
      await serveCommand({
        port: options.port,
        host: options.host,
        workers: options.workers,
        reload: options.reload,
      });
    } catch (error) {
      console.error(chalk.red(`\n  Error: ${(error as Error).message}\n`));
      process.exit(1);
    }
  });

// ──────────────────────────────────────────────────────────────
// kantorku dev - Start Next.js interface
// ──────────────────────────────────────────────────────────────
program
  .command('dev')
  .description('Start the Next.js development interface')
  .option('-p, --port <port>', 'Port to run on', parseInt)
  .option('-h, --host <host>', 'Host to bind to')
  .option('--open', 'Open in browser automatically')
  .action(async (options) => {
    try {
      await devCommand({
        port: options.port,
        host: options.host,
        open: options.open,
      });
    } catch (error) {
      console.error(chalk.red(`\n  Error: ${(error as Error).message}\n`));
      process.exit(1);
    }
  });

// ──────────────────────────────────────────────────────────────
// kantorku worker - Worker management
// ──────────────────────────────────────────────────────────────
const workerCmd = program
  .command('worker')
  .description('Manage Kantorku workers');

workerCmd
  .command('list')
  .alias('ls')
  .description('List all registered workers')
  .action(async () => {
    try {
      await workerListCommand();
    } catch (error) {
      console.error(chalk.red(`\n  Error: ${(error as Error).message}\n`));
      process.exit(1);
    }
  });

workerCmd
  .command('show <workerId>')
  .description('Show detailed information about a worker')
  .action(async (workerId: string) => {
    try {
      await workerShowCommand(workerId);
    } catch (error) {
      console.error(chalk.red(`\n  Error: ${(error as Error).message}\n`));
      process.exit(1);
    }
  });

workerCmd
  .command('start <workerId>')
  .description('Start a worker')
  .action(async (workerId: string) => {
    try {
      await workerStartCommand(workerId);
    } catch (error) {
      console.error(chalk.red(`\n  Error: ${(error as Error).message}\n`));
      process.exit(1);
    }
  });

workerCmd
  .command('stop <workerId>')
  .description('Stop a worker')
  .action(async (workerId: string) => {
    try {
      await workerStopCommand(workerId);
    } catch (error) {
      console.error(chalk.red(`\n  Error: ${(error as Error).message}\n`));
      process.exit(1);
    }
  });

// ──────────────────────────────────────────────────────────────
// kantorku status - System health check
// ──────────────────────────────────────────────────────────────
program
  .command('status')
  .description('Show system health and status information')
  .action(async () => {
    try {
      await statusCommand();
    } catch (error) {
      console.error(chalk.red(`\n  Error: ${(error as Error).message}\n`));
      process.exit(1);
    }
  });

// ──────────────────────────────────────────────────────────────
// Default action (no command)
// ──────────────────────────────────────────────────────────────
program.on('command:*', () => {
  console.error(
    chalk.red(`\n  Unknown command: ${chalk.white(process.argv.slice(2).join(' '))}`)
  );
  console.log(chalk.gray('  Run ') + chalk.cyan('kantorku --help') + chalk.gray(' for available commands.\n'));
  process.exit(1);
});

// If no arguments, show banner + help
if (process.argv.length <= 2) {
  showBanner();
  console.log(chalk.bold('  Quick Start:'));
  console.log(chalk.gray('  ────────────────────────'));
  console.log(`  ${chalk.cyan('kantorku init')}        ${chalk.gray('# Create a new project')}`);
  console.log(`  ${chalk.cyan('kantorku setup')}      ${chalk.gray('# Configure API keys')}`);
  console.log(`  ${chalk.cyan('kantorku serve')}      ${chalk.gray('# Start the backend')}`);
  console.log(`  ${chalk.cyan('kantorku chat')}       ${chalk.gray('# Start chatting')}`);
  console.log(`  ${chalk.cyan('kantorku status')}     ${chalk.gray('# Check system health')}`);
  console.log('');
  console.log(chalk.gray('  Run ') + chalk.cyan('kantorku --help') + chalk.gray(' for all commands.'));
  console.log('');
  process.exit(0);
}

// Parse
program.parse(process.argv);
