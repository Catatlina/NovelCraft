/** 项目相关类型定义 */

/** 项目状态机阶段 */
export type ProjectState = 'idea' | 'outline' | 'world' | 'writing' | 'review' | 'publish';

/** 项目状态历史记录 */
export interface StateHistoryEntry {
  state: ProjectState;
  timestamp: string;
  note?: string;
}

/** 项目完整信息（匹配后端 novel_projects 表） */
export interface Project {
  id: string;
  user_id: string;
  title: string;
  target_platform: string;
  target_words: number;
  current_words: number;
  current_state: ProjectState;
  state_history: StateHistoryEntry[];
  outline: string | null;
  world_setting: string | null;
  meta?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

/** 创建项目请求 */
export interface ProjectCreate {
  title: string;
  target_platform?: string;
  target_words?: number;
}

/** 状态迁移请求 */
export interface TransitionRequest {
  target_state: ProjectState;
  reason?: string;
}

/** 大纲更新请求 */
export interface ProjectOutlineUpdate {
  overall_outline: string;
}

/** 世界观更新请求 */
export interface ProjectWorldUpdate {
  world_setting: string;
}
