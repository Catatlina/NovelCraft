/** 质量分析相关类型定义 */

/** 质量评估维度（7 维度） */
export type QualityDimension =
  | 'readability'
  | 'pacing'
  | 'logic'
  | 'character'
  | 'emotion'
  | 'style'
  | 'foreshadow';

/** 维度详细评分 */
export interface DimensionScore {
  name: QualityDimension;
  label: string;
  score: number; // 0-100
  issues: string[];
  suggestions: string[];
}

/** 质量评审结果 */
export interface QualityReview {
  id: string;
  project_id: string;
  chapter_id: string;
  overall_score: number;
  dimensions: DimensionScore[];
  summary: string;
  created_at: string;
}

/** 质量评审请求 */
export interface ReviewRequest {
  chapter_id: string;
  project_id: string;
  scope?: QualityDimension[];
}

/** AI 改写请求 */
export interface RewriteRequest {
  chapter_id: string;
  project_id: string;
  instruction: string;
  scope?: 'sentence' | 'paragraph' | 'chapter';
  target_dimension?: QualityDimension;
}
