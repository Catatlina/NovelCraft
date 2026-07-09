/** 章节相关类型定义 */

/** 章节状态 */
export type ChapterStatus = 'draft' | 'in_progress' | 'completed' | 'reviewed';

/** 章节完整信息（含正文）— 通过 GET /chapters/{id} 获取 */
export interface Chapter {
  id: string;
  project_id: string;
  chapter_num: number;
  title: string;
  content: string;
  word_count: number;
  summary: string | null;
  /** 0-100 综合评分，来自最近一次7维审查；未审查过则为 null */
  overall_score: number | null;
  status: ChapterStatus;
  volume?: string;
  created_at: string;
  updated_at: string;
}

/** 章节摘要（不含正文）— 列表接口 GET /projects/{id}/chapters 返回，用于导航栏/章节树展示 */
export interface ChapterSummary {
  id: string;
  chapter_num: number;
  title: string;
  word_count: number;
  summary: string | null;
  overall_score: number | null;
  status: ChapterStatus;
  volume?: string;
  created_at: string;
}

/** 生成章节请求 */
export interface GenerateChapterRequest {
  mode?: 'continue' | 'first_chapter';
}
