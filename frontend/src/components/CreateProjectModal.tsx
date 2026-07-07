import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, BookOpen } from 'lucide-react';
import { useCreateProject } from '@/hooks/useApi';
import { useProjectStore } from '@/store/projectStore';
import type { ProjectCreate } from '@/types';

interface CreateProjectModalProps {
  open: boolean;
  onClose: () => void;
}

/** 可选小说类型 */
const GENRE_OPTIONS: string[] = [
  '玄幻',
  '都市',
  '仙侠',
  '科幻',
  '历史',
  '悬疑',
  '言情',
  '网游',
  '末世',
  '无限流',
];

/** 可选目标平台 */
const PLATFORM_OPTIONS: string[] = [
  '起点',
  '番茄',
  '晋江',
  '纵横',
  '七猫',
  '飞卢',
  '掌阅',
  '其他',
];

/**
 * 新建项目 Modal 组件
 * 表单：书名（必填）、类型（下拉）、平台（下拉）
 * 使用 useCreateProject mutation，成功后跳转到新项目页面
 */
const CreateProjectModal: React.FC<CreateProjectModalProps> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const setSelectedProjectId = useProjectStore((s) => s.setSelectedProjectId);
  const createMutation = useCreateProject();

  const [title, setTitle] = useState<string>('');
  const [genre, setGenre] = useState<string>('玄幻');
  const [platform, setPlatform] = useState<string>('起点');
  const [error, setError] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);

  const inputRef = useRef<HTMLInputElement>(null);

  // 打开时聚焦书名输入框
  useEffect(() => {
    if (open) {
      setTitle('');
      setGenre('玄幻');
      setPlatform('起点');
      setError('');
      setSubmitting(false);
      // 延迟聚焦以等待动画完成
      const timer: ReturnType<typeof setTimeout> = setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [open]);

  // 关闭（ESC 键）
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent): void => {
      if (e.key === 'Escape' && !submitting) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onClose, submitting]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const trimmedTitle: string = title.trim();

      if (!trimmedTitle) {
        setError('请输入书名');
        return;
      }

      setError('');
      setSubmitting(true);

      const payload: ProjectCreate = {
        title: trimmedTitle,
        target_platform: platform,
      };

      try {
        const project = await createMutation.mutateAsync(payload);
        onClose();
        setSelectedProjectId(project.id);
        navigate(`/write/${project.id}`);
      } catch (err: unknown) {
        const message: string =
          err instanceof Error ? err.message : '创建失败，请稍后重试';
        setError(message);
        setSubmitting(false);
      }
    },
    [title, platform, createMutation, onClose, navigate],
  );

  const handleOverlayClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget && !submitting) {
        onClose();
      }
    },
    [onClose, submitting],
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm"
      onClick={handleOverlayClick}
      role="dialog"
      aria-modal="true"
      aria-label="新建项目"
    >
      <div className="relative w-full max-w-md rounded-2xl border border-gray-200 bg-white p-6 shadow-2xl dark:border-gray-700 dark:bg-dark-surface">
        {/* 关闭按钮 */}
        <button
          onClick={onClose}
          disabled={submitting}
          className="absolute right-4 top-4 rounded-md p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
          aria-label="关闭"
        >
          <X size={18} />
        </button>

        {/* 标题区域 */}
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-primary text-white">
            <BookOpen size={20} />
          </div>
          <div>
            <h2 className="text-[18px] font-bold text-gray-800 dark:text-gray-100">
              新建项目
            </h2>
            <p className="text-[13px] text-gray-400 dark:text-gray-500">
              开始一本新的小说创作
            </p>
          </div>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {/* 书名 */}
          <div>
            <label
              htmlFor="project-title"
              className="mb-1.5 block text-[13px] font-medium text-gray-600 dark:text-gray-300"
            >
              书名 <span className="text-red-500">*</span>
            </label>
            <input
              ref={inputRef}
              id="project-title"
              type="text"
              className="input"
              placeholder="输入小说书名..."
              value={title}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                setTitle(e.target.value);
                if (error) setError('');
              }}
              disabled={submitting}
              maxLength={100}
            />
          </div>

          {/* 类型 */}
          <div>
            <label
              htmlFor="project-genre"
              className="mb-1.5 block text-[13px] font-medium text-gray-600 dark:text-gray-300"
            >
              类型
            </label>
            <select
              id="project-genre"
              className="input cursor-pointer appearance-none"
              value={genre}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setGenre(e.target.value)}
              disabled={submitting}
            >
              {GENRE_OPTIONS.map((g: string) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </div>

          {/* 平台 */}
          <div>
            <label
              htmlFor="project-platform"
              className="mb-1.5 block text-[13px] font-medium text-gray-600 dark:text-gray-300"
            >
              目标平台
            </label>
            <select
              id="project-platform"
              className="input cursor-pointer appearance-none"
              value={platform}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setPlatform(e.target.value)}
              disabled={submitting}
            >
              {PLATFORM_OPTIONS.map((p: string) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-[13px] text-red-600 dark:bg-red-900/30 dark:text-red-400">
              {error}
            </div>
          )}

          {/* 按钮 */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              className="btn-ghost flex-1"
              onClick={onClose}
              disabled={submitting}
            >
              取消
            </button>
            <button
              type="submit"
              className="btn-primary flex-1"
              disabled={submitting || !title.trim()}
            >
              {submitting ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  创建中...
                </span>
              ) : (
                '创建项目'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateProjectModal;
