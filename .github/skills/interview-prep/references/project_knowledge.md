# 当前项目源码锚点

## 主链路

- `app.py`：创建 FastAPI、注入 Repository，并仅在环境变量显式开启时初始化 Schema/演示数据。
- `api/education.py`：校区、课程、教师、匹配、排课、知识和聊天 API。
- `agents/coordinator.py`：分类后路由到排课或咨询。
- `agents/task_classification_agent.py`：确定性关键词分类。
- `agents/scheduling_agent.py`：多轮字段收集、实体解析与候选返回。
- `agents/session_store.py`：按 `session_id` 隔离的 TTL 会话。

## 排课与数据

- `agents/scheduling/input_parser.py`：离线中文字段解析。
- `services/scheduling_service.py`：教师硬约束、软排序、创建课程。
- `db/models.py`：Campus、Teacher、Course、Student、ClassBooking 等模型。
- `db/repositories/education_repository.py`：CRUD、冲突查询、事务内二次检查，以及 SQLite `BEGIN IMMEDIATE` 并发写入串行化。
- `db/models.py`：带时区输入统一转 UTC 持久化，读取恢复 aware UTC。

需要讲清：`start < existing_end AND end > existing_start`，相邻课程允许；资格、校区、可用时间和双方冲突都是硬约束；指定教师和专长等只参与软排序。

## 知识与 Agent 边界

- `services/knowledge_service.py`：当前是离线关键词检索封装。
- `agents/consultant_agent.py`：只回答课程、教师、校区和政策文本。
- 实时档期必须走 Repository/SchedulingService，不能由知识文本回答。

## 可验证证据

- `tests/test_parser.py`：字段抽取和缺失追问。
- `tests/test_scheduling_service.py`：替代教师、双方冲突、相邻课程、稳定排序。
- `tests/test_sessions.py`：会话隔离。
- `tests/test_api.py`：健康检查、页面、排课和知识 API。

## 声称边界

当前已实现：教育模型、中文与 ISO 时间确定性解析、离线分类和知识检索、会话隔离、SQLite 单库并发冲突防护、聊天确认/取消、最近偏好教师反馈、管理 CRUD、API 与离线测试。

当前仅为扩展方向：LLM 结构化解析、FAISS 语义检索、Redis、PostgreSQL 并发锁、复杂权限、支付、班课、教室容量、真实机构生产数据。
