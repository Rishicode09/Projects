/**
 * A lightweight Result type used across the service and repository layers so
 * callers handle failure explicitly instead of relying on thrown exceptions.
 */
export type Result<T, E = AppError> =
  | { ok: true; value: T }
  | { ok: false; error: E };

export interface AppError {
  code: string;
  message: string;
  cause?: unknown;
}

export const ok = <T>(value: T): Result<T, never> => ({ ok: true, value });

export const err = <E = AppError>(error: E): Result<never, E> => ({
  ok: false,
  error,
});

export function appError(code: string, message: string, cause?: unknown): AppError {
  return { code, message, cause };
}

/** Wraps a promise, converting thrown errors into a Result. */
export async function tryAsync<T>(
  fn: () => Promise<T>,
  code = 'unknown'
): Promise<Result<T>> {
  try {
    return ok(await fn());
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Unexpected error';
    return err(appError(code, message, e));
  }
}
