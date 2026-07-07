/**
 * API 端点函数 — 所有后端接口的 TypeScript 封装
 * 每个函数调用通用的 api<T>() 并带完整的请求/响应类型
 */
import { api } from '@/api/client';
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  User,
  Project,
  ProjectCreate,
  TransitionRequest,
  ProjectOutlineUpdate,
  ProjectWorldUpdate,
  Chapter,
  GenerateChapterRequest,
  Foreshadow,
  ForeshadowStats,
  PayoffCheckResult,
  QualityReview,
  ReviewRequest,
  RewriteRequest,
  HitAnalysisRequest,
  HitAnalysisResult,
  HitBenchmark,
  KnowledgeSearchRequest,
  KnowledgeSearchResult,
  BatchGenerateRequest,
  PipelineState,
} from '@/types';

// ============================================================
// Auth 认证
// ============================================================

export const authLogin = (data: LoginRequest): Promise<LoginResponse> =>
  api<LoginResponse>('/auth/login', 'POST', data);

export const authRegister = (data: RegisterRequest): Promise<LoginResponse> =>
  api<LoginResponse>('/auth/register', 'POST', data);

export const authMe = (): Promise<User> =>
  api<User>('/auth/me', 'GET');

export const authLogout = (): Promise<void> =>
  api<void>('/auth/logout', 'POST');

// ============================================================
// Project 项目
// ============================================================

export const projList = (): Promise<Project[]> =>
  api<Project[]>('/projects', 'GET');

export const projGet = (id: string): Promise<Project> =>
  api<Project>(`/projects/${id}`, 'GET');

export const projCreate = (data: ProjectCreate): Promise<Project> =>
  api<Project>('/projects', 'POST', data);

export const projDelete = (id: string): Promise<void> =>
  api<void>(`/projects/${id}`, 'DELETE');

export const projTransition = (id: string, data: TransitionRequest): Promise<Project> =>
  api<Project>(`/projects/${id}/transition`, 'POST', data);

export const projUpdateOutline = (id: string, data: ProjectOutlineUpdate): Promise<Project> =>
  api<Project>(`/projects/${id}/outline`, 'PUT', data);

export const projUpdateWorld = (id: string, data: ProjectWorldUpdate): Promise<Project> =>
  api<Project>(`/projects/${id}/world`, 'PUT', data);

export const projListChapters = (id: string): Promise<Chapter[]> =>
  api<Chapter[]>(`/projects/${id}/chapters`, 'GET');

// ============================================================
// Chapter 章节生成
// ============================================================

export const genChapter = (
  projectId: string,
  data: GenerateChapterRequest,
): Promise<Chapter> =>
  api<Chapter>(`/projects/${projectId}/generate`, 'POST', data);

export const pipelineBatch = (data: BatchGenerateRequest): Promise<PipelineState> =>
  api<PipelineState>('/pipeline/batch', 'POST', data);

export const pipelineStatus = (): Promise<PipelineState> =>
  api<PipelineState>('/pipeline/status', 'GET');

// ============================================================
// Tools 工具
// ============================================================

export const toolAnalyzeBook = (projectId: string): Promise<unknown> =>
  api<unknown>(`/tools/analyze/${projectId}`, 'POST');

export const toolDeslop = (chapterId: string): Promise<unknown> =>
  api<unknown>(`/tools/deslop/${chapterId}`, 'POST');

export const toolReview = (chapterId: string): Promise<unknown> =>
  api<unknown>(`/tools/review/${chapterId}`, 'POST');

// ============================================================
// Quality 质量分析
// ============================================================

export const qualityReview = (data: ReviewRequest): Promise<QualityReview> =>
  api<QualityReview>('/quality/review', 'POST', data);

export const qualityRewrite = (data: RewriteRequest): Promise<{ result: string }> =>
  api<{ result: string }>('/quality/rewrite', 'POST', data);

// ============================================================
// Foreshadow 伏笔
// ============================================================

export const fsList = (projectId: string): Promise<Foreshadow[]> =>
  api<Foreshadow[]>(`/foreshadows/${projectId}`, 'GET');

export const fsStats = (projectId: string): Promise<ForeshadowStats> =>
  api<ForeshadowStats>(`/foreshadows/${projectId}/stats`, 'GET');

export const fsCheckPayoff = (foreshadowId: string): Promise<PayoffCheckResult> =>
  api<PayoffCheckResult>(`/foreshadows/${foreshadowId}/check-payoff`, 'POST');

export const fsCheckOverdue = (projectId: string): Promise<Foreshadow[]> =>
  api<Foreshadow[]>(`/foreshadows/${projectId}/check-overdue`, 'POST');

// ============================================================
// Hit 爆款分析
// ============================================================

export const hitAnalyze = (projectId: string, data: HitAnalysisRequest): Promise<HitAnalysisResult> =>
  api<HitAnalysisResult>(`/hit/analyze/${projectId}`, 'POST', data);

export const hitBenchmarks = (platform?: string): Promise<HitBenchmark[]> =>
  api<HitBenchmark[]>(
    `/hit/benchmarks${platform ? `?platform=${encodeURIComponent(platform)}` : ''}`,
    'GET',
  );

// ============================================================
// Knowledge 知识库
// ============================================================

export const kbSearch = (data: KnowledgeSearchRequest): Promise<KnowledgeSearchResult[]> =>
  api<KnowledgeSearchResult[]>('/knowledge/search', 'POST', data);

export const kbIngest = (projectId: string): Promise<{ ingested: number }> =>
  api<{ ingested: number }>(`/knowledge/ingest/${projectId}`, 'POST');

// ============================================================
// Auto / AI 自动功能
// ============================================================

// 4-2: 自动书名生成
export const autoTitle = (
  genre: string,
  platform: string = '起点',
  count: number = 5,
): Promise<{ genre: string; platform: string; titles: string[] }> =>
  api<{ genre: string; platform: string; titles: string[] }>('/tools/auto/generate-title', 'POST', { genre, platform, count });

// 4-6: 灵感一键生成
export const autoInspiration = (
  idea: string,
  genre: string = '玄幻',
  platform: string = '起点',
): Promise<{ title: string; synopsis: string; outline: string; golden_three_outline: string; first_chapter: string }> =>
  api<{ title: string; synopsis: string; outline: string; golden_three_outline: string; first_chapter: string }>(
    '/tools/auto/inspiration-to-chapter',
    'POST',
    { idea, genre, platform },
  );

export const autoOutline = (projectId: string): Promise<{ outline: string }> =>
  api<{ outline: string }>(`/auto/outline/${projectId}`, 'POST');

// ============================================================
// Ops 运营
// ============================================================

export const opsDashboard = (): Promise<Record<string, unknown>> =>
  api<Record<string, unknown>>('/ops/dashboard', 'GET');

export const opsExport = (projectId: string, format: 'txt' | 'epub' | 'docx' = 'txt'): Promise<{ url: string }> =>
  api<{ url: string }>(`/ops/export/${projectId}?format=${format}`, 'POST');

// ============================================================
// Scan 扫描
// ============================================================

export const scanRun = (projectId: string): Promise<unknown> =>
  api<unknown>(`/scan/run/${projectId}`, 'POST');

export const scanPlatforms = (): Promise<string[]> =>
  api<string[]>('/scan/platforms', 'GET');

// ============================================================
// Translate 翻译
// ============================================================

export const translateChapter = (
  chapterId: string,
  platform: string,
  glossary?: Record<string, string>,
): Promise<{ translated_text: string }> =>
  api<{ translated_text: string }>(`/translate/chapter/${chapterId}`, 'POST', {
    platform,
    glossary,
  });

export const getTranslatePlatforms = (): Promise<Array<{ id: string; name: string; lang: string }>> =>
  api<Array<{ id: string; name: string; lang: string }>>('/translate/platforms', 'GET');

// ============================================================
// Analytics 分析
// ============================================================

export const getAnalyticsDashboard = (
  projectId?: string,
  timeRange?: string,
): Promise<Record<string, unknown>> => {
  const params: string[] = [];
  if (projectId) params.push(`project_id=${encodeURIComponent(projectId)}`);
  if (timeRange) params.push(`time_range=${encodeURIComponent(timeRange)}`);
  const query: string = params.length > 0 ? `?${params.join('&')}` : '';
  return api<Record<string, unknown>>(`/analytics/dashboard${query}`, 'GET');
};

// ============================================================
// Version 版本管理
// ============================================================

export const getChapterVersions = (
  chapterId: string,
): Promise<Array<{ id: string; version: number; created_at: string; summary: string }>> =>
  api<Array<{ id: string; version: number; created_at: string; summary: string }>>(
    `/chapters/${chapterId}/versions`,
    'GET',
  );

export const getVersionDiff = (
  chapterId: string,
  versionId: string,
): Promise<{ old_text: string; new_text: string }> =>
  api<{ old_text: string; new_text: string }>(
    `/chapters/${chapterId}/versions/${versionId}/diff`,
    'GET',
  );

export const restoreVersion = (
  chapterId: string,
  versionId: string,
): Promise<Chapter> =>
  api<Chapter>(`/chapters/${chapterId}/versions/${versionId}/restore`, 'POST');

export const createSnapshot = (
  chapterId: string,
): Promise<{ id: string; version: number }> =>
  api<{ id: string; version: number }>(`/chapters/${chapterId}/snapshot`, 'POST');

// ============================================================
// Search 全局搜索
// ============================================================

export const globalSearch = (
  query: string,
  type?: string,
  projectId?: string,
): Promise<{ results: unknown[]; total: number }> => {
  const params: string[] = [`q=${encodeURIComponent(query)}`];
  if (type) params.push(`type=${encodeURIComponent(type)}`);
  if (projectId) params.push(`project_id=${encodeURIComponent(projectId)}`);
  return api<{ results: unknown[]; total: number }>(
    `/search?${params.join('&')}`,
    'GET',
  );
};

// ============================================================
// Export 导出
// ============================================================

export const exportNovel = (
  projectId: string,
  format: 'txt' | 'epub' | 'docx' | 'pdf' = 'txt',
  options?: { chapters?: string[]; include_outline?: boolean },
): Promise<{ url: string }> =>
  api<{ url: string }>(`/export/${projectId}`, 'POST', { format, ...options });

// ============================================================
// A/B Test
// ============================================================

export const createABTest = (
  data: { project_id: string; name: string; variants: Array<{ name: string; content: string }> },
): Promise<{ id: string }> =>
  api<{ id: string }>('/ab-test', 'POST', data);

// ============================================================
// Platform Accounts 平台账号
// ============================================================

export const addPlatformAccount = (
  data: { platform: string; account_name: string; credentials?: Record<string, string> },
): Promise<{ id: string }> =>
  api<{ id: string }>('/platform-accounts', 'POST', data);

// ============================================================
// Publish 发布
// ============================================================

export const executePublish = (
  projectId: string,
  data: { platform: string; chapter_ids: string[]; scheduled_at?: string },
): Promise<{ execution_id: string; status: string }> =>
  api<{ execution_id: string; status: string }>(
    `/publish-executions/${projectId}`,
    'POST',
    data,
  );

// ============================================================
// Quality Benchmarks 质量基准
// ============================================================

export const getBenchmarks = (
  platform?: string,
  genre?: string,
): Promise<Array<{ id: string; platform: string; metric: string; value: number }>> => {
  const params: string[] = [];
  if (platform) params.push(`platform=${encodeURIComponent(platform)}`);
  if (genre) params.push(`genre=${encodeURIComponent(genre)}`);
  const query: string = params.length > 0 ? `?${params.join('&')}` : '';
  return api<Array<{ id: string; platform: string; metric: string; value: number }>>(
    `/quality-benchmarks${query}`,
    'GET',
  );
};

export const overrideBenchmark = (
  data: { platform: string; metric: string; value: number },
): Promise<{ id: string }> =>
  api<{ id: string }>('/benchmarks/override', 'POST', data);

// ============================================================
// Short Story 短篇生成
// ============================================================

export const generateShortStory = (
  projectId: string,
  premise: string,
  styleTags?: string[],
  targetWords?: number,
): Promise<{ chapter: Chapter }> =>
  api<{ chapter: Chapter }>('/generate/short', 'POST', {
    project_id: projectId,
    premise,
    style_tags: styleTags,
    target_words: targetWords,
  });

// ============================================================
// World Rules 世界观规则
// ============================================================

export const createWorldRule = (
  projectId: string,
  data: { rule_name: string; rule_type: string; description: string; dsl_expression: string; severity?: string },
): Promise<{ id: string }> =>
  api<{ id: string }>(`/projects/${projectId}/world-rules/rules`, 'POST', data);

export const getWorldRules = (
  projectId: string,
  activeOnly?: boolean,
): Promise<Array<Record<string, unknown>>> =>
  api<Array<Record<string, unknown>>>(`/projects/${projectId}/world-rules/rules${activeOnly ? '?active_only=true' : ''}`, 'GET');

export const updateWorldRule = (
  projectId: string,
  ruleId: string,
  data: Record<string, unknown>,
): Promise<Record<string, unknown>> =>
  api<Record<string, unknown>>(`/projects/${projectId}/world-rules/rules/${ruleId}`, 'PUT', data);

export const deleteWorldRule = (
  projectId: string,
  ruleId: string,
): Promise<void> =>
  api<void>(`/projects/${projectId}/world-rules/rules/${ruleId}`, 'DELETE');

export const validateWorldRules = (
  projectId: string,
  chapterText: string,
  chapterNum: number,
): Promise<{ violations: Array<Record<string, unknown>> }> =>
  api<{ violations: Array<Record<string, unknown>> }>(`/projects/${projectId}/world-rules/rules/validate`, 'POST', {
    chapter_text: chapterText,
    chapter_num: chapterNum,
  });

// ============================================================
// Prompt Optimization
// ============================================================

export const logPromptChange = (
  projectId: string,
  data: { prompt_name: string; params_before: Record<string, unknown>; params_after: Record<string, unknown>; reason: string },
): Promise<{ id: string }> =>
  api<{ id: string }>('/prompt-optimization/log', 'POST', { project_id: projectId, ...data });

export const getPromptHistory = (
  projectId: string,
): Promise<Array<Record<string, unknown>>> =>
  api<Array<Record<string, unknown>>>(`/prompt-optimization/history?project_id=${encodeURIComponent(projectId)}`, 'GET');
