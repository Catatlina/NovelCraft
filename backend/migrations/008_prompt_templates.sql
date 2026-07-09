-- 008_prompt_templates.sql: Prompt 平台化存储
-- 支持在线编辑/版本管理/A/B测试，替代硬编码字符串

CREATE TABLE IF NOT EXISTS prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    version INT NOT NULL DEFAULT 1,
    system_prompt TEXT NOT NULL,
    user_prompt_template TEXT NOT NULL DEFAULT '',
    temperature FLOAT NOT NULL DEFAULT 0.9,
    max_tokens INT NOT NULL DEFAULT 4000,
    description TEXT DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(name, version)
);

CREATE INDEX IF NOT EXISTS idx_prompt_templates_active
    ON prompt_templates(name, is_active);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_name_version
    ON prompt_templates(name, version DESC);

-- 种子数据：当前 7 个硬编码 Prompt 作为 v1
INSERT INTO prompt_templates (name, version, system_prompt, user_prompt_template, temperature, max_tokens, description) VALUES
('novel-write', 1,
 '你是一名专业网络小说写手，正在为付费连载平台撰写正文。你必须严格遵守下面提供的上下文设定。',
 '{context_json}',
 0.9, 4000, '基础续写 v1'),
('novel-review', 1,
 '你是一名资深编辑，需要从7个维度审查小说章节质量。',
 '请审查以下章节：\n{content}\n\n维度：逻辑一致性、人物弧光、节奏起伏、情感层次、市场吸引力、原创性、伏笔管理',
 0.3, 4000, '7维审查 v1'),
('novel-translate', 1,
 '你是一名专业文学翻译，需要将中文小说翻译为目标语言，保持文学性和风格。',
 'Title: {title}\nContent: {content}\nPlatform: {platform}',
 0.3, 16384, '翻译出海 v1'),
('novel-deslop', 1,
 '你是一名专业编辑，需要去除AI写作痕迹，使文本更自然。',
 '{content}',
 0.7, 4000, '去AI味 v1'),
('novel-scan', 1,
 '你是一名市场分析师，需要分析网络小说榜单趋势。',
 '{scan_data}',
 0.3, 4000, '扫榜分析 v1'),
('novel-analyze', 1,
 '你是一名文学评论家，需要深度分析爆款小说的成功要素。',
 '{analysis_target}',
 0.3, 4000, '拆文学习 v1'),
('novel-short-write', 1,
 '你是一名短篇小说作家，需要创作完整的短篇故事。',
 '{prompt}',
 0.9, 16384, '短篇生成 v1')
ON CONFLICT (name, version) DO NOTHING;
