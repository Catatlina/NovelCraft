/** 流水线相关类型定义 */

/** 流水线任务状态 */
export type PipelineStatus = 'idle' | 'running' | 'completed' | 'failed';

/** 批量生成子任务 */
export interface BatchTask {
  chapter_num: number;
  status: PipelineStatus;
  title?: string;
  word_count?: number;
  error?: string;
}

/** 批量生成请求 */
export interface BatchGenerateRequest {
  project_id: string;
  start_chapter: number;
  end_chapter: number;
  style_hint?: string;
}

/** 流水线状态详情 */
export interface PipelineState {
  status: PipelineStatus;
  project_id: string;
  tasks: BatchTask[];
  total: number;
  completed: number;
  failed: number;
  started_at?: string;
  estimated_remaining_seconds?: number;
}
