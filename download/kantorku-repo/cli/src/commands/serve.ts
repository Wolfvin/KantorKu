import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import chalk from 'chalk';
import ora from 'ora';
import boxen from 'boxen';
import { readConfig, loadEnv, getBackendUrl, findProjectRoot } from '../lib/config';

// ============================================================
// kantorku serve - Start the Python Backend
// ============================================================

interface ServeOptions {
  port?: number;
  host?: string;
  workers?: number;
  reload?: boolean;
}

export async function serveCommand(options: ServeOptions = {}): Promise<void> {
  const config = readConfig();
  loadEnv();

  const host = options.host || config.backend.host;
  const port = options.port || config.backend.port;
  const reload = options.reload !== false;

  console.log('');
  console.log(
    boxen(
      chalk.cyan.bold('  🚀 Starting Kantorku Backend  ') + '\n\n' +
      chalk.gray(`Host: ${chalk.white(host)}`) + '\n' +
      chalk.gray(`Port: ${chalk.white(String(port))}`) + '\n' +
      chalk.gray(`Reload: ${chalk.white(reload ? 'enabled' : 'disabled')}`),
      {
        padding: 1,
        margin: 0,
        borderStyle: 'round',
        borderColor: 'cyan',
      }
    )
  );
  console.log('');

  // Find project root
  const projectRoot = findProjectRoot();
  const backendDir = projectRoot
    ? path.join(projectRoot, config.backend.workers_dir, '..')
    : process.cwd();

  // Check for Python backend
  const mainPy = path.join(backendDir, 'main.py');
  const appPy = path.join(backendDir, 'app.py');
  const managePy = path.join(backendDir, 'manage.py');

  let pythonEntry: string | null = null;
  for (const candidate of [mainPy, appPy, managePy]) {
    if (fs.existsSync(candidate)) {
      pythonEntry = candidate;
      break;
    }
  }

  if (!pythonEntry) {
    console.log(chalk.yellow('  ⚠ No Python backend entry point found.'));
    console.log(chalk.gray('  Looking for: main.py, app.py, or manage.py'));
    console.log(chalk.gray(`  Searched in: ${backendDir}`));
    console.log('');
    console.log(chalk.cyan('  Creating a minimal backend...'));

    await createMinimalBackend(backendDir, host, port);
    pythonEntry = path.join(backendDir, 'main.py');
  }

  // Find Python executable
  const pythonCmd = findPython();

  const spinner = ora('Starting Python backend...').start();

  // Set environment variables
  const env = { ...process.env } as Record<string, string>;
  env.HOST = host;
  env.PORT = String(port);
  env.KANTORKU_WORKERS = String(options.workers || config.office.max_workers);

  try {
    const proc = spawn(pythonCmd, [pythonEntry, '--host', host, '--port', String(port)], {
      cwd: backendDir,
      env,
      stdio: 'inherit',
    });

    spinner.succeed(chalk.green('Backend process started'));
    console.log('');
    console.log(chalk.gray(`  Backend URL: ${chalk.white(getBackendUrl({ ...config, backend: { ...config.backend, host, port } }))}`));
    console.log(chalk.gray('  Press Ctrl+C to stop'));
    console.log('');

    // Handle process events
    proc.on('error', (err) => {
      console.log(chalk.red(`\n  ✗ Failed to start backend: ${err.message}`));
      process.exit(1);
    });

    proc.on('exit', (code) => {
      if (code !== 0 && code !== null) {
        console.log(chalk.red(`\n  ✗ Backend exited with code ${code}`));
      }
      process.exit(code || 0);
    });

    // Handle Ctrl+C gracefully
    process.on('SIGINT', () => {
      console.log(chalk.yellow('\n\n  Shutting down backend...'));
      proc.kill('SIGTERM');
      setTimeout(() => process.exit(0), 1000);
    });

    // Keep the process alive
    await new Promise(() => {});
  } catch (error) {
    spinner.fail(chalk.red('Failed to start backend'));
    throw error;
  }
}

function findPython(): string {
  const candidates = ['python3', 'python'];
  for (const cmd of candidates) {
    try {
      const result = spawn(cmd, ['--version'], { stdio: 'pipe' });
      // If spawn doesn't throw, the command exists
      return cmd;
    } catch {
      continue;
    }
  }
  return 'python3';
}

async function createMinimalBackend(dir: string, host: string, port: number): Promise<void> {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  const mainPyContent = `#!/usr/bin/env python3
"""
Kantorku Backend - Minimal FastAPI Server
"""
import os
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class KantorkuHandler(BaseHTTPRequestHandler):
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
                "workers": {"total": 0, "active": 0, "idle": 0, "error": 0},
                "memory": {"total_mb": 0, "used_mb": 0, "free_mb": 0},
                "backend_url": f"http://{host}:{port}"
            })
        elif parsed.path == "/api/workers":
            self.send_json({"workers": []})
        elif parsed.path.startswith("/api/workers/"):
            worker_id = parsed.path.split("/")[-1]
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
                self.send_json({
                    "message": {
                        "role": "assistant",
                        "content": f"Hello! I am the Kantorku Conductor. I received your message: '{message}'. The office is currently running but no workers are assigned yet. Use 'kantorku setup' to configure your API keys and 'kantorku worker list' to see available workers.",
                        "timestamp": time.time()
                    },
                    "worker_used": None,
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
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, format, *args):
        print(f"[Kantorku] {args[0]}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Kantorku Backend")
    parser.add_argument("--host", default="${host}", help="Host to bind to")
    parser.add_argument("--port", type=int, default=${port}, help="Port to bind to")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), KantorkuHandler)
    print(f"🏠 Kantorku Backend running on http://{args.host}:{args.port}")
    print(f"   Health check: http://{args.host}:{args.port}/health")
    print(f"   API base: http://{args.host}:{args.port}/api")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\n🛑 Shutting down Kantorku Backend...")
        server.server_close()
`;

  fs.writeFileSync(path.join(dir, 'main.py'), mainPyContent, 'utf-8');
  console.log(chalk.green('  ✓ Created minimal backend at ' + path.join(dir, 'main.py')));
}
