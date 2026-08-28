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

每条 bullet 优先包含一个业务不变量和一个源码可解释点，例如：确认门、4 步工具上限、半开区间冲突、事务内二次检查、会话隔离、FAISS 来源或知识/实时数据边界。

## Claim 规则

- 可以写：强制 DeepSeek 结构化路由与字段提取、LangChain 有界工具调用、FAISS + 本地 Embedding RAG、grounded 来源、服务端确认门、教师硬约束与软排序、学生/教师冲突、SQLAlchemy Repository、`session_id + TTL`、FastAPI JSON API、Fake provider 离线测试。
- 需要限定：模型负责理解与工具选择，排课规则和写入仍由确定性服务控制；自动化测试未调用真实 DeepSeek。
- 只能写为规划：MCP、流式输出、Redis、复杂长期记忆、反思自学习、PostgreSQL 排他约束、生产客户与业务提升。真实 DeepSeek 成功率、延迟和成本必须现场实测后再写。
- 不得引用不存在路径或历史模块。任何量化数字都必须能由测试、命令输出或用户提供的数据解释。

初稿后可附 3 个高概率追问，重点检查 Agent 边界、排课一致性和实现/规划区分。
