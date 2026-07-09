/**
 * TanStack React Query Hooks
 * 封装所有 API 调用的查询 (useQuery) 和变更 (useMutation)
 */
import { useQuery, useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';
import {
  projList,
  projGet,
  projCreate,
  projDelete,
  projTransition,
  projUpdateOutline,
  projUpdateWorld,
  projListChapters,
  getChapter,
  genChapter,
  pipelineBatch,
  pipelineStatus,
  toolAnalyzeBook,
  toolDeslop,
  qualityReview,
  qualityRewrite,
  fsList,
  fsStats,
  fsCheckPayoff,
  fsCheckOverdue,
  hitAnalyze,
  hitBenchmarks,
  kbSearch,
  kbIngest,
  autoInspiration,
  autoTitle,
  autoOutline,
  opsDashboard,
  opsExport,
  scanRun,
  scanPlatforms,
  translateChapter,
  getTranslatePlatforms,
  getAnalyticsDashboard,
  getChapterVersions,
  getVersionDiff,
  restoreVersion,
  createSnapshot,
  globalSearch,
  exportNovel,
  createABTest,
  addPlatformAccount,
  executePublish,
  getBenchmarks,
  overrideBenchmark,
} from '@/api/endpoints';
import type {
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
  ForeshadowStatus,
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
// Query Keys
// ============================================================

export const queryKeys = {
  projects: ['projects'] as const,
  project: (id: string) => ['projects', id] as const,
  chapters: (projectId: string) => ['projects', projectId, 'chapters'] as const,
  foreshadows: (projectId: string) => ['projects', projectId, 'foreshadows'] as const,
  foreshadowStats: (projectId: string) => ['projects', projectId, 'foreshadow-stats'] as const,
  pipelineStatus: ['pipeline', 'status'] as const,
  knowledgeSearch: (projectId: string, query: string) => ['knowledge', projectId, query] as const,
  opsDashboard: ['ops', 'dashboard'] as const,
  qualityBenchmarks: (platform?: string) => ['quality', 'benchmarks', platform] as const,
  hitBenchmarks: (platform?: string) => ['hit', 'benchmarks', platform] as const,
  analyticsDashboard: (projectId?: string, timeRange?: string) =>
    ['analytics', 'dashboard', projectId, timeRange] as const,
  chapterVersions: (chapterId: string) => ['chapters', chapterId, 'versions'] as const,
  versionDiff: (chapterId: string, versionId: string) =>
    ['chapters', chapterId, 'versions', versionId, 'diff'] as const,
  globalSearch: (query: string, type?: string, projectId?: string) =>
    ['search', query, type, projectId] as const,
  translatePlatforms: ['translate', 'platforms'] as const,
  qualityBenchmarksFiltered: (platform?: string, genre?: string) =>
    ['quality', 'benchmarks', platform, genre] as const,
};

// ============================================================
// Query Hooks (Read)
// ============================================================

/** 项目列表 */
export function useProjects() {
  return useQuery<Project[]>({
    queryKey: queryKeys.projects,
    queryFn: projList,
    staleTime: 1000 * 60,
  });
}

/** 单个项目详情 */
export function useProject(id: string | undefined) {
  return useQuery<Project>({
    queryKey: queryKeys.project(id || ''),
    queryFn: () => projGet(id!),
    enabled: !!id,
    staleTime: 1000 * 30,
  });
}

/** 项目章节列表 */
export function useChapters(projectId: string | undefined) {
  return useQuery<ChapterSummary[]>({
    queryKey: queryKeys.chapters(projectId || ''),
    queryFn: () => projListChapters(projectId!),
    enabled: !!projectId,
    staleTime: 1000 * 30,
  });
}

/** 单章完整详情（含正文），供编辑器按需加载当前正在查看的那一章。
 *  P0-1 fix 的一部分：列表接口(useChapters)不再带正文，编辑器改用这个
 *  hook 单独按 chapterId 拉取。*/
export function useChapter(chapterId: string | undefined) {
  return useQuery<Chapter>({
    queryKey: ['chapter', chapterId],
    queryFn: () => getChapter(chapterId!),
    enabled: !!chapterId,
    staleTime: 1000 * 10,
  });
}

/** 伏笔列表 */
export function useForeshadows(projectId: string | undefined, status?: ForeshadowStatus) {
  return useQuery<Foreshadow[]>({
    queryKey: [...queryKeys.foreshadows(projectId || ''), status],
    queryFn: () => fsList(projectId!),
    enabled: !!projectId,
    select: status
      ? (data: Foreshadow[]) => data.filter((f: Foreshadow) => f.status === status)
      : undefined,
    staleTime: 1000 * 30,
  });
}

/** 伏笔统计 */
export function useForeshadowStats(projectId: string | undefined) {
  return useQuery<ForeshadowStats>({
    queryKey: queryKeys.foreshadowStats(projectId || ''),
    queryFn: () => fsStats(projectId!),
    enabled: !!projectId,
  });
}

/** 流水线状态（轮询 5 秒） */
export function usePipelineStatus() {
  return useQuery<PipelineState>({
    queryKey: queryKeys.pipelineStatus,
    queryFn: pipelineStatus,
    refetchInterval: 5000,
  });
}

/** 知识检索 */
export function useKnowledgeSearch(projectId: string | undefined, query: string) {
  return useQuery<KnowledgeSearchResult[]>({
    queryKey: queryKeys.knowledgeSearch(projectId || '', query),
    queryFn: () => kbSearch({ query, project_id: projectId! }),
    enabled: !!projectId && query.length > 1,
  });
}

/** 运营仪表盘 */
export function useOpsDashboard() {
  return useQuery<Record<string, unknown>>({
    queryKey: queryKeys.opsDashboard,
    queryFn: () => opsDashboard().catch(() => ({} as Record<string, unknown>)),
    placeholderData: {} as Record<string, unknown>,
    staleTime: 1000 * 60 * 5,
  });
}

/** 爆款对标数据 */
export function useQualityBenchmarks(platform?: string) {
  return useQuery<HitBenchmark[]>({
    queryKey: queryKeys.qualityBenchmarks(platform),
    queryFn: () => hitBenchmarks(platform),
    staleTime: 1000 * 60 * 10,
  });
}

/** 反馈摘要（使用 hit benchmarks 作为代理） */
export function useFeedbackSummary(projectId: string | undefined) {
  return useQuery<HitBenchmark[]>({
    queryKey: [...queryKeys.qualityBenchmarks(), 'feedback', projectId],
    queryFn: () => hitBenchmarks(),
    enabled: !!projectId,
    staleTime: 1000 * 60 * 10,
  });
}

// ============================================================
// Mutation Hooks (Write)
// ============================================================

/** 创建项目 */
export function useCreateProject(): UseMutationResult<Project, Error, ProjectCreate> {
  const qc = useQueryClient();
  return useMutation<Project, Error, ProjectCreate>({
    mutationFn: projCreate,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });
}

/** 生成章节 */
export function useGenerateChapter(projectId: string) {
  const qc = useQueryClient();
  return useMutation<Chapter, Error, GenerateChapterRequest>({
    mutationFn: (data: GenerateChapterRequest) => genChapter(projectId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.chapters(projectId) });
    },
  });
}

/** 项目状态迁移 */
export function useTransitionProject(projectId: string) {
  const qc = useQueryClient();
  return useMutation<Project, Error, TransitionRequest>({
    mutationFn: (data: TransitionRequest) => projTransition(projectId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.project(projectId) });
      qc.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });
}

/** 质量评审 */
export function useQualityReview() {
  return useMutation<QualityReview, Error, ReviewRequest>({
    mutationFn: qualityReview,
  });
}

/** AI 改写 */
export function useQualityRewrite() {
  return useMutation<{ rewritten: string; applied: boolean; message?: string | null }, Error, RewriteRequest>({
    mutationFn: qualityRewrite,
  });
}

/** 爆款分析 */
export function useHitAnalyze(_projectId: string) {
  return useMutation<HitAnalysisResult, Error, HitAnalysisRequest>({
    mutationFn: (data: HitAnalysisRequest) => hitAnalyze(data),
  });
}

/** 批量生成 */
export function useBatchGenerate() {
  const qc = useQueryClient();
  return useMutation<PipelineState, Error, BatchGenerateRequest>({
    mutationFn: pipelineBatch,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.pipelineStatus });
    },
  });
}

/** 平台扫描 */
export function useScanRun() {
  return useMutation<unknown, Error, string[] | undefined>({
    mutationFn: (platforms?: string[]) => scanRun(platforms),
  });
}

/** 去口语化 */
export function useDeslop() {
  return useMutation<unknown, Error, { content: string; mode?: string }>({
    mutationFn: ({ content, mode }) => toolDeslop(content, mode),
  });
}

/** 全书分析 */
export function useAnalyzeBook() {
  return useMutation<unknown, Error, { title: string; chapters: string; depth?: string }>({
    mutationFn: ({ title, chapters, depth }) => toolAnalyzeBook(title, chapters, depth),
  });
}

/** 伏笔回收检查 */
export function useCheckPayoff(foreshadowId: string) {
  return useMutation<PayoffCheckResult, Error, string>({
    mutationFn: (chapterContent: string) => fsCheckPayoff(foreshadowId, chapterContent),
  });
}

/** 伏笔逾期检查 */
export function useAutoCheckOverdue(projectId: string) {
  const qc = useQueryClient();
  return useMutation<{ checked: number; overdue: number }, Error, void>({
    mutationFn: () => fsCheckOverdue(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.foreshadows(projectId) });
    },
  });
}

/** 灵感一键生成 */
export function useAutoInspiration() {
  return useMutation<
    { title: string; synopsis: string; outline: string; golden_three_outline: string; first_chapter: string },
    Error,
    { idea: string; genre?: string; platform?: string }
  >({
    mutationFn: ({ idea, genre = '玄幻', platform = '起点' }) => autoInspiration(idea, genre, platform),
  });
}

/** 自动书名生成 */
export function useAutoTitle() {
  return useMutation<
    { genre: string; platform: string; titles: string[] },
    Error,
    { genre: string; platform?: string; count?: number }
  >({
    mutationFn: ({ genre, platform = '起点', count = 5 }) => autoTitle(genre, platform, count),
  });
}

/** 大纲生成 */
export function useAutoOutline(projectId: string) {
  const qc = useQueryClient();
  return useMutation<{ outline: string }, Error, void>({
    mutationFn: () => autoOutline(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.project(projectId) });
    },
  });
}

/** 知识检索（Mutation 版，供回车触发） */
export function useKbSearch() {
  return useMutation<KnowledgeSearchResult[], Error, KnowledgeSearchRequest>({
    mutationFn: kbSearch,
  });
}

/** 知识注入 */
export function useKbIngest(projectId: string) {
  return useMutation<{ ingested: number }, Error, void>({
    mutationFn: () => kbIngest(projectId),
  });
}

/** 删除项目 */
export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: projDelete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });
}

/** 更新大纲 */
export function useUpdateOutline(projectId: string) {
  const qc = useQueryClient();
  return useMutation<Project, Error, ProjectOutlineUpdate>({
    mutationFn: (data: ProjectOutlineUpdate) => projUpdateOutline(projectId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.project(projectId) });
    },
  });
}

/** 更新世界观 */
export function useUpdateWorld(projectId: string) {
  const qc = useQueryClient();
  return useMutation<Project, Error, ProjectWorldUpdate>({
    mutationFn: (data: ProjectWorldUpdate) => projUpdateWorld(projectId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.project(projectId) });
    },
  });
}

/** 导出项目 */
export function useExportProject(projectId: string) {
  return useMutation<{ url: string }, Error, 'txt' | 'epub' | 'docx'>({
    mutationFn: (format: 'txt' | 'epub' | 'docx') => opsExport(projectId, format),
  });
}

/** 获取扫描平台列表 */
export function useScanPlatforms() {
  return useQuery<{ platforms: unknown[]; total: number }>({
    queryKey: ['scan', 'platforms'],
    queryFn: scanPlatforms,
    staleTime: Infinity,
  });
}

// ============================================================
// Translate 翻译 Hooks
// ============================================================

/** 翻译章节 */
export function useTranslateChapter(chapterId: string) {
  return useMutation<
    { translated_text: string; word_count?: number; cultural_notes?: string[] },
    Error,
    { target_platform: string; glossary?: Record<string, string> }
  >({
    mutationFn: (data) => translateChapter(chapterId, data.target_platform, data.glossary),
  });
}

/** 获取翻译平台列表 */
export function useTranslatePlatforms() {
  return useQuery<Array<{ id: string; name: string; lang: string }>>({
    queryKey: queryKeys.translatePlatforms,
    queryFn: getTranslatePlatforms,
    staleTime: Infinity,
  });
}

// ============================================================
// Analytics 分析 Hooks
// ============================================================

/** 分析仪表盘数据 */
export function useAnalyticsDashboard(projectId?: string, timeRange?: string) {
  return useQuery<Record<string, unknown>>({
    queryKey: queryKeys.analyticsDashboard(projectId, timeRange),
    queryFn: () => getAnalyticsDashboard(projectId, timeRange),
    staleTime: 1000 * 60 * 5,
  });
}

// ============================================================
// Version 版本管理 Hooks
// ============================================================

/** 章节版本列表 */
export function useChapterVersions(chapterId: string | undefined) {
  return useQuery<Array<{ id: string; version: number; created_at: string; summary: string }>>({
    queryKey: queryKeys.chapterVersions(chapterId || ''),
    queryFn: () => getChapterVersions(chapterId!),
    enabled: !!chapterId,
  });
}

/** 版本 Diff */
export function useVersionDiff(chapterId: string | undefined, versionId: string | undefined) {
  return useQuery<{ old_text: string; new_text: string }>({
    queryKey: queryKeys.versionDiff(chapterId || '', versionId || ''),
    queryFn: () => getVersionDiff(chapterId!, versionId!),
    enabled: !!chapterId && !!versionId,
  });
}

/** 恢复版本 */
export function useRestoreVersion(chapterId: string) {
  return useMutation<unknown, Error, string>({
    mutationFn: (versionId: string) => restoreVersion(chapterId, versionId),
  });
}

/** 创建快照 */
export function useCreateSnapshot(chapterId: string) {
  return useMutation<{ id: string; version: number }, Error, void>({
    mutationFn: () => createSnapshot(chapterId),
  });
}

// ============================================================
// Search 搜索 Hooks
// ============================================================

/** 全局搜索 (Mutation 版，用于搜索栏触发) */
export function useGlobalSearch() {
  return useMutation<
    { results: unknown[]; total: number },
    Error,
    { query: string; type?: string; projectId?: string }
  >({
    mutationFn: (data) => globalSearch(data.query, data.type, data.projectId),
  });
}

// ============================================================
// Export 导出 Hooks
// ============================================================

/** 导出小说 */
export function useExportNovel(projectId: string) {
  return useMutation<
    { url: string },
    Error,
    { format: 'txt' | 'epub' | 'docx' | 'pdf'; options?: { chapters?: string[]; include_outline?: boolean } }
  >({
    mutationFn: (data) => exportNovel(projectId, data.format, data.options),
  });
}

// ============================================================
// A/B Test Hooks
// ============================================================

/** 创建 A/B 测试 */
export function useCreateABTest() {
  return useMutation<
    { id: string },
    Error,
    { project_id: string; name: string; variants: Array<{ name: string; content: string }> }
  >({
    mutationFn: createABTest,
  });
}

// ============================================================
// Platform Accounts Hooks
// ============================================================

/** 添加平台账号 */
export function useAddPlatformAccount() {
  return useMutation<
    { id: string },
    Error,
    { platform: string; auth_method: 'oauth' | 'cookie'; account_name: string; credentials?: Record<string, string>; expires_at?: string }
  >({
    mutationFn: addPlatformAccount,
  });
}

// ============================================================
// Publish 发布 Hooks
// ============================================================

/** 执行发布 */
export function useExecutePublish(projectId: string) {
  return useMutation<
    { execution_id: string; status: string },
    Error,
    { platform: string; chapter_ids: string[]; scheduled_at?: string }
  >({
    mutationFn: (data) => executePublish(projectId, data),
  });
}

// ============================================================
// Quality Benchmarks 质量基准 Hooks
// ============================================================

/** 获取质量基准 */
export function useGetBenchmarks(platform?: string, genre?: string) {
  return useQuery<Array<{ id: string; platform: string; metric: string; value: number }>>({
    queryKey: queryKeys.qualityBenchmarksFiltered(platform, genre),
    queryFn: () => getBenchmarks(platform, genre),
    staleTime: 1000 * 60 * 10,
  });
}

/** 覆盖基准值 */
export function useOverrideBenchmark() {
  return useMutation<
    { id: string },
    Error,
    { platform: string; metric: string; value: number }
  >({
    mutationFn: overrideBenchmark,
  });
}
