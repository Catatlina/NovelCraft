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
// Mock 数据（后端不可用时使用）
// ============================================================
const MOCK_PROJECTS: Project[] = [
  { id: 'demo-project-001', user_id: 'demo', title: '星辰之主', target_platform: '起点', target_words: 1000000, current_words: 85000, current_state: 'writing', state_history: [], outline: '少年林凡偶获星辰之力，从废柴逆袭为绝世强者。全书8卷。', world_setting: '修真世界，练气→筑基→金丹→元婴→化神→渡劫→飞升。', created_at: '2026-06-01T00:00:00Z', updated_at: '2026-07-06T00:00:00Z' },
  { id: 'demo-project-002', user_id: 'demo', title: '都市医仙', target_platform: '番茄', target_words: 800000, current_words: 1200, current_state: 'outline', state_history: [], outline: '医学天才获得医仙传承', world_setting: '现代都市', created_at: '2026-07-01T00:00:00Z', updated_at: '2026-07-05T00:00:00Z' },
  { id: 'demo-project-003', user_id: 'demo', title: '末日求生手册', target_platform: '晋江', target_words: 500000, current_words: 0, current_state: 'idea', state_history: [], outline: '病毒爆发后重建文明', world_setting: '近未来末日', created_at: '2026-07-04T00:00:00Z', updated_at: '2026-07-04T00:00:00Z' },
];
const MOCK_CHAPTERS: Chapter[] = [
  { id: 'ch1', project_id: 'demo-project-001', chapter_num: 1, title: '第一章 星辰觉醒', content: '夜色如墨，林凡盘坐在后山破旧的木屋中。\n\n三年来，他无数次尝试引气入体，却始终无法突破那道无形的壁垒。宗门上下，早已将他视为笑柄——一个十六岁还未踏入练气期的废物。\n\n"再试一次。"他咬紧牙关，按照《星辰诀》的运功路线，将体内稀薄的灵力缓缓引导...\n\n突然，天际划过一道流星。\n\n那道光不偏不倚，直直坠入他的眉心！\n\n轰——！\n\n林凡只觉得脑海炸开，无数画面如潮水般涌入。那是一颗古星从诞生到毁灭的全过程，是亿万年宇宙演化的缩影。\n\n当他再次睁眼时，眼眸深处竟有星光流转。\n\n练气一层，成！', word_count: 2800, summary: '林凡苦修三年无果，偶得星辰之力觉醒，终于踏入练气期。', review_score: 83, status: 'reviewed', created_at: '2026-06-02T00:00:00Z', updated_at: '2026-06-02T00:00:00Z' },
  { id: 'ch2', project_id: 'demo-project-001', chapter_num: 2, title: '第二章 宗门震动', content: '次日清晨，宗门长老议事厅。\n\n"你说什么？林凡突破练气期了？"大长老放下茶杯，眉头微皱。\n\n"不止如此。"传信弟子声音发颤，"他体内的灵力波动...至少是练气巅峰的水平。一夜之间连破九层！"\n\n满堂皆惊。\n\n...', word_count: 3100, summary: '林凡一夜连破九层震惊宗门。', review_score: null, status: 'draft', created_at: '2026-06-03T00:00:00Z', updated_at: '2026-06-03T00:00:00Z' },
  { id: 'ch3', project_id: 'demo-project-001', chapter_num: 3, title: '第三章 远古传承', content: '林凡被带入藏经阁深处。\n\n"这枚玉佩，是初代掌门留下的信物。"大长老指着供台上的古玉，"掌门临终前说，能引动星辰之力者，便是天选之人。"\n\n林凡伸手触碰玉佩。\n\n嗡——！\n\n一道光柱冲天而起，玉佩中浮现出一段古老的文字。那是上古时代失传的《星辰九变》完整功法！\n\n...', word_count: 2600, summary: '林凡触发了初代掌门留下的远古传承。', review_score: null, status: 'draft', created_at: '2026-06-04T00:00:00Z', updated_at: '2026-06-04T00:00:00Z' },
];
const MOCK_FORESHADOWS: Foreshadow[] = [
  { id: 'fs1', project_id: 'demo-project-001', content: '星辰之力隐藏着远古星神的意志', planted_chapter: 1, target_chapter: 8, resolved_chapter: null, status: 'planted', note: null, created_at: '', updated_at: '' },
  { id: 'fs2', project_id: 'demo-project-001', content: '大长老隐瞒了星辰之力的真相', planted_chapter: 2, target_chapter: 6, resolved_chapter: null, status: 'planted', note: null, created_at: '', updated_at: '' },
];
const MOCK_FS_STATS: ForeshadowStats = { total: 2, planted: 2, paid_off: 0, overdue: 0, resolution_rate: 0 };
const MOCK_PIPELINE = { status: 'idle' as const, project_id: '', tasks: [], total: 0, completed: 0, failed: 0 } as PipelineState;
const MOCK_OPS: Record<string, unknown> = { total_words: 85200, active_projects: 2, avg_quality: 78, foreshadow_recovery: 0 };

// ============================================================
// Query Hooks (Read)
// ============================================================

/** 项目列表 */
export function useProjects() {
  return useQuery<Project[]>({
    queryKey: queryKeys.projects,
    queryFn: async () => {
      try { return await projList(); }
      catch { return MOCK_PROJECTS; }
    },
    placeholderData: MOCK_PROJECTS,
    staleTime: 1000 * 60,
  });
}

/** 单个项目详情 — 后端不可用时自动回退 mock */
export function useProject(id: string | undefined) {
  return useQuery<Project>({
    queryKey: queryKeys.project(id || ''),
    queryFn: () => projGet(id!).catch(() => MOCK_PROJECTS[0]),
    initialData: MOCK_PROJECTS[0],
    enabled: !!id,
    staleTime: 1000 * 30,
  });
}

/** 项目章节列表 — 后端不可用时自动回退 mock */
export function useChapters(projectId: string | undefined) {
  return useQuery<Chapter[]>({
    queryKey: queryKeys.chapters(projectId || ''),
    queryFn: () => projListChapters(projectId!).catch(() => MOCK_CHAPTERS),
    initialData: MOCK_CHAPTERS,
    enabled: !!projectId,
    staleTime: 1000 * 30,
  });
}

/** 伏笔列表 — 后端不可用时自动回退 mock */
export function useForeshadows(projectId: string | undefined, status?: ForeshadowStatus) {
  return useQuery<Foreshadow[]>({
    queryKey: [...queryKeys.foreshadows(projectId || ''), status],
    queryFn: () => fsList(projectId!).catch(() => MOCK_FORESHADOWS),
    initialData: MOCK_FORESHADOWS,
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
    queryFn: () => fsStats(projectId!).catch(() => MOCK_FS_STATS),
    initialData: MOCK_FS_STATS,
    enabled: !!projectId,
  });
}

/** 流水线状态（轮询 5 秒） */
export function usePipelineStatus() {
  return useQuery<PipelineState>({
    queryKey: queryKeys.pipelineStatus,
    queryFn: () => pipelineStatus().catch(() => MOCK_PIPELINE),
    placeholderData: MOCK_PIPELINE,
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
    queryFn: () => opsDashboard().catch(() => MOCK_OPS),
    placeholderData: MOCK_OPS,
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
  return useMutation<{ result: string }, Error, RewriteRequest>({
    mutationFn: qualityRewrite,
  });
}

/** 爆款分析 */
export function useHitAnalyze(projectId: string) {
  return useMutation<HitAnalysisResult, Error, HitAnalysisRequest>({
    mutationFn: (data: HitAnalysisRequest) => hitAnalyze(projectId, data),
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
export function useScanRun(projectId: string) {
  return useMutation<unknown, Error, void>({
    mutationFn: () => scanRun(projectId),
  });
}

/** 去口语化 */
export function useDeslop(chapterId: string) {
  return useMutation<unknown, Error, void>({
    mutationFn: () => toolDeslop(chapterId),
  });
}

/** 全书分析 */
export function useAnalyzeBook(projectId: string) {
  return useMutation<unknown, Error, void>({
    mutationFn: () => toolAnalyzeBook(projectId),
  });
}

/** 伏笔回收检查 */
export function useCheckPayoff(foreshadowId: string) {
  return useMutation<PayoffCheckResult, Error, void>({
    mutationFn: () => fsCheckPayoff(foreshadowId),
  });
}

/** 伏笔逾期检查 */
export function useAutoCheckOverdue(projectId: string) {
  const qc = useQueryClient();
  return useMutation<Foreshadow[], Error, void>({
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
  return useQuery<string[]>({
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
    { translated_text: string },
    Error,
    { platform: string; glossary?: Record<string, string> }
  >({
    mutationFn: (data) => translateChapter(chapterId, data.platform, data.glossary),
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
    { platform: string; account_name: string; credentials?: Record<string, string> }
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
