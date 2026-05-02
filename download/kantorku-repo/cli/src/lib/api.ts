import axios, { AxiosInstance, AxiosError } from 'axios';
import { getBackendUrl, readConfig, loadEnv, KantorkuConfig } from './config';

// ============================================================
// Kantorku API Client
// Communicates with the Python backend REST API
// ============================================================

export interface WorkerInfo {
  id: string;
  name: string;
  role: string;
  status: 'idle' | 'busy' | 'error' | 'offline';
  provider: string;
  model: string;
  tasks_completed: number;
  tasks_failed: number;
  last_activity: string;
  capabilities: string[];
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  worker_id?: string;
}

export interface ChatResponse {
  message: ChatMessage;
  worker_used?: string;
  tokens_used?: number;
}

export interface SystemStatus {
  status: 'running' | 'stopped' | 'error';
  uptime: number;
  version: string;
  workers: {
    total: number;
    active: number;
    idle: number;
    error: number;
  };
  memory: {
    total_mb: number;
    used_mb: number;
    free_mb: number;
  };
  backend_url: string;
}

export interface TaskInfo {
  id: string;
  type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  assigned_to?: string;
  created_at: string;
  completed_at?: string;
  result?: string;
  error?: string;
}

export class KantorkuApi {
  private client: AxiosInstance;
  private config: KantorkuConfig;

  constructor(config?: KantorkuConfig) {
    this.config = config || readConfig();
    loadEnv();

    const baseURL = getBackendUrl(this.config);
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'kantorku-cli/1.0.0',
      },
    });
  }

  /**
   * Check if the backend is reachable
   */
  async isHealthy(): Promise<boolean> {
    try {
      const response = await this.client.get('/health');
      return response.status === 200;
    } catch {
      return false;
    }
  }

  /**
   * Get system status
   */
  async getStatus(): Promise<SystemStatus> {
    try {
      const response = await this.client.get('/api/status');
      return response.data;
    } catch (error) {
      if (this.isAxiosError(error) && error.response?.status === 404) {
        // Fallback: try health endpoint
        const healthy = await this.isHealthy();
        return {
          status: healthy ? 'running' : 'stopped',
          uptime: 0,
          version: 'unknown',
          workers: { total: 0, active: 0, idle: 0, error: 0 },
          memory: { total_mb: 0, used_mb: 0, free_mb: 0 },
          backend_url: getBackendUrl(this.config),
        };
      }
      throw this.formatError(error);
    }
  }

  /**
   * List all workers
   */
  async listWorkers(): Promise<WorkerInfo[]> {
    try {
      const response = await this.client.get('/api/workers');
      return response.data.workers || response.data || [];
    } catch (error) {
      if (this.isAxiosError(error) && error.response?.status === 404) {
        return [];
      }
      throw this.formatError(error);
    }
  }

  /**
   * Get a specific worker
   */
  async getWorker(workerId: string): Promise<WorkerInfo> {
    try {
      const response = await this.client.get(`/api/workers/${workerId}`);
      return response.data;
    } catch (error) {
      throw this.formatError(error);
    }
  }

  /**
   * Start a worker
   */
  async startWorker(workerId: string): Promise<{ message: string }> {
    try {
      const response = await this.client.post(`/api/workers/${workerId}/start`);
      return response.data;
    } catch (error) {
      throw this.formatError(error);
    }
  }

  /**
   * Stop a worker
   */
  async stopWorker(workerId: string): Promise<{ message: string }> {
    try {
      const response = await this.client.post(`/api/workers/${workerId}/stop`);
      return response.data;
    } catch (error) {
      throw this.formatError(error);
    }
  }

  /**
   * Send a chat message to the conductor
   */
  async chat(message: string, conversationId?: string): Promise<ChatResponse> {
    try {
      const response = await this.client.post('/api/chat', {
        message,
        conversation_id: conversationId,
      });
      return response.data;
    } catch (error) {
      throw this.formatError(error);
    }
  }

  /**
   * Get chat history
   */
  async getChatHistory(conversationId: string): Promise<ChatMessage[]> {
    try {
      const response = await this.client.get(`/api/chat/${conversationId}`);
      return response.data.messages || response.data || [];
    } catch (error) {
      throw this.formatError(error);
    }
  }

  /**
   * List tasks
   */
  async listTasks(): Promise<TaskInfo[]> {
    try {
      const response = await this.client.get('/api/tasks');
      return response.data.tasks || response.data || [];
    } catch (error) {
      if (this.isAxiosError(error) && error.response?.status === 404) {
        return [];
      }
      throw this.formatError(error);
    }
  }

  /**
   * Create a new task
   */
  async createTask(type: string, payload: Record<string, any>): Promise<TaskInfo> {
    try {
      const response = await this.client.post('/api/tasks', { type, payload });
      return response.data;
    } catch (error) {
      throw this.formatError(error);
    }
  }

  private isAxiosError(error: any): error is AxiosError {
    return error && error.isAxiosError === true;
  }

  private formatError(error: any): Error {
    if (this.isAxiosError(error)) {
      if (error.code === 'ECONNREFUSED') {
        return new Error(
          `Cannot connect to backend at ${getBackendUrl(this.config)}. Is the server running?`
        );
      }
      if (error.code === 'ETIMEDOUT') {
        return new Error('Connection to backend timed out. The server may be overloaded.');
      }
      if (error.response) {
        const data = error.response.data as any;
        const msg = data?.detail || data?.message || data?.error || JSON.stringify(data);
        return new Error(`Backend error (${error.response.status}): ${msg}`);
      }
    }
    return error instanceof Error ? error : new Error(String(error));
  }
}
