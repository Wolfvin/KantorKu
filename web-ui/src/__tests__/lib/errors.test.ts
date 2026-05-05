import { describe, it, expect } from 'vitest';
import {
  AppError,
  ValidationError,
  NotFoundError,
  UnauthorizedError,
  ForbiddenError,
  RateLimitError,
  TimeoutError,
  BudgetExceededError,
  InternalError,
  handleApiError,
  isAppError,
  ErrorCode,
} from '@/lib/kantorku/errors';

// ── ErrorCode constants ──────────────────────────────────────────

describe('ErrorCode', () => {
  it('should have all expected error codes', () => {
    expect(ErrorCode.VALIDATION).toBe('VALIDATION_ERROR');
    expect(ErrorCode.NOT_FOUND).toBe('NOT_FOUND');
    expect(ErrorCode.UNAUTHORIZED).toBe('UNAUTHORIZED');
    expect(ErrorCode.FORBIDDEN).toBe('FORBIDDEN');
    expect(ErrorCode.RATE_LIMITED).toBe('RATE_LIMITED');
    expect(ErrorCode.TIMEOUT).toBe('TIMEOUT');
    expect(ErrorCode.BUDGET_EXCEEDED).toBe('BUDGET_EXCEEDED');
    expect(ErrorCode.INTERNAL).toBe('INTERNAL_ERROR');
  });
});

// ── AppError ─────────────────────────────────────────────────────

describe('AppError', () => {
  describe('constructor', () => {
    it('should create an AppError with default values', () => {
      const error = new AppError('Something went wrong');
      expect(error.message).toBe('Something went wrong');
      expect(error.statusCode).toBe(500);
      expect(error.code).toBe('INTERNAL_ERROR');
      expect(error.details).toBeUndefined();
      expect(error.isOperational).toBe(true);
      expect(error.name).toBe('AppError');
    });

    it('should create an AppError with custom statusCode', () => {
      const error = new AppError('Bad request', 400);
      expect(error.statusCode).toBe(400);
    });

    it('should create an AppError with custom code', () => {
      const error = new AppError('Custom error', 500, 'CUSTOM_CODE');
      expect(error.code).toBe('CUSTOM_CODE');
    });

    it('should create an AppError with details', () => {
      const details = { field: 'email', reason: 'invalid format' };
      const error = new AppError('Validation failed', 400, 'VALIDATION_ERROR', details);
      expect(error.details).toEqual(details);
    });

    it('should create an AppError with custom isOperational', () => {
      const error = new AppError('Fatal error', 500, 'FATAL', undefined, false);
      expect(error.isOperational).toBe(false);
    });

    it('should be an instance of Error', () => {
      const error = new AppError('test');
      expect(error).toBeInstanceOf(Error);
    });

    it('should be an instance of AppError', () => {
      const error = new AppError('test');
      expect(error).toBeInstanceOf(AppError);
    });

    it('should have a stack trace', () => {
      const error = new AppError('test');
      expect(error.stack).toBeDefined();
    });
  });

  describe('toResponse()', () => {
    it('should return a NextResponse with correct JSON shape', async () => {
      const error = new AppError('Not found', 404, 'NOT_FOUND', { resource: 'session' });
      const response = error.toResponse();

      expect(response.status).toBe(404);

      const body = await response.json();
      expect(body).toEqual({
        error: {
          message: 'Not found',
          code: 'NOT_FOUND',
          statusCode: 404,
          details: { resource: 'session' },
        },
      });
    });

    it('should return details as null when not provided', async () => {
      const error = new AppError('Error without details');
      const response = error.toResponse();
      const body = await response.json();
      expect(body.error.details).toBeNull();
    });

    it('should use the correct HTTP status code in the response', async () => {
      const error = new AppError('Rate limited', 429, 'RATE_LIMITED');
      const response = error.toResponse();
      expect(response.status).toBe(429);
    });
  });
});

// ── ValidationError ──────────────────────────────────────────────

describe('ValidationError', () => {
  it('should have statusCode 400', () => {
    const error = new ValidationError('Invalid input');
    expect(error.statusCode).toBe(400);
  });

  it('should have code VALIDATION_ERROR', () => {
    const error = new ValidationError('Invalid input');
    expect(error.code).toBe('VALIDATION_ERROR');
  });

  it('should accept details', () => {
    const details = { fields: ['name', 'email'] };
    const error = new ValidationError('Multiple fields invalid', details);
    expect(error.details).toEqual(details);
  });

  it('should be an instance of AppError', () => {
    const error = new ValidationError('test');
    expect(error).toBeInstanceOf(AppError);
  });

  it('should be an instance of ValidationError', () => {
    const error = new ValidationError('test');
    expect(error).toBeInstanceOf(ValidationError);
  });

  it('should have name "ValidationError"', () => {
    const error = new ValidationError('test');
    expect(error.name).toBe('ValidationError');
  });

  it('should produce correct toResponse shape', async () => {
    const error = new ValidationError('Missing field', { field: 'title' });
    const response = error.toResponse();
    const body = await response.json();
    expect(body.error.code).toBe('VALIDATION_ERROR');
    expect(body.error.statusCode).toBe(400);
    expect(response.status).toBe(400);
  });

  it('should have default message', () => {
    const error = new ValidationError();
    expect(error.message).toBe('Validation failed');
  });
});

// ── NotFoundError ────────────────────────────────────────────────

describe('NotFoundError', () => {
  it('should have statusCode 404', () => {
    const error = new NotFoundError('Session');
    expect(error.statusCode).toBe(404);
  });

  it('should have code NOT_FOUND', () => {
    const error = new NotFoundError('Worker');
    expect(error.code).toBe('NOT_FOUND');
  });

  it('should auto-generate message from resource name', () => {
    const error = new NotFoundError('Session');
    expect(error.message).toBe('Session not found');
  });

  it('should accept details', () => {
    const error = new NotFoundError('Worker', { worker_id: 'nonexistent' });
    expect(error.details).toEqual({ worker_id: 'nonexistent' });
  });

  it('should be an instance of AppError', () => {
    const error = new NotFoundError('test');
    expect(error).toBeInstanceOf(AppError);
  });

  it('should have name "NotFoundError"', () => {
    const error = new NotFoundError('test');
    expect(error.name).toBe('NotFoundError');
  });
});

// ── UnauthorizedError ────────────────────────────────────────────

describe('UnauthorizedError', () => {
  it('should have statusCode 401', () => {
    const error = new UnauthorizedError();
    expect(error.statusCode).toBe(401);
  });

  it('should have code UNAUTHORIZED', () => {
    const error = new UnauthorizedError();
    expect(error.code).toBe('UNAUTHORIZED');
  });

  it('should have default message', () => {
    const error = new UnauthorizedError();
    expect(error.message).toBe('Authentication required');
  });

  it('should accept custom message', () => {
    const error = new UnauthorizedError('Invalid API key');
    expect(error.message).toBe('Invalid API key');
  });
});

// ── ForbiddenError ───────────────────────────────────────────────

describe('ForbiddenError', () => {
  it('should have statusCode 403', () => {
    const error = new ForbiddenError();
    expect(error.statusCode).toBe(403);
  });

  it('should have code FORBIDDEN', () => {
    const error = new ForbiddenError();
    expect(error.code).toBe('FORBIDDEN');
  });

  it('should have default message', () => {
    const error = new ForbiddenError();
    expect(error.message).toBe('Access denied');
  });
});

// ── RateLimitError ───────────────────────────────────────────────

describe('RateLimitError', () => {
  it('should have statusCode 429', () => {
    const error = new RateLimitError();
    expect(error.statusCode).toBe(429);
  });

  it('should have code RATE_LIMITED', () => {
    const error = new RateLimitError();
    expect(error.code).toBe('RATE_LIMITED');
  });

  it('should have default message "Rate limit exceeded"', () => {
    const error = new RateLimitError();
    expect(error.message).toBe('Rate limit exceeded');
  });

  it('should accept custom message', () => {
    const error = new RateLimitError('Too many requests from your IP');
    expect(error.message).toBe('Too many requests from your IP');
  });

  it('should have retryAfterMs property', () => {
    const error = new RateLimitError('Rate limited', 10000);
    expect(error.retryAfterMs).toBe(10000);
  });

  it('should have default retryAfterMs of 5000', () => {
    const error = new RateLimitError();
    expect(error.retryAfterMs).toBe(5000);
  });

  it('should include retry_after_ms in toResponse', async () => {
    const error = new RateLimitError('Rate limited', 3000);
    const response = error.toResponse();
    const body = await response.json();
    expect(body.error.details.retry_after_ms).toBe(3000);
  });

  it('should be an instance of AppError', () => {
    const error = new RateLimitError();
    expect(error).toBeInstanceOf(AppError);
  });

  it('should have name "RateLimitError"', () => {
    const error = new RateLimitError();
    expect(error.name).toBe('RateLimitError');
  });
});

// ── TimeoutError ─────────────────────────────────────────────────

describe('TimeoutError', () => {
  it('should have statusCode 504', () => {
    const error = new TimeoutError();
    expect(error.statusCode).toBe(504);
  });

  it('should have code TIMEOUT', () => {
    const error = new TimeoutError();
    expect(error.code).toBe('TIMEOUT');
  });

  it('should have default message "Request timed out"', () => {
    const error = new TimeoutError();
    expect(error.message).toBe('Request timed out');
  });

  it('should accept custom message', () => {
    const error = new TimeoutError('Worker took too long');
    expect(error.message).toBe('Worker took too long');
  });

  it('should be an instance of AppError', () => {
    const error = new TimeoutError();
    expect(error).toBeInstanceOf(AppError);
  });

  it('should have name "TimeoutError"', () => {
    const error = new TimeoutError();
    expect(error.name).toBe('TimeoutError');
  });
});

// ── BudgetExceededError ──────────────────────────────────────────

describe('BudgetExceededError', () => {
  it('should have statusCode 403', () => {
    const error = new BudgetExceededError(10, 15);
    expect(error.statusCode).toBe(403);
  });

  it('should have code BUDGET_EXCEEDED', () => {
    const error = new BudgetExceededError(10, 15);
    expect(error.code).toBe('BUDGET_EXCEEDED');
  });

  it('should auto-generate message from budget and estimated cost', () => {
    const error = new BudgetExceededError(10, 15);
    expect(error.message).toContain('15');
    expect(error.message).toContain('10');
  });

  it('should accept custom message', () => {
    const error = new BudgetExceededError(10, 15, 'Monthly budget reached');
    expect(error.message).toBe('Monthly budget reached');
  });

  it('should store budget and estimatedCost', () => {
    const error = new BudgetExceededError(10, 15);
    expect(error.budget).toBe(10);
    expect(error.estimatedCost).toBe(15);
  });

  it('should include budget details in response', async () => {
    const error = new BudgetExceededError(10, 15);
    const response = error.toResponse();
    const body = await response.json();
    expect(body.error.details.budget).toBe(10);
    expect(body.error.details.estimated_cost).toBe(15);
  });

  it('should be an instance of AppError', () => {
    const error = new BudgetExceededError(10, 15);
    expect(error).toBeInstanceOf(AppError);
  });

  it('should have name "BudgetExceededError"', () => {
    const error = new BudgetExceededError(10, 15);
    expect(error.name).toBe('BudgetExceededError');
  });
});

// ── InternalError ────────────────────────────────────────────────

describe('InternalError', () => {
  it('should have statusCode 500', () => {
    const error = new InternalError();
    expect(error.statusCode).toBe(500);
  });

  it('should have code INTERNAL_ERROR', () => {
    const error = new InternalError();
    expect(error.code).toBe('INTERNAL_ERROR');
  });

  it('should have default message', () => {
    const error = new InternalError();
    expect(error.message).toBe('Internal server error');
  });
});

// ── isAppError ───────────────────────────────────────────────────

describe('isAppError', () => {
  it('should return true for AppError instances', () => {
    expect(isAppError(new AppError('test'))).toBe(true);
  });

  it('should return true for all subclass instances', () => {
    expect(isAppError(new ValidationError('test'))).toBe(true);
    expect(isAppError(new NotFoundError('test'))).toBe(true);
    expect(isAppError(new UnauthorizedError())).toBe(true);
    expect(isAppError(new ForbiddenError())).toBe(true);
    expect(isAppError(new RateLimitError())).toBe(true);
    expect(isAppError(new TimeoutError())).toBe(true);
    expect(isAppError(new BudgetExceededError(10, 15))).toBe(true);
    expect(isAppError(new InternalError())).toBe(true);
  });

  it('should return false for plain Error', () => {
    expect(isAppError(new Error('test'))).toBe(false);
  });

  it('should return false for non-Error types', () => {
    expect(isAppError('error')).toBe(false);
    expect(isAppError(null)).toBe(false);
    expect(isAppError(undefined)).toBe(false);
    expect(isAppError(42)).toBe(false);
    expect(isAppError({ message: 'test' })).toBe(false);
  });
});

// ── handleApiError ───────────────────────────────────────────────

describe('handleApiError', () => {
  it('should handle AppError instances', async () => {
    const error = new NotFoundError('Session', { session_id: 'abc123' });
    const response = handleApiError(error);
    expect(response.status).toBe(404);
    const body = await response.json();
    expect(body.error.code).toBe('NOT_FOUND');
    expect(body.error.message).toBe('Session not found');
    expect(body.error.details).toEqual({ session_id: 'abc123' });
  });

  it('should handle ValidationError via handleApiError', async () => {
    const error = new ValidationError('Missing required field');
    const response = handleApiError(error);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error.code).toBe('VALIDATION_ERROR');
  });

  it('should handle RateLimitError via handleApiError', async () => {
    const error = new RateLimitError();
    const response = handleApiError(error);
    expect(response.status).toBe(429);
  });

  it('should handle plain Error instances', async () => {
    const error = new Error('Something unexpected');
    const response = handleApiError(error);
    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.error.message).toBe('Something unexpected');
    expect(body.error.code).toBe('INTERNAL_ERROR');
  });

  it('should detect timeout errors from message patterns', async () => {
    const response = handleApiError(new Error('Request timeout: ETIMEDOUT'));
    expect(response.status).toBe(504);
    const body = await response.json();
    expect(body.error.code).toBe('TIMEOUT');
  });

  it('should detect rate limit errors from message patterns', async () => {
    const response = handleApiError(new Error('HTTP 429: rate limit exceeded'));
    expect(response.status).toBe(429);
    const body = await response.json();
    expect(body.error.code).toBe('RATE_LIMITED');
  });

  it('should handle non-Error thrown values', async () => {
    const response = handleApiError('string error');
    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.error.message).toBe('An unknown error occurred');
    expect(body.error.code).toBe('INTERNAL_ERROR');
  });

  it('should handle null error', async () => {
    const response = handleApiError(null);
    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.error.code).toBe('INTERNAL_ERROR');
  });

  it('should handle undefined error', async () => {
    const response = handleApiError(undefined);
    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.error.code).toBe('INTERNAL_ERROR');
  });

  it('should handle number error', async () => {
    const response = handleApiError(42);
    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.error.code).toBe('INTERNAL_ERROR');
  });

  it('should handle ZodError-like objects with issues', async () => {
    const zodLikeError = {
      issues: [
        { message: 'Required field missing' },
        { message: 'Invalid email format' },
      ],
    };
    const response = handleApiError(zodLikeError);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error.code).toBe('VALIDATION_ERROR');
    expect(body.error.details.issues).toEqual([
      'Required field missing',
      'Invalid email format',
    ]);
  });

  it('should always return a consistent JSON shape', async () => {
    const cases = [
      new AppError('test'),
      new Error('test'),
      'string',
      null,
      undefined,
      42,
      { foo: 'bar' },
    ];

    for (const error of cases) {
      const response = handleApiError(error);
      const body = await response.json();
      expect(body).toHaveProperty('error');
      expect(body.error).toHaveProperty('message');
      expect(body.error).toHaveProperty('code');
      expect(body.error).toHaveProperty('statusCode');
      expect(body.error).toHaveProperty('details');
    }
  });
});
