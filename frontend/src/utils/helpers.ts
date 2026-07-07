/**
 * 通用辅助函数
 * 格式化、状态映射、字符串工具等
 */
import type { ProjectState } from '@/types';

/** 格式化字数：>10000 显示为 "1.2万" */
export function fmtWords(n: number): string {
  if (n >= 10000) {
    return `${(n / 10000).toFixed(1)}万`;
  }
  return n.toLocaleString();
}

/** 状态中文标签映射 */
export const STATE_LABELS: Record<ProjectState, string> = {
  idea: '构思',
  outline: '大纲',
  world: '设定',
  writing: '创作中',
  review: '审核',
  publish: '发布',
};

/** 状态颜色映射（Tailwind 色值） */
export const STATE_COLORS: Record<ProjectState, string> = {
  idea: '#9CA3AF',
  outline: '#3B82F6',
  world: '#8B5CF6',
  writing: '#FF6B35',
  review: '#F59E0B',
  publish: '#10B981',
};

/** 格式化日期 */
export function formatDate(
  dateStr: string,
  locale: string = 'zh-CN',
): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString(locale, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

/** 截断文本 */
export function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 3) + '...';
}

/** 合并 class 名（简易版 clsx） */
export function classNames(
  ...args: (string | undefined | null | false)[]
): string {
  return args.filter(Boolean).join(' ');
}
