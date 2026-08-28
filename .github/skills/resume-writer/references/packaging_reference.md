# 包装边界

## 已实现可直接写

- Coordinator + 三类职责组件的确定性路由。
- 进程内短期会话状态与 TTL。
- 教师课程资格、服务校区、档期、教师/学生冲突。
- 指定教师替代与可解释稳定评分。
- SQLite/SQLAlchemy/Repository 与事务复检。
- 关键词教育知识检索和来源返回。
- FastAPI JSON API 与离线测试。

## 有基础但必须限定

- 确认排课后会把最近选择写入 `Student.preferred_teacher_id` 并用于后续 +15 排序，可写“基础教师偏好反馈”；`StudentPreference`/`StudentBehavior` 尚未形成完整长期学习闭环。
- `KnowledgeDocument.embedding` 与 `requirements-ai.txt` 提供扩展接口；当前只能写“预留语义检索能力”。
- 类名可以称为多 Agent 职责拆分，但要说明是中心化确定性协调，不是自治网络。

## 只能写未来设计

LLM 自然语言解析、FAISS、MCP Server、StreamingResponse、反思自学习、主动课程推荐、Redis 会话、PostgreSQL 并发约束、复杂权限、班课、支付和真实生产规模。

如果用户要求增强版，将句式写成“设计扩展边界”“预留接口”“计划接入”，不能使用“落地、实现、提升了”等完成态。
