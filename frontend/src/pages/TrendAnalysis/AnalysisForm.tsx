import React, { useState, useCallback } from 'react';
import { Search, Loader2 } from 'lucide-react';
import type { HitAnalysisRequest } from '@/types';

interface AnalysisFormProps {
  onAnalyze: (data: HitAnalysisRequest) => void;
  isAnalyzing: boolean;
}

const GENRES: string[] = [
  '玄幻', '都市', '言情', '仙侠', '科幻', '悬疑', '历史', '游戏', '轻小说', '其他',
];

const PLATFORMS: string[] = ['起点中文网', '番茄小说', '七猫', '晋江', 'QQ阅读', '其他'];

/**
 * 爆款分析表单组件
 * 书名 + 类型 + 平台 + 第一章内容粘贴
 */
const AnalysisForm: React.FC<AnalysisFormProps> = ({ onAnalyze, isAnalyzing }) => {
  const [title, setTitle] = useState<string>('');
  const [genre, setGenre] = useState<string>('玄幻');
  const [platform, setPlatform] = useState<string>('起点中文网');
  const [sampleText, setSampleText] = useState<string>('');
  const [analyzed, setAnalyzed] = useState<boolean>(false);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!title.trim()) return;

      onAnalyze({
        title: title.trim(),
        tags: [genre],
        target_platform: platform,
        sample_text: sampleText.trim() || undefined,
      });
      setAnalyzed(true);
    },
    [title, genre, platform, sampleText, onAnalyze],
  );

  return (
    <div className="card">
      <h3 className="mb-4 text-[15px] font-semibold text-gray-800 dark:text-gray-100">
        分析我的作品
      </h3>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {/* 书名 + 类型 + 平台 */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className="mb-1 block text-[12px] font-medium text-gray-500 dark:text-gray-400">
              书名
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="输入书名…"
              className="input"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-[12px] font-medium text-gray-500 dark:text-gray-400">
              类型
            </label>
            <select
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
              className="input"
            >
              {GENRES.map((g: string) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[12px] font-medium text-gray-500 dark:text-gray-400">
              目标平台
            </label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="input"
            >
              {PLATFORMS.map((p: string) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 第一章内容 */}
        <div>
          <label className="mb-1 block text-[12px] font-medium text-gray-500 dark:text-gray-400">
            第一章内容（可选）
          </label>
          <textarea
            value={sampleText}
            onChange={(e) => setSampleText(e.target.value)}
            placeholder="粘贴第一章内容，获取更精准的市场分析…"
            rows={5}
            className="input h-auto resize-y font-serif text-[13px] leading-relaxed"
          />
        </div>

        {/* 提交按钮 */}
        <button
          type="submit"
          disabled={isAnalyzing || !title.trim()}
          className="btn-primary self-start"
        >
          {isAnalyzing ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              分析中…
            </>
          ) : (
            <>
              <Search size={16} />
              开始分析
            </>
          )}
        </button>

        {analyzed && !isAnalyzing && (
          <p className="text-[12px] text-emerald-500 dark:text-emerald-400">
            ✓ 分析完成，结果见下方
          </p>
        )}
      </form>
    </div>
  );
};

export default AnalysisForm;
