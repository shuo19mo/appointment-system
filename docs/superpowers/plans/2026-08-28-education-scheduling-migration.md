# Cross-Campus Education Scheduling Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将旧到店预约项目完整迁移为可运行、可测试的多校区一对一补习排课与课程咨询系统。

**Architecture:** 保留 FastAPI、SQLAlchemy、Jinja2 与可选 LangChain 能力，重建教育领域模型。核心排课以数据库硬约束和确定性排序为准；LLM/RAG 是可选增强层，所有核心测试均离线运行。

**Tech Stack:** Python 3.11+、FastAPI、Pydantic v2、SQLAlchemy 2、SQLite、Jinja2、可选 LangChain/OpenAI、pytest。

**Spec:** `DEV_SPEC.md`

## Global Constraints

- 所有开发在 `codex/education-scheduling-migration` 隔离 worktree 中完成。
- 先写失败测试，再写最小实现并验证转绿。
- 业务时间统一为带时区 `datetime`。
- 核心排课不得依赖外部模型、网络或向量服务。
- 不保留会误导维护者的旧领域入口、模板与测试。

---

### Task 1: 建立测试基础与领域验收用例

**Files:** `pytest.ini`、`requirements-dev.txt`、`tests/conftest.py`、`tests/test_parser.py`、`tests/test_scheduling_service.py`、`tests/test_sessions.py`、`tests/test_api.py`

- [x] 固定 pytest 导入路径和测试数据库 fixture。
- [x] 为字段解析、缺失字段提示、教师匹配与稳定排序编写失败测试。
- [x] 为教师/学生冲突和相邻课程编写失败测试。
- [x] 为会话隔离、API 健康检查与排课接口编写失败测试。
- [x] 运行测试并确认失败源自缺少新实现。

### Task 2: 重建教育领域数据层

**Files:** `db/models.py`、`db/repositories/education_repository.py`、`db/db_router.py`、`config/database.py`

- [x] 定义校区、教师、课程、关联、档期、学生、排课、知识与行为模型。
- [x] 实现教育领域 repository 的 CRUD、候选筛选与冲突查询。
- [x] 提供事务边界与 SQLite 测试兼容性。
- [x] 运行数据层和冲突测试。

### Task 3: 实现排课服务与结构化解析

**Files:** `agents/scheduling/models.py`、`agents/scheduling/input_parser.py`、`services/scheduling_service.py`

- [x] 实现中文关键词、常见相对时间与带偏移 ISO 时间的本地解析器。
- [x] 实现缺失字段检测和针对性追问。
- [x] 实现教师硬约束筛选与软排序。
- [x] 实现事务内二次冲突检查、创建与取消排课。
- [x] 运行解析与排课服务测试。

### Task 4: 实现路由、咨询与会话隔离

**Files:** `agents/scheduling_agent.py`、`agents/consultant_agent.py`、`agents/task_classification_agent.py`、`agents/session_store.py`、`services/knowledge_service.py`

- [x] 实现确定性任务分类并预留可选 LLM 增强边界。
- [x] 实现按 `session_id` 隔离的对话状态和 TTL 清理。
- [x] 实现关键词知识检索，并保留可选 Embedding 数据字段。
- [x] 确保响应仅包含状态与业务结论，不包含内部思维链。
- [x] 运行 Agent 与会话测试。

### Task 5: 迁移 FastAPI 与前端

**Files:** `app.py`、`api/*.py`、`web/routes.py`、`web/templates/*.html`、`web/static/styles.css`

- [x] 提供校区、课程、教师、学生、档期、排课、聊天、知识与健康检查 API。
- [x] 将首页改为教育排课助手，并增加教务资料、教师规则与排课管理界面。
- [x] 删除旧到店预约 API 和模板入口。
- [x] 运行 API 测试并启动应用执行健康检查。

### Task 6: 更新文档、配置与项目 Skills

**Files:** `README.md`、`.env.example`、`requirements.txt`、`.agents/skills/*/SKILL.md`

- [x] 重写架构、启动方式、API 示例与无模型降级说明。
- [x] 清理失效路径和不存在的服务说明。
- [x] 将项目内全部 Skills 改为多校区教育排课语境。
- [x] 全仓搜索旧领域术语并处理残留。

### Task 7: 完整验证、提交与推送

- [ ] 运行 `PYTHONPATH=. .venv/bin/pytest -q`。
- [ ] 运行 `PYTHONPATH=. .venv/bin/python -m compileall agents api config db services web app.py`。
- [ ] 使用 TestClient 验证 `/health` 和核心排课流程。
- [ ] 检查 `git diff --check`、工作树与旧领域词扫描。
- [ ] 按逻辑拆分提交，最终推送 `codex/education-scheduling-migration`。
