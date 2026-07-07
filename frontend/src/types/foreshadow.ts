/** 伏笔相关类型定义 */

/** 伏笔状态 */
export type ForeshadowStatus = 'planted' | 'paid_off' | 'overdue';

/** 伏笔完整信息 */
export interface Foreshadow {
  id: string;
  project_id: string;
  content: string;
  planted_chapter: number;
  target_chapter: number | null;
  resolved_chapter: number | null;
  status: ForeshadowStatus;
  note: string | null;
  created_at: string;
  updated_at: string;
}

/** 伏笔统计数据 */
export interface ForeshadowStats {
  total: number;
  planted: number;
  paid_off: number;
  overdue: number;
  resolution_rate: number;
}

/** 伏笔回收检查结果 */
export interface PayoffCheckResult {
  foreshadow_id: string;
  is_paid_off: boolean;
  confidence: number;
  matched_chapter?: number;
  evidence?: string;
}
