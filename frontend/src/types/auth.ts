/** 用户认证相关类型定义 */

/** 用户信息 */
export interface User {
  id: string;
  username: string;
  email: string;
  avatar_url?: string;
  plan?: string;
  created_at: string;
}

/** 登录请求 */
export interface LoginRequest {
  username: string;
  password: string;
}

/** 登录响应 */
export interface LoginResponse {
  user: User;
}

export interface RefreshResponse {
  status: string;
}

/** 注册请求 */
export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
}
