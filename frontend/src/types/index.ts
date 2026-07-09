/** 类型定义总入口 — 从各模块重新导出所有类型 */

export type { User, LoginRequest, LoginResponse, RefreshResponse, RegisterRequest } from './auth';
export type {
  ProjectState,
  StateHistoryEntry,
  Project,
  ProjectCreate,
  TransitionRequest,
  ProjectOutlineUpdate,
  ProjectWorldUpdate,
} from './project';
export type { ChapterStatus, Chapter, ChapterSummary, GenerateChapterRequest } from './chapter';
export type {
  ForeshadowStatus,
  Foreshadow,
  ForeshadowStats,
  PayoffCheckResult,
} from './foreshadow';
export type {
  QualityDimension,
  DimensionScore,
  QualityReview,
  ReviewRequest,
  RewriteRequest,
} from './quality';
export type {
  HitAnalysisRequest,
  HitBenchmark,
  HitAnalysisResult,
} from './hit';
export type {
  KnowledgeEntry,
  KnowledgeSearchRequest,
  KnowledgeSearchResult,
} from './knowledge';
export type {
  PipelineStatus,
  BatchTask,
  BatchGenerateRequest,
  PipelineState,
} from './pipeline';
