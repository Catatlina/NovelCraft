/**
 * DiffViewer — 版本 diff 对比组件
 * Phase 9.2: 版本对比
 *
 * 基于 react-diff-viewer-continued 库，提供分栏/行内两种模式
 * 用于对比章节的不同版本差异
 */
import React, { useState } from 'react';
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued';
import { Columns2, AlignJustify } from 'lucide-react';

// ============================================================
// Types
// ============================================================

export interface DiffViewerProps {
  /** 旧版本文本 */
  oldText: string;
  /** 新版本文本 */
  newText: string;
  /** 旧版本标签 */
  oldLabel?: string;
  /** 新版本标签 */
  newLabel?: string;
  /** 是否默认分栏视图 */
  defaultSplitView?: boolean;
}

// ============================================================
// Styles (react-diff-viewer-continued 暗色模式覆盖)
// ============================================================

const LIGHT_STYLES: Record<string, React.CSSProperties> = {
  diffContainer: {
    borderRadius: '8px',
    overflow: 'hidden',
  },
};

// ============================================================
// Component
// ============================================================

const DiffViewer: React.FC<DiffViewerProps> = ({
  oldText,
  newText,
  oldLabel = '旧版本',
  newLabel = '新版本',
  defaultSplitView = true,
}) => {
  const [splitView, setSplitView] = useState<boolean>(defaultSplitView);

  return (
    <div className="flex flex-col gap-2">
      {/* 工具栏 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-[12px] text-gray-500 dark:text-gray-400">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-red-200 dark:bg-red-800" />
            {oldLabel}
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-green-200 dark:bg-green-800" />
            {newLabel}
          </span>
        </div>

        {/* 视图切换 */}
        <div className="flex rounded-md border border-gray-200 dark:border-gray-600 overflow-hidden">
          <button
            onClick={() => setSplitView(true)}
            className={`flex items-center gap-1 px-2.5 py-1.5 text-[11px] font-medium transition-colors ${
              splitView
                ? 'bg-primary-500 text-white'
                : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-dark-surface dark:text-gray-400 dark:hover:bg-gray-700'
            }`}
            aria-label="分栏视图"
            aria-pressed={splitView}
          >
            <Columns2 size={14} />
            分栏
          </button>
          <button
            onClick={() => setSplitView(false)}
            className={`flex items-center gap-1 px-2.5 py-1.5 text-[11px] font-medium transition-colors ${
              !splitView
                ? 'bg-primary-500 text-white'
                : 'bg-white text-gray-500 hover:bg-gray-50 dark:bg-dark-surface dark:text-gray-400 dark:hover:bg-gray-700'
            }`}
            aria-label="行内视图"
            aria-pressed={!splitView}
          >
            <AlignJustify size={14} />
            行内
          </button>
        </div>
      </div>

      {/* Diff 内容 */}
      <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-600 text-[12px] leading-relaxed">
        <ReactDiffViewer
          oldValue={oldText}
          newValue={newText}
          splitView={splitView}
          leftTitle={oldLabel}
          rightTitle={newLabel}
          compareMethod={DiffMethod.WORDS}
          useDarkTheme={false}
          styles={LIGHT_STYLES}
          hideLineNumbers={false}
          showDiffOnly={false}
        />
      </div>
    </div>
  );
};

export default DiffViewer;
