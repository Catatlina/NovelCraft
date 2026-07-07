/**
 * HTTP 客户端 — 封装 fetch，统一处理 JWT、错误与 toasts
 */

/** 获取 API 基地址 */
const getApiBase = (): string => {
  try {
    const stored: string | null = localStorage.getItem('novelcraft-api-base');
    return stored || 'http://localhost:8100/api/v1';
  } catch {
    return 'http://localhost:8100/api/v1';
  }
};

/** 获取 JWT token */
const getToken = (): string | null => {
  try {
    return localStorage.getItem('novelcraft-token');
  } catch {
    return null;
  }
};

/** 简易 toast 通知（后续可替换为成熟方案） */
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

/** 通用 HTTP 请求函数 */
async function api<T>(
  path: string,
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' = 'GET',
  body?: unknown,
  options?: { headers?: Record<string, string>; timeout?: number },
): Promise<T> {
  const base: string = getApiBase();
  const url: string = `${base}${path.startsWith('/') ? path : `/${path}`}`;
  const token: string | null = getToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // 发送 DeepSeek API Key + Model（前端配置，后端从 header 读取）
  try {
    const dsKey = localStorage.getItem('novelcraft-deepseek-key');
    if (dsKey) headers['X-DeepSeek-API-Key'] = dsKey;
    const dsModel = localStorage.getItem('novelcraft-deepseek-model');
    if (dsModel) headers['X-DeepSeek-Model'] = dsModel;
  } catch {}

  const controller = new AbortController();
  const timeoutId: ReturnType<typeof setTimeout> = setTimeout(
    () => controller.abort(),
    options?.timeout || 30000,
  );

  try {
    const res: Response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // 204 No Content
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

      if (res.status === 401) {
        localStorage.removeItem('novelcraft-token');
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

export { api, getApiBase, getToken, showToast };
