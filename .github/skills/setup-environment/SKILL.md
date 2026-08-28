---
name: setup-environment
description: "Use when bootstrapping, installing, verifying, or launching this multi-campus education scheduling project on a fresh macOS, Linux, or Windows checkout, with or without optional LLM and semantic-retrieval dependencies."
---

# Setup Education Scheduling Environment

核心系统离线优先：没有模型 key 也必须能完成安装、初始化、验证和启动。模型与语义检索是显式可选项。

## 快速执行

macOS / Linux：

```bash
bash .github/skills/setup-environment/scripts/setup.sh
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .github\skills\setup-environment\scripts\setup.ps1
```

| 选项 | 作用 |
|---|---|
| `--run` / `-Run` | 验证后启动 `127.0.0.1:8001` |
| `--ai` / `-AI` | 加装 `requirements-ai.txt` |
| `--test` / `-Test` | 加装开发依赖并运行 pytest |
| `--force` / `-Force` | 明确删除并重建本项目 `.venv` |
| `--no-verify` / `-NoVerify` | 跳过 smoke test |

## 流程

1. 检查 Python 3.11+。
2. 创建或复用项目根目录 `.venv`。
3. 安装 `requirements.txt`；只有 `--ai` 才安装 AI 依赖。
4. `.env` 不存在时从 `.env.example` 复制。空模型字段合法。
5. 创建 `data/`。
6. 运行 `verify_env.py`，验证核心导入、应用创建与 `/health`。
7. `--test` 时运行离线测试，`--run` 时启动应用。

始终使用项目 `.venv` 的 Python。不要把填有密钥的 `.env` 提交到 Git。

## 模型配置

本地字段解析、任务分类、排课冲突检查、关键词知识检索和 API 均不需要 key。需要开发 LLM 结构化解析或语义检索时再填写 `LLM_*` / `EMBEDDING_*`，并使用 `--ai`。

Chat 与 Embedding 可以来自不同 provider；DeepSeek 仅作为 Chat provider 时，Embedding 可改用 Qwen、Zhipu、OpenAI 或其他 OpenAI-compatible 服务。配置为空时验证器只提示“可选 AI 未配置”，不能判定核心安装失败。

## 验收

成功输出必须包含：

- 核心依赖导入通过。
- `create_app(initialize_demo=False)` 可创建应用。
- `/health` 返回 `education-scheduling-agent`。
- 如果启用 `--test`，pytest 全部通过。

常见故障：Python 3.10 不支持本项目使用的 `StrEnum`；端口占用时改用 `--port 8002`；AI 导入失败时确认是否执行 `--ai`，不要阻塞核心模式。
