/**
 * SearchBar — 全局搜索组件
 * Phase 9.3: 全局搜索
 *
 * 置于 AppLayout 顶部栏，支持全局搜索章节、伏笔、项目
 * 调用 GET /api/v1/search?q=xxx 获取结果
 * 下拉面板显示匹配结果，使用 react-highlight-words 高亮关键词
 */
import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, FileText, Network, FolderKanban, X, Loader2 } from 'lucide-react';
import Highlighter from 'react-highlight-words';
import { api } from '@/api/client';

// ============================================================
// Types
// ============================================================

interface SearchResult {
  id: string;
  type: 'chapter' | 'foreshadow' | 'project' | 'character';
  title: string;
  subtitle?: string;
  snippet?: string;
  project_id?: string;
  link?: string;
}

interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
}

// ============================================================
// Constants
// ============================================================

const TYPE_ICONS: Record<string, React.ReactNode> = {
  chapter: <FileText size={14} className="text-blue-500" />,
  foreshadow: <Network size={14} className="text-amber-500" />,
  project: <FolderKanban size={14} className="text-emerald-500" />,
  character: <FileText size={14} className="text-purple-500" />,
};

const TYPE_LABELS: Record<string, string> = {
  chapter: '章节',
  foreshadow: '伏笔',
  project: '项目',
  character: '角色',
};

const DEBOUNCE_MS: number = 300;

// ============================================================
// Component
// ============================================================

const SearchBar: React.FC = () => {
  const navigate = useNavigate();

  // ---- 状态 ----
  const [query, setQuery] = useState<string>('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);

  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // ---- 搜索 ----
  const performSearch = useCallback(async (q: string): Promise<void> => {
    if (q.trim().length < 2) {
      setResults([]);
      setTotal(0);
      setIsOpen(false);
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    try {
      const data: SearchResponse = await api<SearchResponse>(
        `/search?q=${encodeURIComponent(q.trim())}`,
        'GET',
        undefined,
        { signal: controller.signal },
      );
      setResults(data.results || []);
      setTotal(data.total || 0);
      setIsOpen(true);
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, []);

  // ---- 防抖输入 ----
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>): void => {
      const value: string = e.target.value;
      setQuery(value);
      setSelectedIndex(-1);

      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }

      if (value.trim().length < 2) {
        setResults([]);
        setIsOpen(false);
        return;
      }

      debounceRef.current = setTimeout(() => {
        performSearch(value);
      }, DEBOUNCE_MS);
    },
    [performSearch],
  );

  // ---- 键盘导航 ----
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>): void => {
      if (!isOpen || results.length === 0) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev: number) =>
          prev < results.length - 1 ? prev + 1 : 0,
        );
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev: number) =>
          prev > 0 ? prev - 1 : results.length - 1,
        );
      } else if (e.key === 'Enter' && selectedIndex >= 0) {
        e.preventDefault();
        const item: SearchResult = results[selectedIndex];
        if (item.link) {
          navigate(item.link);
        }
        closeDropdown();
      } else if (e.key === 'Escape') {
        closeDropdown();
      }
    },
    [isOpen, results, selectedIndex, navigate],
  );

  // ---- 关闭下拉 ----
  const closeDropdown = useCallback((): void => {
    setIsOpen(false);
    setSelectedIndex(-1);
  }, []);

  // ---- 点击外部关闭 ----
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent): void => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        closeDropdown();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [closeDropdown]);

  // ---- 清理防抖 ----
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  // ---- 分组结果 ----
  const groupedResults = useMemo(() => {
    const groups: Record<string, SearchResult[]> = {};
    for (const r of results) {
      const key: string = r.type || 'other';
      if (!groups[key]) groups[key] = [];
      groups[key].push(r);
    }
    return groups;
  }, [results]);

  // ---- 聚焦快捷键 ----
  useEffect(() => {
    const handleShortcut = (e: KeyboardEvent): void => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener('keydown', handleShortcut);
    return () => document.removeEventListener('keydown', handleShortcut);
  }, []);

  // ---- 渲染 ----
  return (
    <div ref={containerRef} className="relative">
      {/* 搜索框 */}
      <div className="relative flex items-center">
        <Search
          size={15}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
        />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (results.length > 0) setIsOpen(true);
          }}
          placeholder="搜索章节、伏笔、项目… (⌘K)"
          className="w-48 rounded-lg border border-gray-200 bg-gray-50 py-2 pl-9 pr-8 text-[12px] text-gray-700 placeholder:text-gray-400 focus:w-64 focus:border-primary-400 focus:bg-white focus:outline-none focus:ring-1 focus:ring-primary-400 dark:border-gray-600 dark:bg-dark-surface dark:text-gray-200 dark:placeholder:text-gray-500 dark:focus:border-primary-500 dark:focus:bg-gray-800 transition-all duration-200"
          aria-label="全局搜索"
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          aria-autocomplete="list"
          role="combobox"
        />
        {query && (
          <button
            onClick={() => {
              setQuery('');
              setResults([]);
              setIsOpen(false);
              inputRef.current?.focus();
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            aria-label="清除搜索"
          >
            {loading ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <X size={14} />
            )}
          </button>
        )}
      </div>

      {/* 下拉结果面板 */}
      {isOpen && (
        <div
          className="absolute right-0 top-full mt-1.5 w-80 rounded-lg border border-gray-200 bg-white shadow-xl dark:border-gray-600 dark:bg-gray-800 z-50 max-h-[420px] overflow-y-auto"
          role="listbox"
        >
          {/* 结果头 */}
          {total > 0 && (
            <div className="sticky top-0 z-10 border-b border-gray-100 bg-gray-50 px-3 py-2 text-[11px] text-gray-400 dark:border-gray-700 dark:bg-gray-800/80 dark:text-gray-500">
              共 {total} 条结果
            </div>
          )}

          {/* 空结果 */}
          {query.trim().length >= 2 && results.length === 0 && !loading && (
            <div className="px-4 py-8 text-center text-[12px] text-gray-400 dark:text-gray-500">
              未找到与「{query}」相关的结果
            </div>
          )}

          {/* 加载中 */}
          {loading && results.length === 0 && (
            <div className="flex items-center justify-center gap-2 px-4 py-8 text-[12px] text-gray-400 dark:text-gray-500">
              <Loader2 size={14} className="animate-spin" />
              搜索中…
            </div>
          )}

          {/* 分组结果 */}
          {Object.entries(groupedResults).map(([groupType, items]) => (
            <div key={groupType}>
              <div className="px-3 py-1.5 text-[10px] font-semibold uppercase text-gray-400 dark:text-gray-500 bg-gray-50/50 dark:bg-gray-800/50">
                {TYPE_LABELS[groupType] || groupType}
              </div>
              {items.map((item: SearchResult) => {
                const globalIdx: number = results.indexOf(item);
                const isSelected: boolean = globalIdx === selectedIndex;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      if (item.link) navigate(item.link);
                      closeDropdown();
                    }}
                    onMouseEnter={() => setSelectedIndex(globalIdx)}
                    className={`w-full px-3 py-2.5 text-left transition-colors ${
                      isSelected
                        ? 'bg-primary-50 dark:bg-primary-900/20'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                    }`}
                    role="option"
                    aria-selected={isSelected}
                  >
                    <div className="flex items-center gap-2">
                      <span className="shrink-0">
                        {TYPE_ICONS[item.type] || TYPE_ICONS.chapter}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[12px] font-medium text-gray-700 dark:text-gray-200">
                          <Highlighter
                            highlightClassName="bg-amber-200 dark:bg-amber-700/40 text-inherit rounded-sm px-0.5"
                            searchWords={[query.trim()]}
                            autoEscape={true}
                            textToHighlight={item.title}
                          />
                        </p>
                        {item.snippet && (
                          <p className="mt-0.5 truncate text-[11px] text-gray-400 dark:text-gray-500">
                            <Highlighter
                              highlightClassName="bg-amber-200 dark:bg-amber-700/40 text-inherit rounded-sm px-0.5"
                              searchWords={[query.trim()]}
                              autoEscape={true}
                              textToHighlight={item.snippet}
                            />
                          </p>
                        )}
                      </div>
                      {item.subtitle && (
                        <span className="shrink-0 text-[10px] text-gray-400 dark:text-gray-500">
                          {item.subtitle}
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SearchBar;
