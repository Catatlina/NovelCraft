/** 爆款分析相关类型定义 */

/** 爆款分析请求 */
export interface HitAnalysisRequest {
  title: string;
  outline?: string;
  tags?: string[];
  target_platform?: string;
  sample_text?: string;
}

/** 对标爆款书籍 */
export interface HitBenchmark {
  id: string;
  title: string;
  author: string;
  platform: string;
  hot_score: number;
  read_count: number;
  tags: string[];
  similarity: number;
  highlights: string[];
  url?: string;
}

/** 爆款分析结果 */
export interface HitAnalysisResult {
  id: string;
  project_id: string;
  overall_hit_score: number;
  benchmarks: HitBenchmark[];
  suggestions: string[];
  created_at: string;
}
