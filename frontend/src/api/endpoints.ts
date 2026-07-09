/**
 * API 端点函数 — 所有后端接口的 TypeScript 封装
 * 路径与后端路由严格对齐 (backend/app/api/* + main.py router prefixes)
 */
import { api } from '@/api/client';
import type {
  LoginRequest,
  LoginResponse,
  RefreshResponse,
  RegisterRequest,
  User,
  Project,
  ProjectCreate,
  TransitionRequest,
  ProjectOutlineUpdate,
  ProjectWorldUpdate,
  Chapter,
  ChapterSummary,
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

/** 显式手动刷新（一般不需要主动调用——client.ts 在收到 401 时会自动透明刷新一次并重放原请求）。
 *  纯靠 httpOnly 的 refresh_token cookie，不需要也读不到 cookie 的值。*/
export const authRefresh = (): Promise<RefreshResponse> =>
  api<RefreshResponse>('/auth/refresh', 'POST');

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

export const projListChapters = (
  id: string,
  params?: { limit?: number; offset?: number },
): Promise<ChapterSummary[]> => {
  const qs = new URLSearchParams();
  if (params?.limit !== undefined) qs.set('limit', String(params.limit));
  if (params?.offset !== undefined) qs.set('offset', String(params.offset));
  const suffix = qs.toString() ? `?${qs.toString()}` : '';
  return api<ChapterSummary[]>(`/projects/${id}/chapters${suffix}`, 'GET');
};

/** 单章完整详情（含正文），用于编辑器按需加载 */
export const getChapter = (chapterId: string): Promise<Chapter> =>
  api<Chapter>(`/chapters/${chapterId}`, 'GET');

// ============================================================
// Chapter 章节生成 (后端路径: /api/v1/projects/{id}/chapters/generate)
// ============================================================

export const genChapter = (
  projectId: string,
  data: GenerateChapterRequest,
): Promise<Chapter> =>
  api<Chapter>(`/projects/${projectId}/chapters/generate`, 'POST', data);

export const pipelineBatch = (data: BatchGenerateRequest): Promise<PipelineState> =>
  api<PipelineState>('/pipeline/batch-generate', 'POST', data);

export const pipelineStatus = (): Promise<PipelineState> =>
  api<PipelineState>('/pipeline/status', 'GET');

// ============================================================
// Tools 工具 (后端路径: /api/v1/tools/*)
// ============================================================

export const toolAnalyzeBook = (title: string, chapters: string, depth?: string): Promise<unknown> =>
  api<unknown>('/tools/analyze', 'POST', { title, chapters, depth });

export const toolDeslop = (content: string, mode?: string): Promise<unknown> =>
  api<unknown>('/tools/deslop', 'POST', { content, mode });

// ============================================================
// Quality 质量分析 (后端路径: /api/v1/quality/*)
// ============================================================

export const qualityReview = (data: ReviewRequest): Promise<QualityReview> =>
  api<QualityReview>('/quality/review', 'POST', data);

export const qualityRewrite = (data: RewriteRequest): Promise<{ rewritten: string; applied: boolean; message?: string | null }> =>
  api<{ rewritten: string; applied: boolean; message?: string | null }>('/quality/rewrite', 'POST', data);

// ============================================================
// Foreshadow 伏笔 (后端路径: /api/v1/foreshadows/*)
// ============================================================

export const fsList = (projectId: string): Promise<Foreshadow[]> =>
  api<Foreshadow[]>(`/foreshadows/project/${projectId}`, 'GET');

export const fsStats = (projectId: string): Promise<ForeshadowStats> =>
  api<ForeshadowStats>(`/foreshadows/stats/${projectId}`, 'GET');

export const fsCheckPayoff = (
  foreshadowId: string,
  chapterContent: string,
): Promise<PayoffCheckResult> =>
  api<PayoffCheckResult>(`/foreshadows/${foreshadowId}/check-payoff`, 'POST', {
    chapter_content: chapterContent,
  });

export const fsCheckOverdue = (projectId: string): Promise<{ checked: number; overdue: number }> =>
  api<{ checked: number; overdue: number }>(`/foreshadows/auto-check-overdue?project_id=${projectId}`, 'POST');

// ============================================================
// Hit 爆款分析 (后端路径: /api/v1/hit-analysis/*)
// ============================================================

export const hitAnalyze = (data: HitAnalysisRequest): Promise<HitAnalysisResult> =>
  api<HitAnalysisResult>('/hit-analysis/analyze', 'POST', data);

export const hitBenchmarks = (platform?: string): Promise<HitBenchmark[]> =>
  api<HitBenchmark[]>(
    `/quality-benchmarks${platform ? `?platform=${encodeURIComponent(platform)}` : ''}`,
    'GET',
  );

// ============================================================
// Knowledge 知识库 (后端路径: /api/v1/knowledge/*)
// ============================================================

export const kbSearch = (data: KnowledgeSearchRequest): Promise<KnowledgeSearchResult[]> =>
  api<KnowledgeSearchResult[]>('/knowledge/search', 'POST', data);

export const kbIngest = (projectId: string): Promise<{ ingested: number }> =>
  api<{ ingested: number }>('/knowledge/ingest', 'POST', { project_id: projectId });

// ============================================================
// Scan 扫描 (后端路径: /api/v1/scan/*)
// ============================================================

export const scanRun = (platforms?: string[]): Promise<unknown> =>
  api<unknown>('/scan/run', 'POST', { platforms });

export const scanPlatforms = (): Promise<{ platforms: unknown[]; total: number }> =>
  api<{ platforms: unknown[]; total: number }>('/scan/platforms', 'GET');

// ============================================================
// Translate 翻译 (后端路径: /api/v1/translate/*)
// ============================================================

export const translateChapter = (
  chapterId: string,
  targetPlatform: string,
  glossary?: Record<string, string>,
): Promise<{ translated_text: string; word_count?: number; cultural_notes?: string[] }> =>
  api<{ translated_text: string; word_count?: number; cultural_notes?: string[] }>(
    `/translate/chapter/${chapterId}`,  // 此前路径漏了chapter_id路径参数，调用必404
    'POST',
    {
      // 后端 TranslateRequest 的字段名是 target_platform；此前传 platform 会被
      // Pydantic 静默忽略并使用默认值 webnovel——用户选什么平台都没生效
      target_platform: targetPlatform,
      glossary,
    },
  );

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
// Ops 运营
// ============================================================

export const opsDashboard = (): Promise<Record<string, unknown>> =>
  api<Record<string, unknown>>('/ops/dashboard', 'GET');

export const opsExport = (projectId: string, format: 'txt' | 'epub' | 'docx' = 'txt'): Promise<{ url: string }> =>
  api<{ url: string }>('/ops/export', 'POST', { project_id: projectId, format });

// ============================================================
// Auto / AI 自动功能
// ============================================================

export const autoTitle = (
  genre: string,
  platform: string = '起点',
  count: number = 5,
): Promise<{ genre: string; platform: string; titles: string[] }> =>
  api<{ genre: string; platform: string; titles: string[] }>('/tools/auto/generate-title', 'POST', { genre, platform, count });

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

// ============================================================
// Additional endpoints needed by useApi.ts hooks
// ============================================================

export const autoOutline = (projectId: string): Promise<{ outline: string }> =>
  api<{ outline: string }>('/tools/auto/outline', 'POST', { project_id: projectId });

export const getChapterVersions = (
  chapterId: string,
): Promise<Array<{ id: string; version: number; created_at: string; summary: string }>> =>
  api<Array<{ id: string; version: number; created_at: string; summary: string }>>(`/chapters/${chapterId}/versions`, 'GET');

export const getVersionDiff = (
  chapterId: string,
  versionId: string,
): Promise<{ old_text: string; new_text: string }> =>
  api<{ old_text: string; new_text: string }>(`/chapters/${chapterId}/versions/${versionId}/diff`, 'GET');

export const restoreVersion = (chapterId: string, versionId: string): Promise<Chapter> =>
  api<Chapter>(`/chapters/${chapterId}/versions/${versionId}/restore`, 'POST');

export const createSnapshot = (chapterId: string): Promise<{ id: string; version: number }> =>
  api<{ id: string; version: number }>(`/chapters/${chapterId}/snapshot`, 'POST');

export const globalSearch = (
  query: string, type?: string, projectId?: string,
): Promise<{ results: unknown[]; total: number }> => {
  const params: string[] = [`q=${encodeURIComponent(query)}`];
  if (type) params.push(`type=${encodeURIComponent(type)}`);
  if (projectId) params.push(`project_id=${encodeURIComponent(projectId)}`);
  return api<{ results: unknown[]; total: number }>(`/search?${params.join('&')}`, 'GET');
};

export const exportNovel = (
  projectId: string, format: string = 'txt', options?: Record<string, unknown>,
): Promise<{ url: string }> =>
  api<{ url: string }>(`/ops/export/${projectId}`, 'POST', { format, ...options });

export const createABTest = (
  data: { project_id: string; name: string; variants: Array<{ name: string; content: string }> },
): Promise<{ id: string }> => api<{ id: string }>('/ab-tests/create', 'POST', data);

export const addPlatformAccount = (
  data: { platform: string; auth_method: 'oauth' | 'cookie'; account_name: string; credentials?: Record<string, string>; expires_at?: string },
): Promise<{ id: string }> => api<{ id: string }>('/platform-accounts/platform', 'POST', data);

export const executePublish = (
  projectId: string, data: { platform: string; chapter_ids: string[]; scheduled_at?: string },
): Promise<{ execution_id: string; status: string }> =>
  api<{ execution_id: string; status: string }>(`/publish-executions/${projectId}/execute`, 'POST', data);

export const getBenchmarks = (
  platform?: string, genre?: string,
): Promise<Array<{ id: string; platform: string; metric: string; value: number }>> => {
  const params: string[] = [];
  if (platform) params.push(`platform=${encodeURIComponent(platform)}`);
  if (genre) params.push(`genre=${encodeURIComponent(genre)}`);
  return api<Array<{ id: string; platform: string; metric: string; value: number }>>(`/quality-benchmarks/benchmarks?${params.join('&')}`, 'GET');
};

export const overrideBenchmark = (
  data: { platform: string; metric: string; value: number },
): Promise<{ id: string }> => api<{ id: string }>('/quality-benchmarks/benchmarks/override', 'POST', data);
