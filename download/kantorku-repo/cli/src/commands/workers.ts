import inquirer from 'inquirer';
import chalk from 'chalk';
import ora from 'ora';
import boxen from 'boxen';
import { KantorkuApi, WorkerInfo } from '../lib/api';
import { readConfig, loadEnv } from '../lib/config';

// ============================================================
// kantorku worker - Worker Management Commands
// ============================================================

export async function workerListCommand(): Promise<void> {
  const config = readConfig();
  loadEnv();

  const api = new KantorkuApi(config);

  console.log('');
  const spinner = ora('Fetching workers...').start();

  try {
    const workers = await api.listWorkers();
    spinner.stop();

    if (workers.length === 0) {
      console.log(
        boxen(
          chalk.yellow('  No Workers Found  ') + '\n\n' +
          chalk.gray('No workers are currently registered.') + '\n' +
          chalk.gray('Start the backend with ') + chalk.cyan('kantorku serve') +
          chalk.gray(' to initialize workers.'),
          {
            padding: 1,
            margin: 1,
            borderStyle: 'round',
            borderColor: 'yellow',
          }
        )
      );
      console.log('');
      return;
    }

    displayWorkerTable(workers);
  } catch (error) {
    spinner.stop();
    const err = error as Error;
    console.log(chalk.red(`\n  ✗ Error: ${err.message}`));
    console.log(chalk.gray('  Make sure the backend is running with: kantorku serve\n'));
  }
}

export async function workerShowCommand(workerId: string): Promise<void> {
  const config = readConfig();
  loadEnv();

  const api = new KantorkuApi(config);

  console.log('');
  const spinner = ora(`Fetching worker ${workerId}...`).start();

  try {
    const worker = await api.getWorker(workerId);
    spinner.stop();

    displayWorkerDetail(worker);
  } catch (error) {
    spinner.stop();
    const err = error as Error;
    console.log(chalk.red(`\n  ✗ Error: ${err.message}\n`));
  }
}

export async function workerStartCommand(workerId: string): Promise<void> {
  const config = readConfig();
  loadEnv();

  const api = new KantorkuApi(config);

  console.log('');
  const spinner = ora(`Starting worker ${workerId}...`).start();

  try {
    const result = await api.startWorker(workerId);
    spinner.succeed(chalk.green(`Worker ${chalk.white(workerId)} started`));
    console.log(chalk.gray(`  ${result.message}`));
    console.log('');
  } catch (error) {
    spinner.fail(chalk.red(`Failed to start worker ${workerId}`));
    const err = error as Error;
    console.log(chalk.red(`  ${err.message}\n`));
  }
}

export async function workerStopCommand(workerId: string): Promise<void> {
  const config = readConfig();
  loadEnv();

  const api = new KantorkuApi(config);

  console.log('');
  const spinner = ora(`Stopping worker ${workerId}...`).start();

  try {
    const result = await api.stopWorker(workerId);
    spinner.succeed(chalk.green(`Worker ${chalk.white(workerId)} stopped`));
    console.log(chalk.gray(`  ${result.message}`));
    console.log('');
  } catch (error) {
    spinner.fail(chalk.red(`Failed to stop worker ${workerId}`));
    const err = error as Error;
    console.log(chalk.red(`  ${err.message}\n`));
  }
}

function displayWorkerTable(workers: WorkerInfo[]): void {
  console.log(
    boxen(
      chalk.cyan.bold('  👷 Kantorku Workers  ') + '\n\n' +
      chalk.gray(`${workers.length} worker(s) registered`),
      {
        padding: 1,
        margin: 1,
        borderStyle: 'round',
        borderColor: 'cyan',
      }
    )
  );
  console.log('');

  // Table header
  const col1 = 'ID';
  const col2 = 'Name';
  const col3 = 'Role';
  const col4 = 'Status';
  const col5 = 'Provider';
  const col6 = 'Tasks';

  console.log(
    `  ${chalk.bold.gray(col1.padEnd(12))} ` +
    `${chalk.bold.gray(col2.padEnd(16))} ` +
    `${chalk.bold.gray(col3.padEnd(14))} ` +
    `${chalk.bold.gray(col4.padEnd(10))} ` +
    `${chalk.bold.gray(col5.padEnd(12))} ` +
    `${chalk.bold.gray(col6)}`
  );
  console.log(`  ${'─'.repeat(78)}`);

  for (const w of workers) {
    const statusIcon = getStatusIcon(w.status);
    const statusText = statusIcon + ' ' + w.status;

    console.log(
      `  ${chalk.white(w.id.padEnd(12))} ` +
      `${chalk.cyan(w.name.padEnd(16))} ` +
      `${chalk.gray(w.role.padEnd(14))} ` +
      `${statusText.padEnd(18)} ` +
      `${chalk.gray(w.provider.padEnd(12))} ` +
      `${chalk.green(String(w.tasks_completed))}${chalk.gray('/')}${chalk.red(String(w.tasks_failed))}`
    );
  }

  console.log('');
}

function displayWorkerDetail(worker: WorkerInfo): void {
  const statusColor = worker.status === 'idle' ? 'green' :
    worker.status === 'busy' ? 'yellow' :
    worker.status === 'error' ? 'red' : 'gray';

  const content = [
    chalk.bold.white(`  ${worker.name}`) + chalk.gray(` (${worker.id})`),
    '',
    `${chalk.gray('  Role:')}        ${chalk.white(worker.role)}`,
    `${chalk.gray('  Status:')}      ${(chalk as any)[statusColor](worker.status)} ${getStatusIcon(worker.status)}`,
    `${chalk.gray('  Provider:')}    ${chalk.white(worker.provider)}`,
    `${chalk.gray('  Model:')}       ${chalk.white(worker.model)}`,
    `${chalk.gray('  Completed:')}   ${chalk.green(String(worker.tasks_completed))}`,
    `${chalk.gray('  Failed:')}      ${chalk.red(String(worker.tasks_failed))}`,
    `${chalk.gray('  Last Active:')} ${chalk.white(worker.last_activity || 'Never')}`,
    '',
    `${chalk.gray('  Capabilities:')}`,
    ...(worker.capabilities || []).map((c) => `    ${chalk.cyan('•')} ${chalk.white(c)}`),
  ].join('\n');

  console.log(
    boxen(content, {
      padding: 1,
      margin: 1,
      borderStyle: 'round',
      borderColor: 'cyan',
    })
  );
  console.log('');
}

function getStatusIcon(status: string): string {
  switch (status) {
    case 'idle': return '🟢';
    case 'busy': return '🟡';
    case 'error': return '🔴';
    case 'offline': return '⚫';
    default: return '⚪';
  }
}
