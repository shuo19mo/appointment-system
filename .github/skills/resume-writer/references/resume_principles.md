# 简历写作原则

## 四段结构

- 背景：多校区机构需要协调教师资质、校区、档期和学生课程冲突。
- 目标：建立离线可用、可解释、可测试的排课与咨询系统。
- 过程：每条写清动作、技术方案和解决的具体问题。
- 结果：只使用真实测试、压测、日志或用户提供的指标。

## 岗位取向

| 岗位 | 优先内容 |
|---|---|
| Agent Engineer | Coordinator、任务分类、会话隔离、排课 Agent、能力边界 |
| Backend Engineer | SQLAlchemy、Repository、事务复检、API 状态码、数据模型 |
| LLM Application | DeepSeek 结构化输出、有界工具循环、确认安全、Fake provider 测试 |
| RAG Engineer | FAISS、本地 Embedding、grounded 来源、实时数据不入知识库 |

## 数字规则

不得写建议值为真实结果。测试数用 `rg -n '^def test_' tests | wc -l` 等现场命令统计；通过率必须来自本次测试输出。业务指标没有数据时写“设计评估指标”，不能写“提升 X%”。

## 反模式

- 只堆 FastAPI、Agent、RAG 等关键词。
- 把确定性类路由描述成自治多 Agent 协作。
- 把 Fake provider 自动化测试写成真实 DeepSeek 线上调用验证。
- 把进程内会话写成生产级长期记忆。
- 描述不存在的客户、机构规模、营收或上线效果。
