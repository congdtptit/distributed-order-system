// The one fetch wrapper of the screens. Every URL is absolute on the page's origin: the Vite
// server forwards /api/<service>/... to the service (vite.config.ts).

/** A response with a status outside 2xx; ``body`` is the parsed JSON, if any. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly body: unknown,
  ) {
    super(`HTTP ${status}`);
  }
}

/** The service did not answer at all (down, unreachable, timed out). */
export class NoAnswer extends Error {}

export interface Answer<T> {
  status: number;
  body: T;
}

export async function call<T>(path: string, init?: RequestInit): Promise<Answer<T>> {
  let response: Response;
  try {
    response = await fetch(new URL(path, window.location.origin), {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch (error) {
    throw new NoAnswer(String(error));
  }
  const text = await response.text();
  const body: unknown = text ? JSON.parse(text) : null;
  if (response.status === 502 || response.status === 503 || response.status === 504) {
    throw new NoAnswer(`HTTP ${response.status}`); // the Vite proxy found no service
  }
  if (!response.ok) throw new ApiError(response.status, body);
  return { status: response.status, body: body as T };
}

/** The ``message`` the services put in ``detail`` (section 6 of docs/02-detailed-design.md). */
export function detailMessage(body: unknown): string | null {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (detail && typeof detail === "object" && "message" in detail) {
      return String((detail as { message: unknown }).message);
    }
  }
  return null;
}
