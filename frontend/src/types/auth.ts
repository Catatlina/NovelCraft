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
  access_token: string;
  token_type: string;
  user: User;
}

/** 注册请求 */
export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
}
