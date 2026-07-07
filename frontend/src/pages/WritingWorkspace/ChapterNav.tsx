import React from 'react';
import { Plus } from 'lucide-react';
import ChapterTree from '@/components/shared/ChapterTree';
import LoadingSpinner from '@/components/shared/LoadingSpinner';
import { fmtWords, STATE_LABELS } from '@/utils/helpers';
import type { Project, Chapter } from '@/types';

interface ChapterNavProps {
  project: Project;
  chapters: Chapter[];
  chaptersLoading: boolean;
  activeChapter?: string;
  onSelect: (chapterId: string) => void;
  onGenerate: () => void;
}

/**
 * 左侧章节导航组件
 * 展示项目信息头部 + ChapterTree + 新章生成按钮
 */
const ChapterNav: React.FC<ChapterNavProps> = ({
  project,
  chapters,
  chaptersLoading,
  activeChapter,
  onSelect,
  onGenerate,
}) => {
  const totalWords: number = chapters.reduce(
    (sum: number, ch: Chapter) => sum + (ch.word_count || 0),
    0,
  );

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* 头部：项目信息 */}
      <div className="shrink-0 border-b border-gray-100 px-4 py-3 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-primary text-lg font-bold text-white">
            {project.title.charAt(0)}
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-[14px] font-semibold text-gray-800 dark:text-gray-100">
              {project.title}
            </h3>
            <p className="mt-0.5 flex items-center gap-2 text-[12px] text-gray-400 dark:text-gray-500">
              <span>{chapters.length} 章</span>
              <span>·</span>
              <span>{fmtWords(totalWords)}字</span>
              <span>·</span>
              <span>{STATE_LABELS[project.current_state]}</span>
            </p>
          </div>
        </div>
      </div>

      {/* 章节树 */}
      <div className="flex-1 overflow-y-auto px-3 py-2 scrollbar-thin">
        {chaptersLoading ? (
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner text="加载章节..." />
          </div>
        ) : (
          <ChapterTree
            chapters={chapters}
            activeChapter={activeChapter}
            onSelect={onSelect}
          />
        )}
      </div>

      {/* 底部：新章生成按钮 */}
      <div className="shrink-0 border-t border-gray-100 p-3 dark:border-gray-700">
        <button
          onClick={onGenerate}
          className="btn-primary flex w-full items-center justify-center gap-2 !h-9 text-[13px]"
        >
          <Plus size={16} />
          <span>新增章节</span>
        </button>
      </div>
    </div>
  );
};

export default ChapterNav;
