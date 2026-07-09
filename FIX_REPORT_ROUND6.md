# Round6 修复记录

已处理：
- 前端导出接口路径修正 /ops/export/{projectId}
- 平台账号请求模型补充 auth_method 字段
- 生产认证绕过开关强制关闭

待后续工程化：
- 完整 Alembic autogenerate 替换旧 migration runner
- 模型计费表接入真实价格
- 发布 adapter 深化
