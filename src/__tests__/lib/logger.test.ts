import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { logger } from '@/lib/kantorku/logger';

// The logger module captures `isDev` at import time:
//   const isDev = process.env.NODE_ENV === 'development';
// In vitest, NODE_ENV is typically 'test', so isDev = false.
// This means debug() and info() are no-ops, while warn() and error() always log.

// Mock console methods
const mockConsoleDebug = vi.fn();
const mockConsoleInfo = vi.fn();
const mockConsoleWarn = vi.fn();
const mockConsoleError = vi.fn();

beforeEach(() => {
  vi.stubGlobal('console', {
    ...console,
    debug: mockConsoleDebug,
    info: mockConsoleInfo,
    warn: mockConsoleWarn,
    error: mockConsoleError,
  });
  mockConsoleDebug.mockReset();
  mockConsoleInfo.mockReset();
  mockConsoleWarn.mockReset();
  mockConsoleError.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ── All Log Levels ───────────────────────────────────────────────

describe('all log levels', () => {
  it('should have debug method', () => {
    expect(typeof logger.debug).toBe('function');
  });

  it('should have info method', () => {
    expect(typeof logger.info).toBe('function');
  });

  it('should have warn method', () => {
    expect(typeof logger.warn).toBe('function');
  });

  it('should have error method', () => {
    expect(typeof logger.error).toBe('function');
  });

  it('should have exactly 4 log methods', () => {
    const methods = Object.keys(logger).filter((k) => typeof logger[k as keyof typeof logger] === 'function');
    expect(methods).toHaveLength(4);
    expect(methods.sort()).toEqual(['debug', 'error', 'info', 'warn']);
  });
});

// ── debug (no-op in test mode) ───────────────────────────────────

describe('logger.debug', () => {
  it('should NOT call console.debug when not in development mode', () => {
    logger.debug('test-context', 'test message');
    // In test mode (NODE_ENV !== 'development'), debug is a no-op
    expect(mockConsoleDebug).not.toHaveBeenCalled();
  });
});

// ── info (no-op in test mode) ────────────────────────────────────

describe('logger.info', () => {
  it('should NOT call console.info when not in development mode', () => {
    logger.info('test-context', 'test message');
    // In test mode (NODE_ENV !== 'development'), info is a no-op
    expect(mockConsoleInfo).not.toHaveBeenCalled();
  });
});

// ── warn (always logs) ──────────────────────────────────────────

describe('logger.warn', () => {
  it('should always call console.warn regardless of NODE_ENV', () => {
    logger.warn('test-context', 'warning message');
    expect(mockConsoleWarn).toHaveBeenCalledTimes(1);
  });

  it('should include WARN level in formatted message', () => {
    logger.warn('ctx', 'msg');
    const message = mockConsoleWarn.mock.calls[0][0] as string;
    expect(message).toContain('[WARN]');
  });

  it('should include context in formatted message', () => {
    logger.warn('my-module', 'msg');
    const message = mockConsoleWarn.mock.calls[0][0] as string;
    expect(message).toContain('[kantorku:my-module]');
  });

  it('should include the message content', () => {
    logger.warn('ctx', 'Something might be wrong');
    const message = mockConsoleWarn.mock.calls[0][0] as string;
    expect(message).toContain('Something might be wrong');
  });

  it('should pass additional data arguments', () => {
    const extraData = { code: 'WARN_001' };
    logger.warn('ctx', 'msg', extraData);
    expect(mockConsoleWarn.mock.calls[0][1]).toEqual(extraData);
  });

  it('should pass multiple additional data arguments', () => {
    logger.warn('ctx', 'msg', 'extra1', 'extra2');
    expect(mockConsoleWarn.mock.calls[0][1]).toBe('extra1');
    expect(mockConsoleWarn.mock.calls[0][2]).toBe('extra2');
  });

  it('should format message with timestamp', () => {
    logger.warn('ctx', 'msg');
    const message = mockConsoleWarn.mock.calls[0][0] as string;
    // Timestamp format: [HH:MM:SS]
    expect(message).toMatch(/^\[\d{2}:\d{2}:\d{2}\]/);
  });

  it('should format message as: [timestamp] [LEVEL] [kantorku:context] message', () => {
    logger.warn('my-context', 'test warning');
    const message = mockConsoleWarn.mock.calls[0][0] as string;
    expect(message).toMatch(
      /^\[\d{2}:\d{2}:\d{2}\] \[WARN\] \[kantorku:my-context\] test warning$/
    );
  });
});

// ── error (always logs) ─────────────────────────────────────────

describe('logger.error', () => {
  it('should always call console.error regardless of NODE_ENV', () => {
    logger.error('test-context', 'error message');
    expect(mockConsoleError).toHaveBeenCalledTimes(1);
  });

  it('should include ERROR level in formatted message', () => {
    logger.error('ctx', 'msg');
    const message = mockConsoleError.mock.calls[0][0] as string;
    expect(message).toContain('[ERROR]');
  });

  it('should include context in formatted message', () => {
    logger.error('api-handler', 'msg');
    const message = mockConsoleError.mock.calls[0][0] as string;
    expect(message).toContain('[kantorku:api-handler]');
  });

  it('should include the message content', () => {
    logger.error('ctx', 'Critical failure');
    const message = mockConsoleError.mock.calls[0][0] as string;
    expect(message).toContain('Critical failure');
  });

  it('should pass additional data arguments including error objects', () => {
    const error = new Error('test error');
    logger.error('ctx', 'msg', error);
    expect(mockConsoleError.mock.calls[0][1]).toBe(error);
  });

  it('should pass multiple additional data arguments', () => {
    logger.error('ctx', 'msg', 'extra1', { key: 'val' });
    expect(mockConsoleError.mock.calls[0][1]).toBe('extra1');
    expect(mockConsoleError.mock.calls[0][2]).toEqual({ key: 'val' });
  });

  it('should format message with timestamp', () => {
    logger.error('ctx', 'msg');
    const message = mockConsoleError.mock.calls[0][0] as string;
    expect(message).toMatch(/^\[\d{2}:\d{2}:\d{2}\]/);
  });

  it('should format message as: [timestamp] [LEVEL] [kantorku:context] message', () => {
    logger.error('my-context', 'test error');
    const message = mockConsoleError.mock.calls[0][0] as string;
    expect(message).toMatch(
      /^\[\d{2}:\d{2}:\d{2}\] \[ERROR\] \[kantorku:my-context\] test error$/
    );
  });
});

// ── Formatted Message Structure ──────────────────────────────────

describe('message formatting', () => {
  it('should format with timestamp in [HH:MM:SS] format', () => {
    logger.error('ctx', 'msg');
    const message = mockConsoleError.mock.calls[0][0] as string;
    expect(message).toMatch(/^\[\d{2}:\d{2}:\d{2}\]/);
  });

  it('should prefix context with "kantorku:"', () => {
    logger.error('module', 'msg');
    const message = mockConsoleError.mock.calls[0][0] as string;
    expect(message).toContain('kantorku:module');
  });

  it('should handle empty context string', () => {
    logger.error('', 'msg');
    const message = mockConsoleError.mock.calls[0][0] as string;
    expect(message).toContain('[kantorku:]');
  });

  it('should handle empty message string', () => {
    logger.error('ctx', '');
    const message = mockConsoleError.mock.calls[0][0] as string;
    expect(message).toMatch(/\[kantorku:ctx\] $/);
  });

  it('should handle special characters in context', () => {
    logger.error('api/v1/users', 'msg');
    const message = mockConsoleError.mock.calls[0][0] as string;
    expect(message).toContain('[kantorku:api/v1/users]');
  });
});

// ── Context Parameter ────────────────────────────────────────────

describe('context parameter', () => {
  it('should accept string context parameter', () => {
    logger.error('store', 'msg');
    expect(mockConsoleError).toHaveBeenCalled();
    const message = mockConsoleError.mock.calls[0][0] as string;
    expect(message).toContain('[kantorku:store]');
  });

  it('should differentiate between contexts', () => {
    logger.error('context-a', 'msg a');
    logger.error('context-b', 'msg b');

    const msgA = mockConsoleError.mock.calls[0][0] as string;
    const msgB = mockConsoleError.mock.calls[1][0] as string;

    expect(msgA).toContain('[kantorku:context-a]');
    expect(msgB).toContain('[kantorku:context-b]');
  });

  it('should use context in both warn and error', () => {
    logger.warn('shared-ctx', 'warn msg');
    logger.error('shared-ctx', 'error msg');

    const warnMsg = mockConsoleWarn.mock.calls[0][0] as string;
    const errorMsg = mockConsoleError.mock.calls[0][0] as string;

    expect(warnMsg).toContain('[kantorku:shared-ctx]');
    expect(errorMsg).toContain('[kantorku:shared-ctx]');
  });
});

// ── Level-specific behavior ──────────────────────────────────────

describe('level-specific behavior', () => {
  it('should not call console.debug when NODE_ENV is test', () => {
    logger.debug('ctx', 'msg');
    expect(mockConsoleDebug).not.toHaveBeenCalled();
  });

  it('should not call console.info when NODE_ENV is test', () => {
    logger.info('ctx', 'msg');
    expect(mockConsoleInfo).not.toHaveBeenCalled();
  });

  it('should always call console.warn even when NODE_ENV is test', () => {
    logger.warn('ctx', 'msg');
    expect(mockConsoleWarn).toHaveBeenCalled();
  });

  it('should always call console.error even when NODE_ENV is test', () => {
    logger.error('ctx', 'msg');
    expect(mockConsoleError).toHaveBeenCalled();
  });

  it('should use uppercase level in format', () => {
    logger.error('ctx', 'msg');
    const msg = mockConsoleError.mock.calls[0][0] as string;
    expect(msg).toContain('[ERROR]');
    expect(msg).not.toContain('[error]');
  });

  it('should use uppercase WARN in format', () => {
    logger.warn('ctx', 'msg');
    const msg = mockConsoleWarn.mock.calls[0][0] as string;
    expect(msg).toContain('[WARN]');
    expect(msg).not.toContain('[warn]');
  });
});
