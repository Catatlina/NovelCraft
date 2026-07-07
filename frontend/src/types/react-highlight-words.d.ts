declare module 'react-highlight-words' {
  import type { ComponentType } from 'react';

  interface HighlighterProps {
    /** 要高亮搜索的词数组 */
    searchWords: string[];
    /** 要高亮显示的文本 */
    textToHighlight: string;
    /** 是否自动转义正则特殊字符 */
    autoEscape?: boolean;
    /** 高亮匹配词的 CSS 类名 */
    highlightClassName?: string;
    /** 高亮匹配词的内联样式 */
    highlightStyle?: React.CSSProperties;
    /** 大小写敏感 */
    caseSensitive?: boolean;
    /** 未匹配文本的 CSS 类名 */
    unhighlightClassName?: string;
    /** 未匹配文本的内联样式 */
    unhighlightStyle?: React.CSSProperties;
    /** 自定义高亮标签，默认 <mark> */
    highlightTag?: string | ComponentType<{ children: React.ReactNode }>;
    /** 用于查找匹配词的正则搜索函数 */
    findChunks?: (args: {
      autoEscape?: boolean;
      caseSensitive?: boolean;
      sanitize?: (text: string) => string;
      searchWords: string[];
      textToHighlight: string;
    }) => Array<{ start: number; end: number }>;
    /** 自定义净化函数 */
    sanitize?: (text: string) => string;
  }

  const Highlighter: ComponentType<HighlighterProps>;
  export default Highlighter;
}
