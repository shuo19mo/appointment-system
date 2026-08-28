# EduFlow AI：DeepSeek 多校区智能排课 Agent

EduFlow AI 面向类似新东方的多校区补习机构，用 DeepSeek LLM Agent 理解家长或教务的自然语言需求，再用确定性排课服务校验教师资质、服务校区、档期、教师冲突和学生冲突。

生产聊天强制使用 DeepSeek，模型不可用时不会切换到本地关键词或正则解析器。自动化测试注入 Fake LLM 和 Fake Embedding，因此不会访问模型网络或产生 API 费用。

## 核心能力

- DeepSeek 结构化路由：区分排课、课程咨询与能力范围外请求。
- DeepSeek 结构化提取：支持多轮补充学生、校区、学科、年级、时间、时长和教师偏好。
- 有界工具调用：模型最多执行 4 步只读查询，工具 trace 不记录联系方式、完整参数或思维过程。
- 安全确认门：聊天中的模型无法直接创建课程；先返回候选教师，用户确认后才通过 `SchedulingService` 写库。
- FAISS RAG：本地 `BAAI/bge-small-zh-v1.5` Embedding 检索课程、教师、校区和政策资料，咨询回答带来源。
- 多校区排课：硬约束筛选、稳定软排序、双边冲突检查、UTC 持久化和 SQLite 并发写入保护。
- 教务后台：维护校区、教师、课程、学生、教师资格、服务校区与档期。

V1 聚焦一对一课程，不包含支付、班课、教室容量、考勤和复杂权限。

## 架构

```text
Web / API
    ↓
EducationCoordinator
    ├── TaskClassificationAgent ── DeepSeek structured output
    ├── SchedulingAgent
    │   ├── LLMSchedulingInputParser ── DeepSeek structured output
    │   ├── EducationTools ── real database lookups / teacher matching
    │   └── confirmation gate ── SchedulingService ── Repository
    └── ConsultantAgent
        └── DeepSeek bounded tool loop ── search_knowledge ── FAISS
                                                        ↓
                                             SQLAlchemy / SQLite
```

LLM 负责语义理解和工具选择；时间冲突、资格、校区、负载、候选排序和最终写入仍由可测试的确定性服务负责。实时档期永远查询数据库，不进入向量知识库。

## 快速启动

要求 Python 3.11+ 和 DeepSeek API Key。首次启动会下载本地 Embedding 模型。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`：

```env
AGENT_MODE=llm
MODEL_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的密钥
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

然后启动：

```bash
uvicorn app:app --host 127.0.0.1 --port 8001 --reload
```

打开：

- 控制台：http://127.0.0.1:8001
- OpenAPI：http://127.0.0.1:8001/docs
- 存活检查：http://127.0.0.1:8001/health
- Agent 就绪检查：http://127.0.0.1:8001/ready

缺少 `DEEPSEEK_API_KEY`、`AGENT_MODE` 不是 `llm` 或 provider 不是 `deepseek` 时，应用会在启动阶段明确失败。真实 `.env` 不应提交到 Git。

也可使用项目 Skill 脚本：

```bash
bash .github/skills/setup-environment/scripts/setup.sh --test
```

## 排课安全规则

候选教师必须同时满足目标课程资格、服务目标校区、目标时间完整位于可用区间、教师无冲突、学生无冲突。重叠判定使用半开区间：

```text
new_start < existing_end AND new_end > existing_start
```

因此 14:00–15:30 与 15:30–17:00 可以相邻安排。硬约束通过后，再按指定教师、专长、学生历史偏好和当日负载排序。

聊天创建流程必须经过“匹配候选 → 用户确认 → 服务端重新校验 → 写库”。管理 API 的 `POST /api/schedules` 是教务直接操作入口，不是 LLM 工具。

## Chat 示例

```bash
curl -X POST http://127.0.0.1:8001/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "family-001",
    "message": "给小明在浦东校区约初二数学，2026-09-05 14:00，90分钟，最好王老师"
  }'
```

响应包含 `request_id`、`agent_mode`、`model` 和经过清洗的 `tool_trace`。模型不可用时 `/api/chat` 返回 503，不会切换到规则解析。

## 主要 API

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/health` | 进程存活 |
| GET | `/ready` | LLM 与向量服务就绪 |
| POST | `/api/chat` | DeepSeek Agent 统一入口 |
| GET/POST | `/api/knowledge` | 知识维护 |
| GET | `/api/knowledge/search` | FAISS 语义检索 |
| POST | `/api/schedules/match` | 确定性候选教师匹配 |
| POST | `/api/schedules` | 教务直接创建课程安排 |
| GET/DELETE | `/api/schedules[/{id}]` | 查询或取消课程安排 |
| GET/POST/PUT/DELETE | `/api/campuses`、`courses`、`teachers`、`students` | 基础资料管理 |

## 测试

```bash
python -m pip install -r requirements-dev.txt
pytest -q
python -m compileall -q agents api config db services web app.py
```

测试覆盖强制配置、LLM 路由与结构化提取、工具调用上限、确认门、FAISS 排序、grounded 咨询、排课不变量、会话隔离、API、时区和 SQLite 并发占位。测试通过依赖注入运行 Fake providers；真实 DeepSeek smoke test 需要开发者单独配置密钥后执行。

## 数据与迁移

教育排课模型与旧按摩/到店预约模型没有可靠的一一映射，本仓库使用独立 `education_scheduling.db` 和 clean-slate 初始化。开发环境可设置 `AUTO_INIT_DB=true`、`SEED_DEMO_DATA=true`；生产环境应关闭并使用受控迁移。详见 [docs/migrations/v2-clean-slate.md](docs/migrations/v2-clean-slate.md)。

空数据库首次启动时会生成一套固定、可复现的运营演示数据：5 个校区、15 位教师、10 个课程产品、18 位学生、12 条近期课程安排和 12 条知识资料。数据包含指定教师冲突、替代教师、跨校区资质、学生时间冲突、教师每日课时上限以及 `confirmed`、`pending`、`cancelled` 状态，可直接用于页面、排课 API、RAG 和 Agent 联调。已有数据库不会被 seed 自动覆盖。

## 目录

```text
agents/                 DeepSeek 路由、排课、咨询、工具与会话
api/                    FastAPI 教育业务端点
config/                 强制 Agent 配置、数据库和 provider
db/                     教育领域模型与 Repository
services/               排课规则与 FAISS 检索
tests/                  Fake provider 离线验收测试
web/                    学生聊天与教务后台
.github/skills/         环境、学习、面试和简历 Skills
```
