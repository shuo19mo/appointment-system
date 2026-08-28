---
name: setup-environment
description: "Use when bootstrapping, installing, verifying, or launching this mandatory DeepSeek multi-campus education scheduling Agent on a fresh macOS, Linux, or Windows checkout."
---

# Setup Education Scheduling Environment

生产聊天强制使用 DeepSeek，启动前必须配置 `DEEPSEEK_API_KEY`。自动化测试通过 Fake LLM 与 Fake Embedding 保持离线、无费用。

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
| `--test` / `-Test` | 加装开发依赖并运行 pytest |
| `--force` / `-Force` | 明确删除并重建本项目 `.venv` |
| `--no-verify` / `-NoVerify` | 跳过 smoke test |

## 流程

1. 检查 Python 3.11+。
2. 创建或复用项目根目录 `.venv`。
3. 安装 `requirements.txt`，其中包含 DeepSeek、FAISS 和本地 Embedding 依赖。
4. `.env` 不存在时从 `.env.example` 复制；`DEEPSEEK_API_KEY` 为空时验证必须失败并提示配置。
5. 创建 `data/`。
6. 运行 `verify_env.py`，验证强制配置、应用创建、`/health` 与 `/ready`。
7. `--test` 时运行离线测试，`--run` 时启动应用。

始终使用项目 `.venv` 的 Python。不要把填有密钥的 `.env` 提交到 Git。

## Agent 配置

固定配置为 `AGENT_MODE=llm`、`MODEL_PROVIDER=deepseek`。Chat 使用 DeepSeek OpenAI-compatible API；知识检索使用本地 `BAAI/bge-small-zh-v1.5` Embedding 与 FAISS。首次启动可能需要下载本地模型。密钥只放在 `.env`，不得提交。

## 验收

成功输出必须包含：

- Agent、FAISS 与本地 Embedding 依赖导入通过。
- 强制 DeepSeek 配置通过。
- 使用无网络 smoke provider 创建应用。
- `/health` 返回 `education-scheduling-agent`。
- `/ready` 返回 `agent_mode=llm` 与当前模型。
- 如果启用 `--test`，pytest 全部通过。

常见故障：Python 版本低于 3.11；`DEEPSEEK_API_KEY` 为空；首次下载 Embedding 模型时网络不可用；端口占用时改用 `--port 8002`。
