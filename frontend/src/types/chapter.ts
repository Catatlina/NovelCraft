/** 章节相关类型定义 */

/** 章节状态 */
export type ChapterStatus = 'draft' | 'in_progress' | 'completed' | 'reviewed';

/** 章节完整信息 */
export interface Chapter {
  id: string;
  project_id: string;
  chapter_num: number;
  title: string;
  content: string;
  word_count: number;
  summary: string | null;
  review_score: number | null;
  status: ChapterStatus;
  volume?: string;
  created_at: string;
  updated_at: string;
}

/** 生成章节请求 */
export interface GenerateChapterRequest {
  chapter_num: number;
  title?: string;
  style_hint?: string;
  context_window?: number;
}
