import chalk from 'chalk';
import ora from 'ora';
import boxen from 'boxen';
import { KantorkuApi } from '../lib/api';
import { readConfig, loadEnv, getBackendUrl, readApiKeys, getApiKeyProviders, maskKey } from '../lib/config';

// ============================================================
// kantorku status - System Health Check
// ============================================================

export async function statusCommand(): Promise<void> {
  const config = readConfig();
  loadEnv();

  console.log('');
  console.log(
    boxen(
      chalk.cyan.bold('  🏥 Kantorku System Status  '),
      {
        padding: 1,
        margin: 0,
        borderStyle: 'round',
        borderColor: 'cyan',
      }
    )
  );
  console.log('');

  // Check backend health
  const api = new KantorkuApi(config);
  const backendSpinner = ora('Checking backend...').start();

  let backendStatus: 'online' | 'offline' | 'error' = 'offline';
  let systemInfo: any = null;

  try {
    systemInfo = await api.getStatus();
    backendStatus = systemInfo.status === 'running' ? 'online' : 'error';
    backendSpinner.succeed(chalk.green('Backend is online'));
  } catch {
    backendSpinner.fail(chalk.red('Backend is offline'));
  }

  console.log('');

  // Display system information
  console.log(chalk.bold('  🖥️  System Information'));
  console.log(chalk.gray('  ────────────────────────'));

  if (backendStatus === 'online' && systemInfo) {
    console.log(`  ${chalk.gray('Status:')}      ${chalk.green('● Running')}`);
    console.log(`  ${chalk.gray('Version:')}     ${chalk.white(systemInfo.version || 'unknown')}`);
    console.log(`  ${chalk.gray('Uptime:')}      ${chalk.white(formatUptime(systemInfo.uptime || 0))}`);
    console.log(`  ${chalk.gray('Backend URL:')} ${chalk.white(getBackendUrl(config))}`);
    console.log(`  ${chalk.gray('Office:')}      ${chalk.white(config.office.name)}`);
    console.log(`  ${chalk.gray('Conductor:')}   ${chalk.white(config.office.conductor_name)}`);

    // Workers
    console.log('');
    console.log(chalk.bold('  👷 Workers'));
    console.log(chalk.gray('  ────────────────────────'));

    const w = systemInfo.workers || {};
    console.log(`  ${chalk.gray('Total:')}   ${chalk.white(String(w.total || 0))}`);
    console.log(`  ${chalk.green('Active:')}  ${chalk.green(String(w.active || 0))}`);
    console.log(`  ${chalk.yellow('Idle:')}    ${chalk.yellow(String(w.idle || 0))}`);
    console.log(`  ${chalk.red('Error:')}   ${chalk.red(String(w.error || 0))}`);

    // Memory
    if (systemInfo.memory) {
      console.log('');
      console.log(chalk.bold('  💾 Memory'));
      console.log(chalk.gray('  ────────────────────────'));

      const m = systemInfo.memory;
      const usedPercent = m.total_mb > 0 ? Math.round((m.used_mb / m.total_mb) * 100) : 0;
      const bar = createProgressBar(usedPercent);

      console.log(`  ${chalk.gray('Used:')}  ${bar} ${chalk.white(`${m.used_mb}MB`)} / ${m.total_mb}MB`);
      console.log(`  ${chalk.gray('Free:')}  ${chalk.white(`${m.free_mb}MB`)}`);
    }
  } else {
    console.log(`  ${chalk.gray('Status:')}      ${chalk.red('● Offline')}`);
    console.log(`  ${chalk.gray('Backend URL:')} ${chalk.white(getBackendUrl(config))}`);
    console.log(`  ${chalk.gray('Office:')}      ${chalk.white(config.office.name)}`);
    console.log(`  ${chalk.gray('Conductor:')}   ${chalk.white(config.office.conductor_name)}`);

    console.log('');
    console.log(chalk.yellow('  ⚠  Backend is not running'));
    console.log(chalk.gray('  Start it with: ') + chalk.cyan('kantorku serve'));
  }

  // API Keys status
  console.log('');
  console.log(chalk.bold('  🔑 API Keys'));
  console.log(chalk.gray('  ────────────────────────'));

  const apiKeys = readApiKeys();
  const providers = getApiKeyProviders();
  let configuredCount = 0;

  for (const provider of providers) {
    const value = (apiKeys as any)[provider.key];
    if (value) {
      configuredCount++;
      console.log(
        `  ${chalk.green('✓')} ${chalk.white(provider.label.padEnd(16))} ${chalk.gray(provider.masked ? maskKey(value) : value)}`
      );
    } else {
      console.log(
        `  ${chalk.gray('○')} ${chalk.gray(provider.label.padEnd(16))} ${chalk.gray('not configured')}`
      );
    }
  }

  console.log(
    chalk.gray(`\n  ${configuredCount}/${providers.length} providers configured`)
  );

  if (configuredCount === 0) {
    console.log(chalk.yellow('  ⚠  No API keys configured'));
    console.log(chalk.gray('  Run ') + chalk.cyan('kantorku setup') + chalk.gray(' to configure'));
  }

  // Configuration
  console.log('');
  console.log(chalk.bold('  ⚙️  Configuration'));
  console.log(chalk.gray('  ────────────────────────'));

  console.log(`  ${chalk.gray('LLM Provider:')}  ${chalk.white(config.llm.default_provider)}`);
  console.log(`  ${chalk.gray('LLM Model:')}     ${chalk.white(config.llm.default_model)}`);
  console.log(`  ${chalk.gray('Temperature:')}   ${chalk.white(String(config.llm.temperature))}`);
  console.log(`  ${chalk.gray('Max Tokens:')}    ${chalk.white(String(config.llm.max_tokens))}`);
  console.log(`  ${chalk.gray('Max Workers:')}   ${chalk.white(String(config.office.max_workers))}`);

  console.log('');

  // Overall health score
  const healthScore = calculateHealthScore(backendStatus, configuredCount, providers.length);
  const healthColor = healthScore >= 80 ? 'green' : healthScore >= 50 ? 'yellow' : 'red';
  const healthLabel = healthScore >= 80 ? 'Healthy' : healthScore >= 50 ? 'Needs Attention' : 'Not Configured';

  console.log(
    boxen(
      `  Overall Health: ${(chalk as any)[healthColor](`${healthScore}% - ${healthLabel}`)}  `,
      {
        padding: 0,
        margin: 1,
        borderStyle: 'round',
        borderColor: healthColor,
      }
    )
  );
  console.log('');
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
}

function createProgressBar(percent: number, width: number = 20): string {
  const filled = Math.round((percent / 100) * width);
  const empty = width - filled;

  const bar =
    chalk.green('█'.repeat(Math.min(filled, width))) +
    chalk.gray('░'.repeat(empty));

  return bar;
}

function calculateHealthScore(
  backendStatus: string,
  configuredKeys: number,
  totalProviders: number
): number {
  let score = 0;

  // Backend health (40 points)
  if (backendStatus === 'online') score += 40;
  else if (backendStatus === 'error') score += 10;

  // API keys configured (40 points)
  const keyRatio = configuredKeys / totalProviders;
  score += Math.round(keyRatio * 40);

  // At least one key means basic functionality (20 points)
  if (configuredKeys >= 1) score += 20;

  return Math.min(100, score);
}
