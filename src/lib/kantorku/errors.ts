/**
 * KantorKu Error Classes & Utilities
 *
 * Standardized error handling for the KantorKu application.
 * All custom errors extend AppError for consistent error handling.
 */

import { NextResponse } from 'next/server';
import { logger } from './logger';

// ── Error Code Constants ─────────────────────────────────────────

export const ErrorCode = {
  VALIDATION: 'VALIDATION_ERROR',
  NOT_FOUND: 'NOT_FOUND',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  RATE_LIMITED: 'RATE_LIMITED',
  TIMEOUT: 'TIMEOUT',
  BUDGET_EXCEEDED: 'BUDGET_EXCEEDED',
  INTERNAL: 'INTERNAL_ERROR',
} as const;

export type ErrorCodeType = (typeof ErrorCode)[keyof typeof ErrorCode];

// ── Base AppError ────────────────────────────────────────────────

export class AppError extends Error {
  public readonly statusCode: number;
  public readonly code: string;
  public readonly details?: Record<string, unknown>;
  public readonly isOperational: boolean;

  constructor(
    message: string,
    statusCode: number = 500,
    code: string = ErrorCode.INTERNAL,
    details?: Record<string, unknown>,
    isOperational: boolean = true
  ) {
    super(message);
    this.name = 'AppError';
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
    this.isOperational = isOperational;

    // Maintain proper stack trace in V8 environments
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }

  /** Convert to a NextResponse for API route error handling */
  toResponse(): NextResponse {
    return NextResponse.json(
      {
        error: {
          message: this.message,
          code: this.code,
          statusCode: this.statusCode,
          details: this.details ?? null,
        },
      },
      { status: this.statusCode }
    );
  }
}

// ── Specific Error Subclasses ────────────────────────────────────

export class ValidationError extends AppError {
  constructor(message: string = 'Validation failed', details?: Record<string, unknown>) {
    super(message, 400, ErrorCode.VALIDATION, details);
    this.name = 'ValidationError';
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string, details?: Record<string, unknown>) {
    super(`${resource} not found`, 404, ErrorCode.NOT_FOUND, details);
    this.name = 'NotFoundError';
  }
}

export class UnauthorizedError extends AppError {
  constructor(message: string = 'Authentication required', details?: Record<string, unknown>) {
    super(message, 401, ErrorCode.UNAUTHORIZED, details);
    this.name = 'UnauthorizedError';
  }
}

export class ForbiddenError extends AppError {
  constructor(message: string = 'Access denied', details?: Record<string, unknown>) {
    super(message, 403, ErrorCode.FORBIDDEN, details);
    this.name = 'ForbiddenError';
  }
}

export class RateLimitError extends AppError {
  public readonly retryAfterMs: number;

  constructor(message: string = 'Rate limit exceeded', retryAfterMs: number = 5000, details?: Record<string, unknown>) {
    super(message, 429, ErrorCode.RATE_LIMITED, details);
    this.name = 'RateLimitError';
    this.retryAfterMs = retryAfterMs;
  }

  override toResponse(): NextResponse {
    return NextResponse.json(
      {
        error: {
          message: this.message,
          code: this.code,
          statusCode: this.statusCode,
          details: { ...this.details, retry_after_ms: this.retryAfterMs },
        },
      },
      { status: this.statusCode }
    );
  }
}

export class TimeoutError extends AppError {
  constructor(message: string = 'Request timed out', details?: Record<string, unknown>) {
    super(message, 504, ErrorCode.TIMEOUT, details);
    this.name = 'TimeoutError';
  }
}

export class BudgetExceededError extends AppError {
  public readonly budget: number;
  public readonly estimatedCost: number;

  constructor(budget: number, estimatedCost: number, message?: string, details?: Record<string, unknown>) {
    const autoMessage = message || `Estimated cost $${estimatedCost.toFixed(4)} exceeds budget limit $${budget.toFixed(4)}`;
    super(autoMessage, 403, ErrorCode.BUDGET_EXCEEDED, {
      ...details,
      budget,
      estimated_cost: estimatedCost,
    });
    this.name = 'BudgetExceededError';
    this.budget = budget;
    this.estimatedCost = estimatedCost;
  }
}

export class InternalError extends AppError {
  constructor(message: string = 'Internal server error', details?: Record<string, unknown>) {
    super(message, 500, ErrorCode.INTERNAL, details);
    this.name = 'InternalError';
  }
}

// ── Utility Functions ────────────────────────────────────────────

/** Type guard to check if an error is an AppError */
export function isAppError(error: unknown): error is AppError {
  return error instanceof AppError;
}

/**
 * Handle unknown errors in API routes, returning a consistent NextResponse.
 *
 * Handles:
 * - AppError → calls toResponse()
 * - ZodError → ValidationError with issue messages
 * - Native Error → heuristic matching (timeout, rate-limit patterns)
 * - Unknown → InternalError
 */
export function handleApiError(error: unknown, context?: string): NextResponse {
  // 1. Already an AppError — just convert
  if (isAppError(error)) {
    logger.error(context ?? 'api', error.message, error);
    return error.toResponse();
  }

  // 2. ZodError — validation error with issue messages
  if (typeof error === 'object' && error !== null && 'issues' in error && Array.isArray((error as { issues: unknown }).issues)) {
    const zodError = error as { issues: Array<{ message: string }> };
    logger.warn(context ?? 'api', 'Validation error', zodError.issues);
    return new ValidationError(
      'Validation failed',
      { issues: zodError.issues.map((i) => i.message) }
    ).toResponse();
  }

  // 3. Native Error — heuristic matching
  if (error instanceof Error) {
    const message = error.message;

    // Timeout patterns
    if (message.includes('timeout') || message.includes('ETIMEDOUT')) {
      logger.warn(context ?? 'api', 'Timeout error', message);
      return new TimeoutError(message).toResponse();
    }

    // Rate limit patterns
    if (message.includes('429') || message.toLowerCase().includes('rate limit')) {
      logger.warn(context ?? 'api', 'Rate limit error', message);
      return new RateLimitError(message).toResponse();
    }

    // Generic error
    logger.error(context ?? 'api', message, error);
    return new InternalError(message).toResponse();
  }

  // 4. Completely unknown error type
  logger.error(context ?? 'api', 'Unknown error', error);
  return new InternalError('An unknown error occurred').toResponse();
}
