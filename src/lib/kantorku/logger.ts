/**
 * KantorKu Logger — Structured logging utility
 *
 * In production, only errors and warnings are logged.
 * In development, all levels are logged.
 * This replaces direct console.error/warn calls throughout the codebase.
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

const isDev = process.env.NODE_ENV === 'development';

function formatMessage(level: LogLevel, context: string, message: string): string {
  const timestamp = new Date().toISOString().slice(11, 19);
  return `[${timestamp}] [${level.toUpperCase()}] [kantorku:${context}] ${message}`;
}

export const logger = {
  debug(context: string, message: string, ...data: unknown[]) {
    if (isDev) {
      console.debug(formatMessage('debug', context, message), ...data);
    }
  },

  info(context: string, message: string, ...data: unknown[]) {
    if (isDev) {
      console.info(formatMessage('info', context, message), ...data);
    }
  },

  warn(context: string, message: string, ...data: unknown[]) {
    console.warn(formatMessage('warn', context, message), ...data);
  },

  error(context: string, message: string, ...data: unknown[]) {
    console.error(formatMessage('error', context, message), ...data);
  },
};
