# 当前项目亮点与源码锚点

## 1. 确定性 Agent 编排

- `agents/coordinator.py`：统一入口，路由排课、咨询和无关请求。
- `agents/task_classification_agent.py`：离线关键词分类。
- `agents/session_store.py`：按 `session_id` 隔离、TTL 清理。

可信表达：设计可替换的类级 Agent Coordinator，使核心流程无模型 key 可运行。不要写成 LangChain 自治编排或动态子进程。

## 2. 排课字段与教师匹配

- `agents/scheduling/input_parser.py`：学生、校区、学科、年级、ISO 时间、时长和教师偏好。
- `agents/scheduling_agent.py`：多轮合并、缺字段追问、实体解析。
- `services/scheduling_service.py`：硬约束筛选、指定教师/专长/最近历史偏好/负载评分和稳定排序。

可信表达：指定教师不可用时返回满足资格、校区和档期条件的替代教师，确认后将最近教师选择反馈到后续排序。不要写 Embedding 相似度，除非之后确有运行代码。

## 3. 冲突与事务一致性

- `db/repositories/education_repository.py`：半开区间冲突、双方冲突、事务内二次检查和 SQLite `BEGIN IMMEDIATE` 写入串行化。
- `db/models.py`：统一 UTC 持久化，避免 SQLite 丢弃时区偏移。
- `tests/test_scheduling_service.py`、`tests/test_review_regressions.py`：重叠拒绝、相邻课程、跨偏移冲突和并发占位验证。

可信表达：在单 SQLite 数据库文件内串行化“冲突检查 + 创建”，并用回归测试验证并发仅成功一条。多实例生产高并发仍需 PostgreSQL 时间范围排他约束。

## 4. 教育领域建模

- `db/models.py`：Campus、Teacher、Course、TeacherCourse、TeacherCampus、TeacherAvailability、Student、ClassBooking、KnowledgeDocument 等。
- `db/db_router.py`：引擎、Schema 和 Repository 装配。

可信表达：把教师资质、服务校区、可用时间和课程安排拆分建模，避免用自由文本承担实时约束。

## 5. 知识咨询边界

- `services/knowledge_service.py`：关键词检索接口。
- `agents/consultant_agent.py`：Top-K 文档与来源返回。
- `api/education.py`：知识写入与查询 API。

可信表达：构建 RAG-ready 教育知识层，并强制实时档期走数据库。当前不是 FAISS/LLM 生成链。

## 6. API 与可复现性

- `api/education.py`：基础资料 CRUD、教师资格/校区/档期、匹配、创建、查询、取消、知识和聊天 API。
- `.github/skills/setup-environment/`：无 key 核心安装、健康检查、可选 AI/测试依赖。
- `tests/`：解析、排课不变量、会话和 API 离线验收。

测试数量和通过状态必须现场验证，不硬编码。
