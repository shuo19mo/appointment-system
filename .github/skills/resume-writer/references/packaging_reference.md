# 包装边界

## 已实现可直接写

- Coordinator + DeepSeek 结构化路由和字段提取。
- 最多 4 步的 LangChain 只读工具调用与服务端确认门。
- 进程内短期会话状态与 TTL。
- 教师课程资格、服务校区、档期、教师/学生冲突。
- 指定教师替代与可解释稳定评分。
- SQLite/SQLAlchemy/Repository 与事务复检。
- DeepSeek `search_knowledge` 工具、FAISS 语义检索和来源返回。
- FastAPI JSON API 与 Fake provider 离线测试。

## 有基础但必须限定

- 确认排课后会把最近选择写入 `Student.preferred_teacher_id` 并用于后续 +15 排序，可写“基础教师偏好反馈”；`StudentPreference`/`StudentBehavior` 尚未形成完整长期学习闭环。
- FAISS 与本地 Embedding 已实现；真实 DeepSeek 线上调用、延迟和成本仍需单独 smoke test。
- 可称为多 Agent 职责拆分，但要说明是中心化协调、受限工具循环和确定性写入，不是自主修改数据库的自治网络。

## 只能写未来设计

MCP Server、StreamingResponse、反思自学习、主动课程推荐、Redis 会话、PostgreSQL 并发约束、复杂权限、班课、支付和真实生产规模。真实 DeepSeek 延迟、Token 成本和稳定性也必须实测后再写。

如果用户要求增强版，将句式写成“设计扩展边界”“预留接口”“计划接入”，不能使用“落地、实现、提升了”等完成态。
