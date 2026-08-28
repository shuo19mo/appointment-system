---
name: resume-writer
description: "Use when writing or revising Chinese or English resume project content for this multi-campus education scheduling system, especially Agent Engineer, LLM application, backend, RAG, or AI product engineering roles."
---

# Education Scheduling Resume Writer

将当前仓库整理为可信、可追问的简历项目经历。默认中文；用户指定时输出英文、ATS 或短版。

## 准备

写作前读取：

1. `DEV_SPEC.md` 与 `README.md`。
2. `references/project_highlights.md`：当前实现与源码锚点。
3. `references/resume_principles.md`：输出结构。
4. 用户要求“包装、记忆、RAG、MCP、反思、生产化”时再读 `references/packaging_reference.md`。

若 Claim 依赖测试数量或结果，现场统计并运行测试；不能沿用 reference 中的历史数字。

## 输入处理

用户已给出岗位、语言、条数或侧重时直接写，不重复确认。信息缺失时采用：Agent Engineer、中文、4 条 bullet、保守可信版，并标注可调整项。只有真实业务规模、个人职责或时间段会实质改变结果时才追问。

## 输出

默认结构：

```markdown
**多校区智能排课与课程咨询 Agent** | 时间 | 角色

**背景**：业务对象与教务痛点。
**目标**：核心自动化目标与边界。
**过程**：4–6 条“动作 + 技术实现 + 可验证效果” bullet。
**结果**：只写有测试、压测或用户数据支撑的指标；建议指标必须标“待实测”。
**技术栈**：按目标岗位排序。
```

每条 bullet 优先包含一个业务不变量和一个源码可解释点，例如：半开区间冲突、事务内二次检查、无模型降级、会话隔离、稳定教师排序或知识/实时数据边界。

## Claim 规则

- 可以写：确定性 Multi-Agent 路由、结构化字段收集、教师硬约束与软排序、指定教师替代、学生/教师冲突、SQLAlchemy Repository、`session_id + TTL`、关键词知识检索、FastAPI JSON API、离线测试。
- 需要限定：这是类级协调和规则引擎，不是自治 Agent 网络；知识检索是 RAG-ready 基础，不是完整 LLM RAG。
- 只能写为规划：FAISS/Embedding、LLM 解析、MCP、流式输出、Redis、复杂长期记忆、反思自学习、生产客户与业务提升。
- 不得引用不存在路径或历史模块。任何量化数字都必须能由测试、命令输出或用户提供的数据解释。

初稿后可附 3 个高概率追问，重点检查 Agent 边界、排课一致性和实现/规划区分。
