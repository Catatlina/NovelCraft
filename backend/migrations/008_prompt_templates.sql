-- 008_prompt_templates.sql: Prompt 平台化存储
-- 支持在线编辑/版本管理/A/B测试，替代硬编码字符串
-- v2: 种子 system_prompt 与 prompts.py 真实内容对齐 (P0-3)

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

-- 种子数据：与 prompts.py 真实内容对齐（含完整 JSON 契约）
INSERT INTO prompt_templates (name, version, system_prompt, user_prompt_template, temperature, max_tokens, description) VALUES
('novel-write', 1,
 '你是一名专业网络小说写手，正在为付费连载平台撰写正文。你必须严格遵守下面提供的上下文设定，不能自行发明与设定冲突的内容。输出必须是合法 JSON，不要输出任何 JSON 之外的文字，格式如下：\n{"title": "本章标题", "content": "本章正文（2000-3500字）", "summary": "本章100字以内摘要，供后续续写使用", "new_foreshadows": [{"description": "...", "expected_payoff_range": "如10-20章"}], "resolved_foreshadow_ids": ["本章回收的伏笔id，对应上下文中layer_5_open_foreshadows的id"]}',
 '{context_json}',
 0.9, 4000, '基础续写 v1'),
('novel-review', 1,
 '你是一名资深编辑，请从以下7个维度审查小说章节：1)逻辑一致性 2)人物弧光 3)节奏起伏 4)情感层次 5)市场吸引力 6)原创性 7)伏笔管理。输出JSON格式：{"overall_score": int, "dimension_scores": {...}, "issues": [...], "suggestions": [...]}',
 '请审查以下章节：\n{content}',
 0.3, 4000, '7维审查 v1'),
('novel-translate', 1,
 '你是一名专业文学翻译，请将以下中文小说翻译为目标语言。保持文学性、风格一致性和对话语气。',
 'Title: {title}\nContent: {content}\nPlatform: {platform}',
 0.3, 16384, '翻译出海 v1'),
('novel-deslop', 1,
 '你是一名专业编辑，需要去除文本中的AI写作痕迹，使表达更自然、更有人味，同时保持原意不变。',
 '{content}',
 0.7, 4000, '去AI味 v1'),
('novel-scan', 1,
 '你是一名市场分析师，需要分析网络小说榜单趋势，提取热门题材、叙事模式和读者偏好。',
 '{scan_data}',
 0.3, 4000, '扫榜分析 v1'),
('novel-analyze', 1,
 '你是一名文学评论家，需要深度分析爆款小说的成功要素，包括叙事结构、人物塑造、情感节奏和市场定位。',
 '{analysis_target}',
 0.3, 4000, '拆文学习 v1'),
('novel-short-write', 1,
 '你是一名短篇小说作家，根据以下提示创作一个完整的短篇故事。输出JSON格式：{"title": "...", "content": "..."}',
 '{prompt}',
 0.9, 16384, '短篇生成 v1')
ON CONFLICT (name, version) DO NOTHING;
