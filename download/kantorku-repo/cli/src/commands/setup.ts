import inquirer from 'inquirer';
import chalk from 'chalk';
import ora from 'ora';
import boxen from 'boxen';
import {
  readApiKeys,
  writeApiKeys,
  readConfig,
  writeConfig,
  getApiKeyProviders,
  maskKey,
  KantorkuConfig,
  ApiKeys,
} from '../lib/config';

// ============================================================
// kantorku setup - Interactive API Key Configuration Wizard
// ============================================================

export async function setupCommand(): Promise<void> {
  console.log('');
  console.log(
    boxen(
      chalk.cyan.bold('  🔧 Kantorku Setup Wizard  ') + '\n\n' +
      chalk.gray('Configure your API keys and settings'),
      {
        padding: 1,
        margin: 0,
        borderStyle: 'round',
        borderColor: 'cyan',
      }
    )
  );
  console.log('');

  // Step 1: Configure API keys
  const apiKeys = await configureApiKeys();

  // Step 2: Configure office settings
  const officeConfig = await configureOffice();

  // Step 3: Configure LLM defaults
  const llmConfig = await configureLLM();

  // Step 4: Save everything
  const spinner = ora('Saving configuration...').start();

  try {
    writeApiKeys(apiKeys);

    const currentConfig = readConfig();
    const newConfig: KantorkuConfig = {
      ...currentConfig,
      office: officeConfig,
      llm: llmConfig,
    };
    writeConfig(newConfig);

    spinner.succeed(chalk.green('Configuration saved successfully!'));
  } catch (error) {
    spinner.fail(chalk.red('Failed to save configuration'));
    throw error;
  }

  // Summary
  console.log('');
  console.log(chalk.bold('  📋 Configuration Summary:'));
  console.log(chalk.gray('  ─────────────────────────'));

  const providers = getApiKeyProviders();
  for (const provider of providers) {
    const value = (apiKeys as any)[provider.key];
    if (value) {
      console.log(
        `  ${chalk.green('✓')} ${chalk.white(provider.label)}: ${chalk.gray(provider.masked ? maskKey(value) : value)}`
      );
    } else {
      console.log(`  ${chalk.yellow('○')} ${chalk.white(provider.label)}: ${chalk.gray('not configured')}`);
    }
  }

  console.log('');
  console.log(chalk.gray(`  Office: ${officeConfig.name} (Conductor: ${officeConfig.conductor_name})`));
  console.log(chalk.gray(`  LLM: ${llmConfig.default_provider}/${llmConfig.default_model}`));
  console.log('');
}

async function configureApiKeys(): Promise<ApiKeys> {
  console.log(chalk.bold.cyan('\n  Step 1: API Key Configuration'));
  console.log(chalk.gray('  Enter your API keys for the LLM providers you want to use.'));
  console.log(chalk.gray('  Press Enter to skip a provider.\n'));

  const existingKeys = readApiKeys();
  const providers = getApiKeyProviders();
  const keys: ApiKeys = {};

  for (const provider of providers) {
    const existing = (existingKeys as any)[provider.key] as string | undefined;
    const defaultDisplay = existing
      ? provider.masked
        ? maskKey(existing)
        : existing
      : undefined;

    const { value } = await inquirer.prompt<{ value: string }>([
      {
        type: provider.masked ? 'password' : 'input',
        name: 'value',
        message: `${provider.label} API Key${defaultDisplay ? ` (current: ${defaultDisplay})` : ''}:`,
        default: undefined,
      },
    ]);

    if (value && value.trim()) {
      (keys as any)[provider.key] = value.trim();
    } else if (existing) {
      // Keep existing key if user just pressed Enter
      (keys as any)[provider.key] = existing;
    }
  }

  return keys;
}

async function configureOffice(): Promise<KantorkuConfig['office']> {
  console.log(chalk.bold.cyan('\n  Step 2: Office Configuration'));
  console.log(chalk.gray('  Customize your Kantorku office.\n'));

  const currentConfig = readConfig();

  const answers = await inquirer.prompt([
    {
      type: 'input',
      name: 'name',
      message: 'Office name:',
      default: currentConfig.office.name,
    },
    {
      type: 'input',
      name: 'conductor_name',
      message: 'Conductor (Manager) name:',
      default: currentConfig.office.conductor_name,
    },
    {
      type: 'number',
      name: 'max_workers',
      message: 'Maximum number of workers:',
      default: currentConfig.office.max_workers,
    },
  ]);

  return {
    name: answers.name,
    conductor_name: answers.conductor_name,
    max_workers: answers.max_workers,
  };
}

async function configureLLM(): Promise<KantorkuConfig['llm']> {
  console.log(chalk.bold.cyan('\n  Step 3: LLM Configuration'));
  console.log(chalk.gray('  Set your default LLM provider and model.\n'));

  const currentConfig = readConfig();

  const answers = await inquirer.prompt([
    {
      type: 'list',
      name: 'default_provider',
      message: 'Default LLM provider:',
      choices: [
        { name: 'OpenAI', value: 'openai' },
        { name: 'Anthropic', value: 'anthropic' },
        { name: 'Google / Vertex AI', value: 'google' },
        { name: 'DeepSeek', value: 'deepseek' },
        { name: 'MiniMax', value: 'minimax' },
        { name: 'xAI (Grok)', value: 'xai' },
        { name: 'Ollama (Local)', value: 'ollama' },
        { name: 'Z-AI SDK', value: 'zai' },
      ],
      default: currentConfig.llm.default_provider,
    },
    {
      type: 'input',
      name: 'default_model',
      message: 'Default model:',
      default: currentConfig.llm.default_model,
    },
    {
      type: 'number',
      name: 'temperature',
      message: 'Temperature (0.0 - 2.0):',
      default: currentConfig.llm.temperature,
    },
    {
      type: 'number',
      name: 'max_tokens',
      message: 'Max tokens:',
      default: currentConfig.llm.max_tokens,
    },
  ]);

  return {
    default_provider: answers.default_provider,
    default_model: answers.default_model,
    temperature: answers.temperature,
    max_tokens: answers.max_tokens,
  };
}
