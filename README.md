# EduFlow AI：多校区智能排课系统

EduFlow AI 是一个面向补习机构的教师匹配、课程安排与课程咨询系统。它用 FastAPI、SQLAlchemy 和确定性排课规则处理实时档期与冲突，用可选的 LLM/RAG 能力增强自然语言理解和知识问答。

项目已完成教育领域重构：校区、教师、课程、学生、授课资格、服务校区、教师档期和课程安排均为独立数据模型。核心流程不依赖外部模型，克隆后即可运行和测试。

## 解决的问题

多校区机构的教务通常需要反复核对教师是否能教目标课程、是否服务目标校区、教师和学生是否撞课，以及指定教师无档期时谁能替代。EduFlow AI 将这些判断收敛到统一服务中：

- 按学科、年级、校区、时间和教师偏好匹配教师。
- 同时阻止教师与学生的重叠课程。
- 指定教师不可用时返回满足硬约束的替代人选。
- 使用稳定评分解释推荐原因。
- 将课程、教师、校区和机构政策放入独立知识库。
- 使用 `session_id` 隔离不同家庭的多轮需求。

V1 聚焦一对一课程，不包含支付、班课、教室容量、考勤和复杂权限。

## 架构

```text
Web / API
    ↓
EducationCoordinator
    ├── TaskClassificationAgent
    ├── SchedulingAgent ── SchedulingInputParser
    │                     └── SchedulingService
    └── ConsultantAgent ── KnowledgeService
                              ↓
                    EducationRepository
                              ↓
                     SQLAlchemy / SQLite
```

排课硬约束全部来自数据库。知识检索只处理相对稳定的课程和政策文本，不把实时档期写入向量库。详细产品和技术约束见 [DEV_SPEC.md](DEV_SPEC.md)。

## 核心规则

候选教师必须同时具备目标课程资格、服务目标校区、目标时间落在可用时间内，并且没有已有有效课程冲突。学生也不能在同一时段重复排课。

重叠判定使用半开区间：

```text
new_start < existing_end AND new_end > existing_start
```

因此 14:00–15:30 与 15:30–17:00 可以相邻安排。满足硬约束后，系统再按指定教师、专长、学生偏好和当日负载评分。

## 快速启动

要求 Python 3.11 或更高版本。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --host 127.0.0.1 --port 8001 --reload
```

打开：

- 控制台：[http://127.0.0.1:8001](http://127.0.0.1:8001)
- OpenAPI：[http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)
- 健康检查：[http://127.0.0.1:8001/health](http://127.0.0.1:8001/health)

`.env.example` 为本地开发显式开启 `AUTO_INIT_DB=true` 与 `SEED_DEMO_DATA=true`，因此复制为 `.env` 后首次启动会创建 Schema 和演示数据。生产环境应将两项设为 `false`，先执行受控迁移再启动；仅仅 `import app` 不会写数据库。

## 配置

核心配置：

```env
DATABASE_URL=sqlite:///data/education_scheduling.db
DB_ECHO=false
SESSION_TTL_SECONDS=1800
AUTO_INIT_DB=true
SEED_DEMO_DATA=true
```

本地规则解析、排课 API 和关键词知识检索不需要模型密钥。若要开发 LLM 或 Embedding 增强功能，再安装可选依赖并填写对应配置：

```bash
python -m pip install -r requirements-ai.txt
```

任何真实 `.env` 都不应提交到 Git。

## API 示例

查询教师候选：

```bash
curl -X POST http://127.0.0.1:8001/api/schedules/match \
  -H 'Content-Type: application/json' \
  -d '{
    "student_id": 1,
    "course_id": 1,
    "campus_id": 1,
    "start_at": "2026-09-05T14:00:00+08:00",
    "duration_minutes": 90,
    "preferred_teacher_id": 1
  }'
```

确认创建课程安排：

```bash
curl -X POST http://127.0.0.1:8001/api/schedules \
  -H 'Content-Type: application/json' \
  -d '{
    "student_id": 1,
    "teacher_id": 1,
    "course_id": 1,
    "campus_id": 1,
    "start_at": "2026-09-05T14:00:00+08:00",
    "duration_minutes": 90
  }'
```

自然语言入口：

```bash
curl -X POST http://127.0.0.1:8001/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "family-001",
    "message": "给小明在浦东校区约初二数学，2026-09-05 14:00，90分钟，最好王老师"
  }'
```

主要端点：

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/campuses` | 校区列表 |
| POST/PUT/DELETE | `/api/campuses[/{id}]` | 新增、更新、停用校区 |
| GET | `/api/courses` | 课程列表 |
| POST/PUT/DELETE | `/api/courses[/{id}]` | 新增、更新、停用课程 |
| GET | `/api/teachers` | 教师列表 |
| POST/PUT/DELETE | `/api/teachers[/{id}]` | 新增、更新、停用教师 |
| GET/POST/PUT/DELETE | `/api/students[/{id}]` | 学生资料管理 |
| POST/DELETE | `/api/teachers/{id}/courses/{course_id}` | 教师授课资格 |
| POST/DELETE | `/api/teachers/{id}/campuses/{campus_id}` | 教师服务校区 |
| GET | `/api/teachers/{id}/availability` | 教师可用时间 |
| POST/DELETE | `/api/teachers/{id}/availability[/{availability_id}]` | 教师档期维护 |
| POST | `/api/schedules/match` | 匹配候选教师 |
| POST | `/api/schedules` | 创建课程安排 |
| GET | `/api/schedules` | 查询课程安排 |
| DELETE | `/api/schedules/{id}` | 取消课程安排 |
| GET/POST | `/api/knowledge` | 列出/新增课程与政策知识 |
| GET | `/api/knowledge/search` | 关键词检索知识 |
| POST | `/api/chat` | 统一 Agent 入口 |

## 测试

```bash
python -m pip install -r requirements-dev.txt
pytest -q
python -m compileall agents api config db services web app.py
```

测试覆盖结构化解析、缺失字段追问、教师替代、稳定排序、教师/学生冲突、相邻课程、跨时区往返、SQLite 并发占位、会话隔离、管理 CRUD、知识检索和 API 主流程。测试不会访问真实模型或网络。

## 数据与迁移说明

V2 教育模型与旧到店预约模型不是同一业务语义，本仓库采用明确的 clean-slate 迁移：使用新的 `education_scheduling.db`，不自动猜测或搬运旧客户/预约数据。SQLite 每次连接启用外键约束，时间统一保存为 UTC；创建课程安排时用 `BEGIN IMMEDIATE` 串行化“检查冲突 + 写入”。生产多实例部署仍建议迁移到 PostgreSQL 排他约束。详见 [docs/migrations/v2-clean-slate.md](docs/migrations/v2-clean-slate.md)。

## 目录

```text
agents/                 任务分类、排课、咨询和会话状态
api/                    FastAPI 教育业务端点
config/                 数据库、时区和可选模型配置
db/                     教育领域模型与 Repository
services/               排课规则和知识检索服务
tests/                  离线验收测试
web/                    教务控制台
.github/skills/         环境搭建、学习、面试和简历 Skills
DEV_SPEC.md             产品范围、领域规则与验收标准
```

## 后续演进

- 使用 PostgreSQL 时间范围排他约束支持多实例高并发写入；当前 SQLite 已在单数据库文件内串行化排课创建。
- 将进程内会话替换为 Redis，并增加会话恢复与过期监控。
- 增加教室容量、班课、考勤和教务权限。
- 为教师专长加入 Embedding 语义加分，并建设离线评估集。
- 对接机构现有教务系统、消息通知和日历。
