import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

// ============================================================
// Kantorku Config Management
// Reads/writes kantorku.toml and .env files
// ============================================================

export interface KantorkuConfig {
  backend: {
    host: string;
    port: number;
    workers_dir: string;
    log_level: string;
  };
  frontend: {
    host: string;
    port: number;
  };
  llm: {
    default_provider: string;
    default_model: string;
    temperature: number;
    max_tokens: number;
  };
  office: {
    name: string;
    conductor_name: string;
    max_workers: number;
  };
}

export interface ApiKeys {
  anthropic?: string;
  google?: string;
  minimax?: string;
  deepseek?: string;
  openai?: string;
  xai?: string;
  ollama_host?: string;
  zai_sdk?: string;
}

const DEFAULT_CONFIG: KantorkuConfig = {
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
    default_provider: 'openai',
    default_model: 'gpt-4o',
    temperature: 0.7,
    max_tokens: 4096,
  },
  office: {
    name: 'Kantorku Office',
    conductor_name: 'Pak Raden',
    max_workers: 10,
  },
};

const API_KEY_MAP: Record<string, { envVar: string; label: string; masked: boolean }> = {
  anthropic: { envVar: 'ANTHROPIC_API_KEY', label: 'Anthropic', masked: true },
  google: { envVar: 'GOOGLE_API_KEY', label: 'Google / Vertex AI', masked: true },
  minimax: { envVar: 'MINIMAX_API_KEY', label: 'MiniMax', masked: true },
  deepseek: { envVar: 'DEEPSEEK_API_KEY', label: 'DeepSeek', masked: true },
  openai: { envVar: 'OPENAI_API_KEY', label: 'OpenAI', masked: true },
  xai: { envVar: 'XAI_API_KEY', label: 'xAI (Grok)', masked: true },
  ollama_host: { envVar: 'OLLAMA_HOST', label: 'Ollama Host', masked: false },
  zai_sdk: { envVar: 'ZAI_SDK_KEY', label: 'Z-AI SDK', masked: true },
};

/**
 * Find the project root directory by searching upward for kantorku.toml
 */
export function findProjectRoot(startDir?: string): string | null {
  let dir = startDir || process.cwd();
  while (dir !== path.dirname(dir)) {
    if (fs.existsSync(path.join(dir, 'kantorku.toml'))) {
      return dir;
    }
    dir = path.dirname(dir);
  }
  return null;
}

/**
 * Get the kantorku config directory (~/.kantorku)
 */
export function getConfigDir(): string {
  const dir = path.join(os.homedir(), '.kantorku');
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  return dir;
}

/**
 * Parse a simple TOML-like file into a nested object
 */
function parseToml(content: string): Record<string, any> {
  const result: Record<string, any> = {};
  let currentSection = '';

  for (const rawLine of content.split('\n')) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;

    // Section header [section]
    const sectionMatch = line.match(/^\[(\w+)\]$/);
    if (sectionMatch) {
      currentSection = sectionMatch[1];
      if (!result[currentSection]) result[currentSection] = {};
      continue;
    }

    // Key = value
    const kvMatch = line.match(/^(\w+)\s*=\s*(.+)$/);
    if (kvMatch) {
      const key = kvMatch[1];
      let value: any = kvMatch[2].trim();

      // Remove quotes
      if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
        value = value.slice(1, -1);
      } else if (value === 'true') {
        value = true;
      } else if (value === 'false') {
        value = false;
      } else if (/^\d+$/.test(value)) {
        value = parseInt(value, 10);
      } else if (/^\d+\.\d+$/.test(value)) {
        value = parseFloat(value);
      }

      if (currentSection) {
        result[currentSection][key] = value;
      } else {
        result[key] = value;
      }
    }
  }

  return result;
}

/**
 * Serialize a nested object to TOML-like format
 */
function serializeToml(obj: Record<string, any>): string {
  const lines: string[] = ['# Kantorku Configuration', `# Generated at ${new Date().toISOString()}`, ''];

  for (const [section, values] of Object.entries(obj)) {
    if (typeof values === 'object' && values !== null && !Array.isArray(values)) {
      lines.push(`[${section}]`);
      for (const [key, val] of Object.entries(values)) {
        if (typeof val === 'string') {
          lines.push(`${key} = "${val}"`);
        } else {
          lines.push(`${key} = ${val}`);
        }
      }
      lines.push('');
    } else {
      if (typeof values === 'string') {
        lines.push(`${section} = "${values}"`);
      } else {
        lines.push(`${section} = ${values}`);
      }
    }
  }

  return lines.join('\n');
}

/**
 * Read kantorku.toml config from project root or ~/.kantorku
 */
export function readConfig(projectDir?: string): KantorkuConfig {
  const configPath = projectDir
    ? path.join(projectDir, 'kantorku.toml')
    : path.join(getConfigDir(), 'config.toml');

  if (!fs.existsSync(configPath)) {
    return { ...DEFAULT_CONFIG };
  }

  try {
    const content = fs.readFileSync(configPath, 'utf-8');
    const parsed = parseToml(content);

    // Deep merge with defaults
    return {
      backend: { ...DEFAULT_CONFIG.backend, ...(parsed.backend || {}) },
      frontend: { ...DEFAULT_CONFIG.frontend, ...(parsed.frontend || {}) },
      llm: { ...DEFAULT_CONFIG.llm, ...(parsed.llm || {}) },
      office: { ...DEFAULT_CONFIG.office, ...(parsed.office || {}) },
    };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

/**
 * Write kantorku.toml config
 */
export function writeConfig(config: KantorkuConfig, projectDir?: string): void {
  const configPath = projectDir
    ? path.join(projectDir, 'kantorku.toml')
    : path.join(getConfigDir(), 'config.toml');

  const content = serializeToml(config as unknown as Record<string, any>);
  fs.writeFileSync(configPath, content, 'utf-8');
}

/**
 * Parse .env file into key-value pairs
 */
function parseEnvFile(content: string): Record<string, string> {
  const result: Record<string, string> = {};
  for (const rawLine of content.split('\n')) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const match = line.match(/^([^=]+)=(.*)$/);
    if (match) {
      let value = match[2].trim();
      // Remove surrounding quotes
      if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
        value = value.slice(1, -1);
      }
      result[match[1].trim()] = value;
    }
  }
  return result;
}

/**
 * Serialize key-value pairs to .env format
 */
function serializeEnvFile(vars: Record<string, string>): string {
  const lines: string[] = [
    '# Kantorku Environment Variables',
    `# Updated at ${new Date().toISOString()}`,
    '',
  ];
  for (const [key, value] of Object.entries(vars)) {
    if (value.includes(' ') || value.includes('#')) {
      lines.push(`${key}="${value}"`);
    } else {
      lines.push(`${key}=${value}`);
    }
  }
  return lines.join('\n');
}

/**
 * Read API keys from .env file
 */
export function readApiKeys(projectDir?: string): ApiKeys {
  const envPath = projectDir
    ? path.join(projectDir, '.env')
    : path.join(getConfigDir(), '.env');

  if (!fs.existsSync(envPath)) {
    return {};
  }

  try {
    const content = fs.readFileSync(envPath, 'utf-8');
    const parsed = parseEnvFile(content);
    const keys: ApiKeys = {};

    for (const [provider, info] of Object.entries(API_KEY_MAP)) {
      if (parsed[info.envVar]) {
        (keys as any)[provider] = parsed[info.envVar];
      }
    }

    return keys;
  } catch {
    return {};
  }
}

/**
 * Write API keys to .env file (preserves existing vars)
 */
export function writeApiKeys(keys: ApiKeys, projectDir?: string): void {
  const envPath = projectDir
    ? path.join(projectDir, '.env')
    : path.join(getConfigDir(), '.env');

  // Read existing
  let existing: Record<string, string> = {};
  if (fs.existsSync(envPath)) {
    try {
      existing = parseEnvFile(fs.readFileSync(envPath, 'utf-8'));
    } catch {
      // ignore
    }
  }

  // Merge new keys
  for (const [provider, value] of Object.entries(keys)) {
    if (value !== undefined && value !== null && value !== '') {
      const info = API_KEY_MAP[provider];
      if (info) {
        existing[info.envVar] = value;
      }
    }
  }

  fs.writeFileSync(envPath, serializeEnvFile(existing), 'utf-8');
}

/**
 * Get the API key metadata (for display purposes)
 */
export function getApiKeyProviders(): Array<{
  key: string;
  envVar: string;
  label: string;
  masked: boolean;
}> {
  return Object.entries(API_KEY_MAP).map(([key, info]) => ({
    key,
    ...info,
  }));
}

/**
 * Mask an API key for display
 */
export function maskKey(key: string): string {
  if (key.length <= 8) return '****';
  return key.slice(0, 4) + '****' + key.slice(-4);
}

/**
 * Get the backend URL from config
 */
export function getBackendUrl(config?: KantorkuConfig): string {
  const cfg = config || readConfig();
  return `http://${cfg.backend.host}:${cfg.backend.port}`;
}

/**
 * Get the WebSocket URL from config
 */
export function getWebSocketUrl(config?: KantorkuConfig): string {
  const cfg = config || readConfig();
  return `ws://${cfg.backend.host}:${cfg.backend.port}/ws`;
}

/**
 * Get the frontend URL from config
 */
export function getFrontendUrl(config?: KantorkuConfig): string {
  const cfg = config || readConfig();
  return `http://${cfg.frontend.host}:${cfg.frontend.port}`;
}

/**
 * Load .env into process.env
 */
export function loadEnv(projectDir?: string): void {
  const envPath = projectDir
    ? path.join(projectDir, '.env')
    : path.join(getConfigDir(), '.env');

  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf-8');
    const parsed = parseEnvFile(content);
    for (const [key, value] of Object.entries(parsed)) {
      if (!process.env[key]) {
        process.env[key] = value;
      }
    }
  }
}
