import * as fs from 'fs';
import * as path from 'path';
import inquirer from 'inquirer';
import chalk from 'chalk';
import ora from 'ora';
import boxen from 'boxen';
import { writeConfig, writeApiKeys, KantorkuConfig, ApiKeys } from '../lib/config';

// ============================================================
// kantorku init - Project Scaffolding
// ============================================================

interface InitOptions {
  name?: string;
  template?: string;
  provider?: string;
}

const TEMPLATES = [
  {
    name: 'Basic Office',
    value: 'basic',
    description: 'A simple office with one Conductor and basic workers',
  },
  {
    name: 'Full Office',
    value: 'full',
    description: 'A full office with Conductor, Manager, and specialized workers',
  },
  {
    name: 'Custom',
    value: 'custom',
    description: 'Customize your office configuration from scratch',
  },
];

export async function initCommand(options: InitOptions = {}): Promise<void> {
  console.log('');
  console.log(
    boxen(
      chalk.cyan.bold('  🏗️  Kantorku Project Init  ') + '\n\n' +
      chalk.gray('Scaffold a new Kantorku project'),
      {
        padding: 1,
        margin: 0,
        borderStyle: 'round',
        borderColor: 'cyan',
      }
    )
  );
  console.log('');

  // Get project name
  let projectName = options.name;
  if (!projectName) {
    const answers = await inquirer.prompt<{ name: string }>([
      {
        type: 'input',
        name: 'name',
        message: 'Project name:',
        default: 'my-kantorku-office',
        validate: (input: string) => {
          if (!input.trim()) return 'Project name is required';
          if (!/^[a-z0-9-_]+$/.test(input.trim())) {
            return 'Project name must be lowercase alphanumeric with dashes or underscores';
          }
          return true;
        },
      },
    ]);
    projectName = answers.name.trim();
  }

  // Get template
  let template = options.template;
  if (!template) {
    const answers = await inquirer.prompt<{ template: string }>([
      {
        type: 'list',
        name: 'template',
        message: 'Choose a template:',
        choices: TEMPLATES.map((t) => ({
          name: `${t.name} - ${chalk.gray(t.description)}`,
          value: t.value,
        })),
        default: 'basic',
      },
    ]);
    template = answers.template;
  }

  // Get LLM provider
  let provider = options.provider;
  if (!provider) {
    const answers = await inquirer.prompt<{ provider: string }>([
      {
        type: 'list',
        name: 'provider',
        message: 'Default LLM provider:',
        choices: [
          { name: 'OpenAI', value: 'openai' },
          { name: 'Anthropic', value: 'anthropic' },
          { name: 'Google / Vertex AI', value: 'google' },
          { name: 'DeepSeek', value: 'deepseek' },
          { name: 'Ollama (Local)', value: 'ollama' },
        ],
        default: 'openai',
      },
    ]);
    provider = answers.provider;
  }

  // Create project directory
  const projectDir = path.join(process.cwd(), projectName);

  if (fs.existsSync(projectDir)) {
    console.log(chalk.red(`\n  ✗ Directory "${projectName}" already exists.\n`));
    return;
  }

  const spinner = ora(`Creating project ${projectName}...`).start();

  try {
    // Create directory structure
    fs.mkdirSync(projectDir, { recursive: true });
    fs.mkdirSync(path.join(projectDir, 'workers'), { recursive: true });
    fs.mkdirSync(path.join(projectDir, 'logs'), { recursive: true });
    fs.mkdirSync(path.join(projectDir, 'data'), { recursive: true });

    // Generate config based on template
    const config = generateConfig(projectName, template, provider);
    writeConfig(config, projectDir);

    // Generate .env file
    const envKeys = generateEnvTemplate(provider);
    writeApiKeys(envKeys, projectDir);

    // Generate worker files based on template
    generateWorkerFiles(projectDir, template, config);

    // Generate README
    generateReadme(projectDir, projectName, template, config);

    // Generate .gitignore
    generateGitignore(projectDir);

    // Generate main.py (backend)
    generateBackend(projectDir, config);

    spinner.succeed(chalk.green(`Project ${chalk.white(projectName)} created successfully!`));

    // Show next steps
    console.log('');
    console.log(chalk.bold('  📁 Project Structure:'));
    console.log(chalk.gray('  ────────────────────────'));
    console.log(`  ${chalk.white(projectName)}/`);
    console.log(`  ├── ${chalk.cyan('kantorku.toml')}      ${chalk.gray('# Configuration')}`);
    console.log(`  ├── ${chalk.cyan('.env')}              ${chalk.gray('# API keys')}`);
    console.log(`  ├── ${chalk.cyan('main.py')}           ${chalk.gray('# Backend server')}`);
    console.log(`  ├── ${chalk.cyan('workers/')}`);
    console.log(`  │   ├── ${chalk.cyan('conductor.py')}  ${chalk.gray('# Office conductor')}`);

    if (template === 'full') {
      console.log(`  │   ├── ${chalk.cyan('manager.py')}    ${chalk.gray('# Task manager')}`);
      console.log(`  │   ├── ${chalk.cyan('researcher.py')} ${chalk.gray('# Research worker')}`);
      console.log(`  │   └── ${chalk.cyan('writer.py')}     ${chalk.gray('# Writing worker')}`);
    }

    console.log(`  ├── ${chalk.cyan('logs/')}`);
    console.log(`  ├── ${chalk.cyan('data/')}`);
    console.log(`  ├── ${chalk.cyan('README.md')}`);
    console.log(`  └── ${chalk.cyan('.gitignore')}`);
    console.log('');

    console.log(chalk.bold('  🚀 Next Steps:'));
    console.log(chalk.gray('  ────────────────────────'));
    console.log(`  1. ${chalk.white(`cd ${projectName}`)}`);
    console.log(`  2. ${chalk.white('kantorku setup')}       ${chalk.gray('# Configure API keys')}`);
    console.log(`  3. ${chalk.white('kantorku serve')}       ${chalk.gray('# Start the backend')}`);
    console.log(`  4. ${chalk.white('kantorku chat')}        ${chalk.gray('# Start chatting')}`);
    console.log('');
  } catch (error) {
    spinner.fail(chalk.red('Failed to create project'));
    // Cleanup on failure
    if (fs.existsSync(projectDir)) {
      fs.rmSync(projectDir, { recursive: true, force: true });
    }
    throw error;
  }
}

function generateConfig(
  projectName: string,
  template: string,
  provider: string
): KantorkuConfig {
  const baseConfig: KantorkuConfig = {
    backend: {
      host: '127.0.0.1',
      port: 8000,
      workers_dir: './workers',
      log_level: 'info',
    },
    frontend: {
      host: '127.0.0.1',
      port: 3000,
    },
    llm: {
      default_provider: provider,
      default_model: getDefaultModel(provider),
      temperature: 0.7,
      max_tokens: 4096,
    },
    office: {
      name: projectName.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
      conductor_name: 'Pak Raden',
      max_workers: template === 'full' ? 10 : 5,
    },
  };

  return baseConfig;
}

function getDefaultModel(provider: string): string {
  const models: Record<string, string> = {
    openai: 'gpt-4o',
    anthropic: 'claude-sonnet-4-20250514',
    google: 'gemini-2.0-flash',
    deepseek: 'deepseek-chat',
    minimax: 'minimax-01',
    xai: 'grok-3',
    ollama: 'llama3.2',
    zai: 'default',
  };
  return models[provider] || 'gpt-4o';
}

function generateEnvTemplate(provider: string): ApiKeys {
  const keys: ApiKeys = {};
  // Only add a placeholder for the selected provider
  (keys as any)[provider === 'google' ? 'google' : provider] = 'your-api-key-here';
  return keys;
}

function generateWorkerFiles(
  projectDir: string,
  template: string,
  config: KantorkuConfig
): void {
  const workersDir = path.join(projectDir, 'workers');

  // Always create conductor
  const conductorCode = `"""
${config.office.conductor_name} - The Conductor Worker
The main coordinator of the Kantorku office.
"""
import json
import time


class Conductor:
    """The Conductor manages the office and delegates tasks to workers."""

    def __init__(self, name="${config.office.conductor_name}"):
        self.name = name
        self.role = "conductor"
        self.status = "idle"
        self.tasks_completed = 0

    def greet(self):
        return f"Hello! I am {self.name}, the Conductor of this office. How can I help you today?"

    def process_message(self, message: str) -> str:
        """Process an incoming message and return a response."""
        self.status = "busy"
        try:
            # Simple response logic
            response = self._generate_response(message)
            self.tasks_completed += 1
            return response
        finally:
            self.status = "idle"

    def _generate_response(self, message: str) -> str:
        """Generate a response to the given message."""
        message_lower = message.lower()

        if "hello" in message_lower or "hi" in message_lower:
            return self.greet()
        elif "status" in message_lower:
            return f"Office status: All systems operational. I have completed {self.tasks_completed} tasks."
        elif "help" in message_lower:
            return "I can help you with task delegation, worker management, and office coordination. What do you need?"
        else:
            return f"I received your message: '{message}'. Let me process that and get back to you."


# Worker registration
WORKER_INFO = {
    "id": "conductor",
    "name": "${config.office.conductor_name}",
    "role": "conductor",
    "provider": "${config.llm.default_provider}",
    "model": "${config.llm.default_model}",
    "capabilities": ["coordination", "delegation", "communication"],
}


if __name__ == "__main__":
    conductor = Conductor()
    print(conductor.greet())
`;

  fs.writeFileSync(path.join(workersDir, 'conductor.py'), conductorCode, 'utf-8');

  if (template === 'full') {
    // Manager worker
    const managerCode = `"""
Manager Worker - Task Management Specialist
Handles task decomposition and assignment.
"""


class Manager:
    """The Manager breaks down tasks and assigns them to workers."""

    def __init__(self):
        self.name = "Bu Sari"
        self.role = "manager"
        self.status = "idle"
        self.tasks_completed = 0

    def decompose_task(self, task: str) -> list:
        """Break down a task into subtasks."""
        self.status = "busy"
        try:
            # Simple decomposition
            subtasks = [
                {"id": 1, "description": f"Analyze: {task}", "assignee": "researcher"},
                {"id": 2, "description": f"Process: {task}", "assignee": "writer"},
                {"id": 3, "description": f"Review: {task}", "assignee": "conductor"},
            ]
            self.tasks_completed += 1
            return subtasks
        finally:
            self.status = "idle"


WORKER_INFO = {
    "id": "manager",
    "name": "Bu Sari",
    "role": "manager",
    "provider": "${config.llm.default_provider}",
    "model": "${config.llm.default_model}",
    "capabilities": ["task_decomposition", "assignment", "planning"],
}
`;
    fs.writeFileSync(path.join(workersDir, 'manager.py'), managerCode, 'utf-8');

    // Researcher worker
    const researcherCode = `"""
Researcher Worker - Information Gathering Specialist
Handles research and information retrieval tasks.
"""


class Researcher:
    """The Researcher gathers and analyzes information."""

    def __init__(self):
        self.name = "Mas Budi"
        self.role = "researcher"
        self.status = "idle"
        self.tasks_completed = 0

    def research(self, query: str) -> dict:
        """Research a given topic."""
        self.status = "busy"
        try:
            result = {
                "query": query,
                "findings": f"Research results for: {query}",
                "confidence": 0.85,
            }
            self.tasks_completed += 1
            return result
        finally:
            self.status = "idle"


WORKER_INFO = {
    "id": "researcher",
    "name": "Mas Budi",
    "role": "researcher",
    "provider": "${config.llm.default_provider}",
    "model": "${config.llm.default_model}",
    "capabilities": ["research", "analysis", "information_retrieval"],
}
`;
    fs.writeFileSync(path.join(workersDir, 'researcher.py'), researcherCode, 'utf-8');

    // Writer worker
    const writerCode = `"""
Writer Worker - Content Creation Specialist
Handles writing and content generation tasks.
"""


class Writer:
    """The Writer creates and edits content."""

    def __init__(self):
        self.name = "Mba Dewi"
        self.role = "writer"
        self.status = "idle"
        self.tasks_completed = 0

    def write(self, prompt: str, context: str = "") -> str:
        """Generate written content based on a prompt."""
        self.status = "busy"
        try:
            content = f"Generated content for: {prompt}"
            if context:
                content += f"\\nBased on context: {context}"
            self.tasks_completed += 1
            return content
        finally:
            self.status = "idle"


WORKER_INFO = {
    "id": "writer",
    "name": "Mba Dewi",
    "role": "writer",
    "provider": "${config.llm.default_provider}",
    "model": "${config.llm.default_model}",
    "capabilities": ["writing", "editing", "summarization", "translation"],
}
`;
    fs.writeFileSync(path.join(workersDir, 'writer.py'), writerCode, 'utf-8');
  }

  // Create __init__.py
  fs.writeFileSync(
    path.join(workersDir, '__init__.py'),
    '# Kantorku Workers Package\n',
    'utf-8'
  );
}

function generateReadme(
  projectDir: string,
  projectName: string,
  template: string,
  config: KantorkuConfig
): void {
  const content = `# ${config.office.name}

> A Kantorku AI Office powered by ${config.llm.default_provider}

## Overview

This is a Kantorku office project with a **${template}** template configuration.

- **Conductor**: ${config.office.conductor_name}
- **Default Provider**: ${config.llm.default_provider}
- **Default Model**: ${config.llm.default_model}

## Quick Start

1. Configure your API keys:
   \`\`\`bash
   kantorku setup
   \`\`\`

2. Start the backend:
   \`\`\`bash
   kantorku serve
   \`\`\`

3. Start chatting:
   \`\`\`bash
   kantorku chat
   \`\`\`

## Commands

| Command | Description |
|---------|-------------|
| \`kantorku setup\` | Configure API keys and settings |
| \`kantorku serve\` | Start the Python backend |
| \`kantorku dev\` | Start the Next.js interface |
| \`kantorku chat\` | Interactive chat with the office |
| \`kantorku worker list\` | List all workers |
| \`kantorku status\` | Show system health |
| \`kantorku init\` | Create a new project |

## Project Structure

\`\`\`
${projectName}/
├── kantorku.toml      # Configuration
├── .env               # API keys (do not commit!)
├── main.py            # Backend server
├── workers/           # Worker modules
│   └── conductor.py   # Office conductor
├── logs/              # Application logs
├── data/              # Data storage
└── README.md          # This file
\`\`\`

## Configuration

Edit \`kantorku.toml\` to customize your office settings.

## License

MIT
`;

  fs.writeFileSync(path.join(projectDir, 'README.md'), content, 'utf-8');
}

function generateGitignore(projectDir: string): void {
  const content = `# Environment variables
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/
venv/
.venv/

# Logs
logs/*.log
*.log

# Data
data/*.db
data/*.sqlite

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo
`;

  fs.writeFileSync(path.join(projectDir, '.gitignore'), content, 'utf-8');
}

function generateBackend(projectDir: string, config: KantorkuConfig): void {
  const workers = config.office.name.toLowerCase().includes('full')
    ? ['conductor', 'manager', 'researcher', 'writer']
    : ['conductor'];

  const workerImports = workers
    .map((w) => `from workers.${w} import WORKER_INFO as ${w}_info`)
    .join('\n');

  const workerDict = workers
    .map((w) => `    "${w}": ${w}_info,`)
    .join('\n');

  const content = `#!/usr/bin/env python3
"""
${config.office.name} - Kantorku Backend Server
"""
import os
import sys
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Import workers
${workerImports}

WORKERS = {
${workerDict}
}

class KantorkuHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Kantorku backend."""

    start_time = time.time()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self.send_json({"status": "healthy", "uptime": time.time() - self.start_time})

        elif parsed.path == "/api/status":
            self.send_json({
                "status": "running",
                "uptime": time.time() - self.start_time,
                "version": "1.0.0",
                "workers": {
                    "total": len(WORKERS),
                    "active": 0,
                    "idle": len(WORKERS),
                    "error": 0
                },
                "memory": {"total_mb": 512, "used_mb": 64, "free_mb": 448},
                "backend_url": f"http://{self.server.server_address[0]}:{self.server.server_address[1]}"
            })

        elif parsed.path == "/api/workers":
            self.send_json({"workers": list(WORKERS.values())})

        elif parsed.path.startswith("/api/workers/") and not parsed.path.endswith("/start") and not parsed.path.endswith("/stop"):
            worker_id = parsed.path.split("/")[-1]
            if worker_id in WORKERS:
                self.send_json(WORKERS[worker_id])
            else:
                self.send_json({"error": f"Worker {worker_id} not found"}, 404)

        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"

        if parsed.path == "/api/chat":
            try:
                data = json.loads(body)
                message = data.get("message", "")
                worker_id = data.get("worker_id")

                # Use conductor by default
                response_content = f"Hello! I am ${config.office.conductor_name}, the Conductor of ${config.office.name}. I received your message: '{message}'"

                if worker_id and worker_id in WORKERS:
                    worker = WORKERS[worker_id]
                    response_content = f"[{worker['name']}] I received your message: '{message}'"

                self.send_json({
                    "message": {
                        "role": "assistant",
                        "content": response_content,
                        "timestamp": time.time()
                    },
                    "worker_used": worker_id or "conductor",
                    "tokens_used": 0
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 400)

        elif parsed.path.startswith("/api/workers/") and parsed.path.endswith("/start"):
            worker_id = parsed.path.split("/")[3]
            self.send_json({"message": f"Worker {worker_id} started"})

        elif parsed.path.startswith("/api/workers/") and parsed.path.endswith("/stop"):
            worker_id = parsed.path.split("/")[3]
            self.send_json({"message": f"Worker {worker_id} stopped"})

        else:
            self.send_json({"error": "Not found"}, 404)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        print(f"[Kantorku] {args[0]}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="${config.office.name} Backend")
    parser.add_argument("--host", default="${config.backend.host}", help="Host to bind to")
    parser.add_argument("--port", type=int, default=${config.backend.port}, help="Port to bind to")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), KantorkuHandler)
    print(f"🏠 ${config.office.name} running on http://{args.host}:{args.port}")
    print(f"   Health check: http://{args.host}:{args.port}/health")
    print(f"   Workers: {', '.join(WORKERS.keys())}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\n🛑 Shutting down...")
        server.server_close()
`;

  fs.writeFileSync(path.join(projectDir, 'main.py'), content, 'utf-8');
}
