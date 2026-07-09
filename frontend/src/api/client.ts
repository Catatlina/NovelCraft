/**
 * HTTP 客户端 — 封装 fetch，统一处理认证、错误与 toasts
 * 使用 httpOnly cookie 认证，不存储 JWT 到 localStorage
 */
export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8100/api/v1';

/** 简易 toast 通知 */
const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info'): void => {
  const event = new CustomEvent('novelcraft-toast', {
    detail: { message, type },
  });
  window.dispatchEvent(event);
};

/** API 错误 */
export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}


function getCookie(name: string): string | null {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = document.cookie.match(new RegExp(`(?:^|; )${escaped}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

// 避免并发场景下多个401同时触发多次刷新请求：所有请求共享同一个进行中的刷新Promise。
let refreshInFlight: Promise<boolean> | null = null;

/** 用 httpOnly cookie 里的 refresh_token 换取新的 access_token；成功返回 true。*/
async function tryRefreshToken(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    })
      .then((res) => res.ok)
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

/** 通用 HTTP 请求函数 */
async function api<T>(
  path: string,
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' = 'GET',
  body?: unknown,
  options?: { headers?: Record<string, string>; timeout?: number; _isRetry?: boolean; signal?: AbortSignal },
): Promise<T> {
  const url: string = `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers || {}),
  };

  // DeepSeek API Key 从服务端配置读取（不再从前端 localStorage）。
  // Cookie 认证的写请求统一带 CSRF header。
  if (method !== 'GET') {
    const csrf = getCookie('csrf_token');
    if (csrf) headers['X-CSRF-Token'] = csrf;
  }

  const controller = new AbortController();
  const timeoutId: ReturnType<typeof setTimeout> = setTimeout(
    () => controller.abort(),
    options?.timeout || 60000,
  );

  try {
    const res: Response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: options?.signal || controller.signal,
      credentials: 'include',  // httpOnly cookie 认证
    });

    clearTimeout(timeoutId);

    if (res.status === 204) {
      return undefined as T;
    }

    const data: unknown = await res.json().catch(() => null);

    if (!res.ok) {
      const detail: unknown = (data && typeof data === 'object' && 'detail' in (data as Record<string, unknown>))
        ? (data as Record<string, unknown>).detail
        : data;
      const msg: string = (detail && typeof detail === 'string')
        ? detail
        : `请求失败 (${res.status})`;

      // access_token 过期(401)时，尝试用 httpOnly 的 refresh_token cookie 静默换新，
      // 成功后原样重放一次原请求；避免对 /auth/* 自身的请求做刷新重试造成死循环。
      if (res.status === 401 && !options?._isRetry && !path.startsWith('/auth/')) {
        const refreshed = await tryRefreshToken();
        if (refreshed) {
          return api<T>(path, method, body, { ...options, _isRetry: true });
        }
      }

      throw new ApiError(res.status, msg, detail);
    }

    return data as T;
  } catch (err: unknown) {
    clearTimeout(timeoutId);

    if (err instanceof ApiError) {
      throw err;
    }

    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(0, '请求超时，请稍后重试');
    }

    if (err instanceof TypeError) {
      showToast('后端服务未启动或无法连接', 'error');
      throw new ApiError(0, '后端服务未启动，请稍后重试');
    }

    throw new ApiError(0, '未知错误');
  }
}

export { api, showToast };
