/** 知识库相关类型定义 */

/** 知识条目 */
export interface KnowledgeEntry {
  id: string;
  project_id: string;
  title: string;
  content: string;
  category: string;
  tags: string[];
  source_chapter?: number;
  embedding_id?: string;
  created_at: string;
  updated_at: string;
}

/** 知识检索请求 */
export interface KnowledgeSearchRequest {
  query: string;
  project_id: string;
  top_k?: number;
  category?: string;
}

/** 知识检索结果 */
export interface KnowledgeSearchResult {
  entry: KnowledgeEntry;
  score: number;
  snippet: string;
}
