/**
 * Result type — explicit error handling via tagged union.
 *
 * Discriminated union for representing success/failure without exceptions.
 * New pure functions should use Result instead of throwing.
 */

export type Result<T, E = string> =
  | { readonly ok: true; readonly value: T }
  | { readonly ok: false; readonly error: E };

export const Ok = <T>(value: T): Result<T, never> => ({ ok: true, value });
export const Err = <E>(error: E): Result<never, E> => ({ ok: false, error });

export function mapResult<T, U, E>(
  r: Result<T, E>,
  f: (v: T) => U,
): Result<U, E> {
  return r.ok ? Ok(f(r.value)) : r;
}

export function flatMapResult<T, U, E>(
  r: Result<T, E>,
  f: (v: T) => Result<U, E>,
): Result<U, E> {
  return r.ok ? f(r.value) : r;
}

export function unwrapOr<T, E>(r: Result<T, E>, fallback: T): T {
  return r.ok ? r.value : fallback;
}
