import { spawn } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import chalk from 'chalk';
import ora from 'ora';
import boxen from 'boxen';
import { readConfig, loadEnv, getFrontendUrl, findProjectRoot } from '../lib/config';

// ============================================================
// kantorku dev - Start the Next.js Interface
// ============================================================

interface DevOptions {
  port?: number;
  host?: string;
  open?: boolean;
}

export async function devCommand(options: DevOptions = {}): Promise<void> {
  const config = readConfig();
  loadEnv();

  const host = options.host || config.frontend.host;
  const port = options.port || config.frontend.port;

  console.log('');
  console.log(
    boxen(
      chalk.cyan.bold('  🎨 Starting Kantorku Interface  ') + '\n\n' +
      chalk.gray(`Host: ${chalk.white(host)}`) + '\n' +
      chalk.gray(`Port: ${chalk.white(String(port))}`),
      {
        padding: 1,
        margin: 0,
        borderStyle: 'round',
        borderColor: 'magenta',
      }
    )
  );
  console.log('');

  // Find the frontend directory
  const projectRoot = findProjectRoot();
  let frontendDir: string | null = null;

  if (projectRoot) {
    // Look for common frontend directory names
    const candidates = ['web', 'frontend', 'ui', 'interface', 'app', 'client'];
    for (const dir of candidates) {
      const candidatePath = path.join(projectRoot, dir);
      if (fs.existsSync(candidatePath) && fs.existsSync(path.join(candidatePath, 'package.json'))) {
        frontendDir = candidatePath;
        break;
      }
    }

    // Also check if project root itself is a Next.js project
    if (!frontendDir && fs.existsSync(path.join(projectRoot, 'package.json'))) {
      const pkg = JSON.parse(fs.readFileSync(path.join(projectRoot, 'package.json'), 'utf-8'));
      if (pkg.dependencies?.next || pkg.devDependencies?.next) {
        frontendDir = projectRoot;
      }
    }
  }

  if (!frontendDir) {
    console.log(chalk.yellow('  ⚠ No Next.js frontend found.'));
    console.log(chalk.gray('  Searched for directories: web, frontend, ui, interface, app, client'));
    console.log('');
    console.log(chalk.cyan('  Creating a minimal Next.js interface...'));

    frontendDir = await createMinimalFrontend(projectRoot || process.cwd());
  }

  const spinner = ora('Installing dependencies...').start();

  // Check for node_modules
  const nodeModules = path.join(frontendDir, 'node_modules');
  if (!fs.existsSync(nodeModules)) {
    const installProc = spawn('npm', ['install'], {
      cwd: frontendDir,
      stdio: 'pipe',
      shell: true,
    });

    await new Promise<void>((resolve, reject) => {
      installProc.on('close', (code) => {
        if (code === 0) resolve();
        else reject(new Error(`npm install exited with code ${code}`));
      });
      installProc.on('error', reject);
    });
  }

  spinner.text = 'Starting Next.js development server...';

  try {
    // Build the dev command
    const env = { ...process.env } as Record<string, string>;
    env.PORT = String(port);
    env.HOSTNAME = host;

    // Try to use the project's local next binary first
    const nextBin = path.join(frontendDir, 'node_modules', '.bin', 'next');
    const cmd = fs.existsSync(nextBin) ? nextBin : 'npx';
    const args = fs.existsSync(nextBin) ? ['dev'] : ['next', 'dev'];

    const proc = spawn(cmd, [...args, '-p', String(port)], {
      cwd: frontendDir,
      env,
      stdio: 'inherit',
      shell: true,
    });

    spinner.succeed(chalk.green('Next.js development server starting'));
    console.log('');
    console.log(chalk.gray(`  Frontend URL: ${chalk.white(`http://${host}:${port}`)}`));
    console.log(chalk.gray('  Press Ctrl+C to stop'));
    console.log('');

    // Handle process events
    proc.on('error', (err) => {
      console.log(chalk.red(`\n  ✗ Failed to start frontend: ${err.message}`));
      process.exit(1);
    });

    proc.on('exit', (code) => {
      if (code !== 0 && code !== null) {
        console.log(chalk.red(`\n  ✗ Frontend exited with code ${code}`));
      }
      process.exit(code || 0);
    });

    // Handle Ctrl+C gracefully
    process.on('SIGINT', () => {
      console.log(chalk.yellow('\n\n  Shutting down frontend...'));
      proc.kill('SIGTERM');
      setTimeout(() => process.exit(0), 1000);
    });

    // Keep the process alive
    await new Promise(() => {});
  } catch (error) {
    spinner.fail(chalk.red('Failed to start frontend'));
    throw error;
  }
}

async function createMinimalFrontend(baseDir: string): Promise<string> {
  const webDir = path.join(baseDir, 'web');
  if (!fs.existsSync(webDir)) {
    fs.mkdirSync(webDir, { recursive: true });
  }

  // Create a minimal Next.js-like HTML page
  const indexHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Kantorku Office</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      color: #e2e8f0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .container {
      max-width: 600px;
      text-align: center;
      padding: 2rem;
    }
    h1 {
      font-size: 2.5rem;
      margin-bottom: 0.5rem;
      background: linear-gradient(135deg, #06b6d4, #8b5cf6);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    p { color: #94a3b8; margin-bottom: 1rem; }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      background: rgba(6, 182, 212, 0.1);
      border: 1px solid rgba(6, 182, 212, 0.3);
      border-radius: 9999px;
      margin-top: 1rem;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #06b6d4;
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
    .info {
      margin-top: 2rem;
      padding: 1rem;
      background: rgba(255,255,255,0.05);
      border-radius: 8px;
      font-size: 0.875rem;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>🏢 Kantorku Office</h1>
    <p>Your AI-powered office is running</p>
    <div class="status">
      <span class="dot"></span>
      <span>System Online</span>
    </div>
    <div class="info">
      <p>Use <code>kantorku chat</code> to talk to the Conductor</p>
      <p>Use <code>kantorku worker list</code> to see available workers</p>
    </div>
  </div>
</body>
</html>`;

  // Create a simple server to serve this
  const serverJs = `const http = require('http');
const fs = require('fs');
const path = require('path');

const port = process.env.PORT || 3000;
const host = process.env.HOSTNAME || '127.0.0.1';

const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf-8');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/html' });
  res.end(html);
});

server.listen(port, host, () => {
  console.log('🎨 Kantorku Interface running on http://' + host + ':' + port);
});`;

  fs.writeFileSync(path.join(webDir, 'index.html'), indexHtml, 'utf-8');
  fs.writeFileSync(path.join(webDir, 'server.js'), serverJs, 'utf-8');

  const pkgJson = {
    name: 'kantorku-interface',
    version: '1.0.0',
    scripts: {
      dev: 'node server.js',
      start: 'node server.js',
    },
  };

  fs.writeFileSync(path.join(webDir, 'package.json'), JSON.stringify(pkgJson, null, 2), 'utf-8');

  console.log(chalk.green('  ✓ Created minimal interface at ' + webDir));

  return webDir;
}
