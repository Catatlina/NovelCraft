import React from 'react';
import { ChevronDown, ChevronRight, FileText } from 'lucide-react';
import type { ChapterSummary } from '@/types';

interface ChapterTreeProps {
  chapters: ChapterSummary[];
  activeChapter?: string;
  onSelect: (chapterId: string) => void;
}

interface VolumeGroup {
  name: string;
  chapters: ChapterSummary[];
}

/**
 * 章节目录树组件
 * 按卷分组、可折叠，高亮当前章节，展示章节号、标题、字数
 */
const ChapterTree: React.FC<ChapterTreeProps> = ({
  chapters,
  activeChapter,
  onSelect,
}) => {
  const [collapsedVolumes, setCollapsedVolumes] = React.useState<Set<string>>(
    new Set(),
  );

  // 按卷分组（无 volume 标记的自动归为"正文"）
  const volumes: VolumeGroup[] = React.useMemo(() => {
    const map = new Map<string, ChapterSummary[]>();
    for (const ch of chapters) {
      const vol: string = ch.volume || '正文';
      if (!map.has(vol)) map.set(vol, []);
      map.get(vol)!.push(ch);
    }
    return Array.from(map.entries()).map(([name, chs]) => ({ name, chapters: chs }));
  }, [chapters]);

  const toggleVolume = (name: string): void => {
    setCollapsedVolumes((prev: Set<string>) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  if (chapters.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-gray-400 dark:text-gray-500">
        暂无章节
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      {volumes.map((vol: VolumeGroup) => {
        const isCollapsed: boolean = collapsedVolumes.has(vol.name);
        return (
          <div key={vol.name}>
            {/* 卷标题 */}
            <button
              onClick={() => toggleVolume(vol.name)}
              className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left transition-colors hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <span className="text-[13px] font-semibold text-gray-700 dark:text-gray-200">
                {vol.name}
              </span>
              <span className="flex items-center gap-1">
                <span className="text-[11px] font-mono text-gray-400 dark:text-gray-500">
                  {vol.chapters.length}章
                </span>
                {isCollapsed ? (
                  <ChevronRight size={14} className="text-gray-400" />
                ) : (
                  <ChevronDown size={14} className="text-gray-400" />
                )}
              </span>
            </button>

            {/* 章节列表 */}
            {!isCollapsed && (
              <div className="ml-3 flex flex-col gap-0.5">
                {vol.chapters.map((ch: ChapterSummary) => {
                  const isActive: boolean = ch.id === activeChapter;
                  return (
                    <button
                      key={ch.id}
                      onClick={() => onSelect(ch.id)}
                      className={`flex items-center gap-2 rounded-sm px-2 py-1 text-left text-[13px] transition-colors ${
                        isActive
                          ? 'bg-primary-50 font-semibold text-primary-500 dark:bg-primary-900/30 dark:text-primary-400'
                          : 'text-gray-600 hover:bg-gray-50 dark:text-gray-400 dark:hover:bg-gray-800'
                      }`}
                    >
                      <span className="w-7 shrink-0 font-mono text-[11px] text-gray-400 dark:text-gray-500">
                        {ch.chapter_num}.
                      </span>
                      <FileText size={12} className="shrink-0" />
                      <span className="flex-1 truncate">{ch.title || `第${ch.chapter_num}章`}</span>
                      <span className="font-mono text-[11px] text-gray-400 dark:text-gray-500">
                        {ch.word_count?.toLocaleString() || 0}字
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default ChapterTree;
