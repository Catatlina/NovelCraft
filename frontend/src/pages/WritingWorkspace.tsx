import React, { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useProject, useChapters, useChapter, useGenerateChapter } from '@/hooks/useApi';
import { STATE_LABELS } from '@/utils/helpers';
import ChapterNav from '@/pages/WritingWorkspace/ChapterNav';
import Editor from '@/pages/WritingWorkspace/Editor';
import ContextPanel from '@/pages/WritingWorkspace/ContextPanel';
import QualityBall from '@/pages/WritingWorkspace/QualityBall';

/** 移动端 Tab 类型 */
type MobileTab = 'nav' | 'editor' | 'context';

/**
 * AI 创作工作台 — 主页面
 * 三栏布局：左侧章节导航 + 中央编辑器 + 右侧 Context Hub
 * 响应式：移动端使用 Tab 切换
 *
 * P0-1 fix: 章节列表(useChapters)现在只返回摘要，不含正文——正文改用
 * useChapter(activeChapterId) 按需单独拉取当前选中的这一章，Editor/
 * ContextPanel/QualityBall 三个子组件消费的是这个"当前章节详情"query，
 * 不再从列表数组里 find() 出来。
 */
const WritingWorkspace: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  // 数据加载 — API真实数据；失败显示错误状态
  const { data: project } = useProject(projectId);
  const { data: chapters, isLoading: chaptersListLoading } = useChapters(projectId);

  // 选中章节
  const [activeChapterId, setActiveChapterId] = useState<string | undefined>(undefined);
  const [mobileTab, setMobileTab] = useState<MobileTab>('editor');

  // 章节列表加载完成后，默认选中第一章（此前这个默认值是在渲染时从
  // chapters数组里inline算出来的；现在正文靠单独请求，必须显式把
  // activeChapterId设置成第一章的id，才能触发useChapter去拉正文）
  useEffect(() => {
    if (!activeChapterId && chapters && chapters.length > 0) {
      setActiveChapterId(chapters[0].id);
    }
  }, [chapters, activeChapterId]);

  const { data: activeChapter, isLoading: chapterLoading } = useChapter(activeChapterId);

  const handleSelectChapter = useCallback((chapterId: string) => {
    setActiveChapterId(chapterId);
    setMobileTab('editor');
  }, []);

  // 章节生成
  const genMutation = useGenerateChapter(projectId || '');

  const handleGenerateChapter = useCallback(() => {
    if (!projectId) return;
    genMutation.mutate(
      { mode: 'continue' },
      {
        onSuccess: () => {
          // React Query will auto-invalidate and refresh chapter list
        },
      }
    );
  }, [projectId, genMutation]);

  // 等待数据就绪
  if (!project) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <p className="text-gray-500 dark:text-gray-400">项目未找到或加载失败</p>
        <button className="btn-secondary" onClick={() => navigate('/')}>
          <ArrowLeft size={16} />
          返回驾驶舱
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* PC 端：三栏布局 */}
      <div className="hidden flex-1 overflow-hidden lg:flex">
        {/* 左侧章节导航 */}
        <aside className="flex h-full w-[240px] shrink-0 flex-col border-r border-gray-200 bg-white dark:border-gray-700 dark:bg-dark-surface">
          <ChapterNav
            project={project}
            chapters={chapters ?? []}
            chaptersLoading={chaptersListLoading}
            activeChapter={activeChapterId}
            onSelect={handleSelectChapter}
            onGenerate={handleGenerateChapter}
          />
        </aside>

        {/* 中央编辑器 */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <Editor
            project={project}
            chapter={activeChapter}
            chaptersLoading={chapterLoading}
            onBack={() => navigate('/')}
          />
        </div>

        {/* 右侧 Context Hub */}
        <aside className="flex h-full w-[320px] shrink-0 flex-col border-l border-gray-200 bg-white dark:border-gray-700 dark:bg-dark-surface">
          <ContextPanel project={project} chapter={activeChapter} />
        </aside>
      </div>

      {/* 移动端：Tab 切换布局 */}
      <div className="flex flex-1 flex-col overflow-hidden lg:hidden">
        {/* 移动端顶部 — 项目信息条 */}
        <div className="flex h-12 shrink-0 items-center gap-3 border-b border-gray-200 bg-white px-4 dark:border-gray-700 dark:bg-dark-surface">
          <button
            onClick={() => navigate('/')}
            className="rounded p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <ArrowLeft size={18} />
          </button>
          <span className="truncate text-[13px] font-semibold text-gray-700 dark:text-gray-200">
            {project.title}
          </span>
          <span className="text-[12px] text-gray-400">
            {STATE_LABELS[project.current_state]}
          </span>
        </div>

        {/* Tab 内容区 */}
        <div className="flex-1 overflow-hidden">
          {mobileTab === 'nav' && (
            <div className="h-full overflow-y-auto bg-white dark:bg-dark-surface">
              <ChapterNav
                project={project}
                chapters={chapters ?? []}
                chaptersLoading={chaptersListLoading}
                activeChapter={activeChapterId}
                onSelect={handleSelectChapter}
                onGenerate={handleGenerateChapter}
              />
            </div>
          )}
          {mobileTab === 'editor' && (
            <Editor
              project={project}
              chapter={activeChapter}
              chaptersLoading={chapterLoading}
              onBack={() => navigate('/')}
            />
          )}
          {mobileTab === 'context' && (
            <div className="h-full overflow-y-auto bg-white dark:bg-dark-surface">
              <ContextPanel project={project} chapter={activeChapter} />
            </div>
          )}
        </div>

        {/* 移动端底部 Tab 栏 */}
        <nav className="flex h-12 shrink-0 items-center justify-around border-t border-gray-200 bg-white dark:border-gray-700 dark:bg-dark-surface">
          {([
            { key: 'nav' as MobileTab, label: '目录' },
            { key: 'editor' as MobileTab, label: '编辑' },
            { key: 'context' as MobileTab, label: '上下文' },
          ]).map((tab) => (
            <button
              key={tab.key}
              onClick={() => setMobileTab(tab.key)}
              className={`flex-1 py-2 text-center text-[13px] font-medium transition-colors ${
                mobileTab === tab.key
                  ? 'text-primary-500'
                  : 'text-gray-400 dark:text-gray-500'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* 浮动质量评分球 */}
      <QualityBall chapter={activeChapter} />
    </div>
  );
};

export default WritingWorkspace;
