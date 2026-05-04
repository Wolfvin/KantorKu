import * as readline from 'readline';
import chalk from 'chalk';
import boxen from 'boxen';
import ora from 'ora';
import WebSocket from 'ws';
import { KantorkuApi } from '../lib/api';
import { readConfig, getWebSocketUrl, loadEnv, getBackendUrl } from '../lib/config';

// ============================================================
// kantorku chat - Interactive Chat with the Office Conductor
// ============================================================

interface ChatOptions {
  websocket?: boolean;
  worker?: string;
}

export async function chatCommand(options: ChatOptions = {}): Promise<void> {
  const config = readConfig();
  loadEnv();

  console.log('');
  console.log(
    boxen(
      chalk.cyan.bold(`  💬 ${config.office.name} - Chat  `) + '\n\n' +
      chalk.gray(`Talking to ${chalk.white(config.office.conductor_name)} (Conductor)`) + '\n' +
      chalk.gray('Type ') + chalk.yellow('/help') + chalk.gray(' for commands, ') +
      chalk.yellow('/quit') + chalk.gray(' to exit'),
      {
        padding: 1,
        margin: 0,
        borderStyle: 'round',
        borderColor: 'cyan',
      }
    )
  );
  console.log('');

  const api = new KantorkuApi(config);
  let useWebSocket = options.websocket || false;
  let conversationId = `cli-${Date.now()}`;
  let ws: WebSocket | null = null;
  let messageHistory: Array<{ role: string; content: string }> = [];

  // Try WebSocket connection if requested
  if (useWebSocket) {
    try {
      ws = await connectWebSocket(getWebSocketUrl(config), conversationId);
      console.log(chalk.green('  ✓ Connected via WebSocket'));
      console.log('');
    } catch (error) {
      console.log(chalk.yellow('  ⚠ WebSocket connection failed, falling back to HTTP'));
      console.log('');
      useWebSocket = false;
    }
  }

  // Check if backend is reachable
  if (!useWebSocket) {
    const spinner = ora('Checking backend connection...').start();
    const healthy = await api.isHealthy();
    if (healthy) {
      spinner.succeed(chalk.green('Connected to backend'));
    } else {
      spinner.warn(chalk.yellow('Backend not reachable - using local chat mode'));
    }
    console.log('');
  }

  // Setup readline
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: chalk.cyan('  You > '),
  });

  rl.prompt();

  rl.on('line', async (line) => {
    const input = line.trim();

    if (!input) {
      rl.prompt();
      return;
    }

    // Handle commands
    if (input.startsWith('/')) {
      const handled = handleCommand(input, rl, ws, messageHistory, config);
      if (handled === 'quit') {
        cleanup(ws, rl);
        return;
      }
      rl.prompt();
      return;
    }

    // Send message
    if (useWebSocket && ws && ws.readyState === WebSocket.OPEN) {
      sendWebSocketMessage(ws, input, conversationId, options.worker);
    } else {
      await sendHttpMessage(api, input, conversationId, options.worker, messageHistory);
    }

    rl.prompt();
  });

  rl.on('close', () => {
    cleanup(ws, rl);
  });

  // Handle WebSocket messages
  if (ws) {
    ws.on('message', (data: WebSocket.Data) => {
      try {
        const msg = JSON.parse(data.toString());
        displayAssistantMessage(msg.content || msg.message || '', msg.worker_id);
      } catch {
        // Plain text message
        displayAssistantMessage(data.toString());
      }
      rl.prompt();
    });

    ws.on('error', (err) => {
      console.log(chalk.red(`\n  WebSocket error: ${err.message}`));
      rl.prompt();
    });

    ws.on('close', () => {
      console.log(chalk.yellow('\n  WebSocket connection closed'));
      rl.prompt();
    });
  }
}

function connectWebSocket(url: string, conversationId: string): Promise<WebSocket> {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);

    const timeout = setTimeout(() => {
      ws.close();
      reject(new Error('Connection timeout'));
    }, 5000);

    ws.on('open', () => {
      clearTimeout(timeout);
      // Send initial handshake
      ws.send(JSON.stringify({
        type: 'join',
        conversation_id: conversationId,
        source: 'cli',
      }));
      resolve(ws);
    });

    ws.on('error', (err) => {
      clearTimeout(timeout);
      reject(err);
    });
  });
}

function sendWebSocketMessage(
  ws: WebSocket,
  message: string,
  conversationId: string,
  workerId?: string
): void {
  ws.send(JSON.stringify({
    type: 'message',
    conversation_id: conversationId,
    content: message,
    worker_id: workerId,
  }));
}

async function sendHttpMessage(
  api: KantorkuApi,
  message: string,
  conversationId: string,
  workerId?: string,
  history?: Array<{ role: string; content: string }>
): Promise<void> {
  const spinner = ora({ text: 'Thinking...', spinner: 'dots' }).start();

  try {
    const response = await api.chat(message, conversationId);
    spinner.stop();

    const content = response.message?.content || response.message?.toString() || 'No response';
    displayAssistantMessage(content, response.worker_used);

    if (history) {
      history.push({ role: 'user', content: message });
      history.push({ role: 'assistant', content });
    }
  } catch (error) {
    spinner.stop();

    const err = error as Error;
    if (err.message.includes('Cannot connect') || err.message.includes('ECONNREFUSED')) {
      console.log(chalk.yellow('\n  ⚠ Backend not available. Using local response mode.'));
      console.log(chalk.gray('  Start the backend with: kantorku serve'));
      displayAssistantMessage(
        `I'm sorry, I can't reach the backend right now. Please start the Kantorku backend first using \`kantorku serve\`.`,
        undefined
      );
    } else {
      console.log(chalk.red(`\n  ✗ Error: ${err.message}`));
    }
  }
}

function displayAssistantMessage(content: string, workerId?: string): void {
  const prefix = workerId
    ? chalk.magenta(`  ${workerId} > `)
    : chalk.green('  Conductor > ');

  // Word-wrap the content
  const wrapped = wrapText(content, 70);

  console.log('');
  console.log(prefix + wrapped.split('\n').join('\n' + ' '.repeat(prefix.length - 10)));
  console.log('');
}

function wrapText(text: string, width: number): string {
  const words = text.split(' ');
  const lines: string[] = [];
  let currentLine = '';

  for (const word of words) {
    if (currentLine.length + word.length + 1 > width) {
      lines.push(currentLine);
      currentLine = word;
    } else {
      currentLine = currentLine ? `${currentLine} ${word}` : word;
    }
  }
  if (currentLine) lines.push(currentLine);

  return lines.join('\n');
}

type CommandResult = 'continue' | 'quit';

function handleCommand(
  input: string,
  rl: readline.Interface,
  ws: WebSocket | null,
  history: Array<{ role: string; content: string }>,
  config: ReturnType<typeof readConfig>
): CommandResult {
  const parts = input.split(' ');
  const cmd = parts[0].toLowerCase();
  const args = parts.slice(1);

  switch (cmd) {
    case '/help':
      console.log('');
      console.log(chalk.bold('  Available Commands:'));
      console.log(chalk.gray('  ────────────────────────'));
      console.log(`  ${chalk.yellow('/help')}          Show this help message`);
      console.log(`  ${chalk.yellow('/quit')}          Exit chat mode`);
      console.log(`  ${chalk.yellow('/clear')}         Clear conversation history`);
      console.log(`  ${chalk.yellow('/history')}       Show conversation history`);
      console.log(`  ${chalk.yellow('/worker <id>')}   Send next message to specific worker`);
      console.log(`  ${chalk.yellow('/status')}        Show system status`);
      console.log(`  ${chalk.yellow('/workers')}       List active workers`);
      console.log('');
      return 'continue';

    case '/quit':
    case '/exit':
      console.log(chalk.gray('\n  Goodbye! 👋\n'));
      return 'quit';

    case '/clear':
      history.length = 0;
      console.log(chalk.green('\n  ✓ Conversation history cleared\n'));
      return 'continue';

    case '/history':
      if (history.length === 0) {
        console.log(chalk.gray('\n  No conversation history\n'));
      } else {
        console.log('');
        for (const msg of history) {
          const prefix = msg.role === 'user'
            ? chalk.cyan('  You > ')
            : chalk.green('  Conductor > ');
          console.log(prefix + msg.content);
        }
        console.log('');
      }
      return 'continue';

    case '/status':
      console.log(chalk.gray(`\n  Office: ${config.office.name}`));
      console.log(chalk.gray(`  Conductor: ${config.office.conductor_name}`));
      console.log(chalk.gray(`  Backend: ${getBackendUrl(config)}`));
      console.log(chalk.gray(`  Messages: ${history.length}`));
      console.log(chalk.gray(`  WebSocket: ${ws ? 'connected' : 'disconnected'}\n`));
      return 'continue';

    case '/workers':
      (async () => {
        const api = new KantorkuApi(config);
        const spinner = ora('Fetching workers...').start();
        try {
          const workers = await api.listWorkers();
          spinner.stop();
          if (workers.length === 0) {
            console.log(chalk.gray('\n  No workers found\n'));
          } else {
            console.log('');
            for (const w of workers) {
              const statusIcon = w.status === 'idle' ? chalk.green('●') :
                w.status === 'busy' ? chalk.yellow('●') :
                w.status === 'error' ? chalk.red('●') : chalk.gray('○');
              console.log(`  ${statusIcon} ${chalk.white(w.name)} (${w.id}) - ${chalk.gray(w.role)}`);
            }
            console.log('');
          }
        } catch {
          spinner.stop();
          console.log(chalk.yellow('\n  Could not fetch workers - backend may be offline\n'));
        }
      })();
      return 'continue';

    default:
      console.log(chalk.yellow(`\n  Unknown command: ${cmd}. Type /help for available commands.\n`));
      return 'continue';
  }
}

function cleanup(ws: WebSocket | null, rl: readline.Interface): void {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close();
  }
  rl.close();
  process.exit(0);
}
