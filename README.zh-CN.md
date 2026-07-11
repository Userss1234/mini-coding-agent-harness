# Mini Coding Agent Harness

一个用于代码仓库维护实验的轻量级 Coding Agent Harness。

这个项目不是聊天机器人，也不是简单套一层 LLM API。它的定位是一个小型 agent 基础设施项目：模型负责决定下一步做什么，harness 负责提供工具、权限、执行 trace、上下文压缩、长期记忆、错误恢复建议和评估报告。

英文文档：[README.md](README.md)

开源许可证：[MIT](LICENSE)

## 快速开始

```powershell
python -m pip install -r requirements.txt
python -m pytest
python main.py eval --mode scripted
python main.py demo --task python_bugfix
```

如果要跑真实模型 smoke eval，先把 `.env.example` 复制成 `.env`，填入 DeepSeek/OpenAI-compatible 或 Anthropic-compatible API key，然后运行：

```powershell
python main.py eval --mode agent --task python_bugfix --task python_add_tests --task multi_file_service_fix
```

## 项目快照

- **Scripted benchmark：**31 个确定性代码仓库维护任务，当前提交快照 31/31 通过。
- **真实 Agent eval：**DeepSeek `deepseek-chat` 运行 10 个代表任务，10/10 通过；扩展 20 任务评估 20/20 通过。
- **Ablation：**已提交 2 任务 memory/context 对比，以及 `context_pack_retrieval` 的 retrieval-on/off 对比。
- **CI：**`.github/workflows/ci.yml` 会运行测试、语法检查、scripted benchmark、trace HTML 渲染和 MCP smoke 验证。
- **报告入口：**优先看 [`reports/AGENT_EVAL_20_TASKS.md`](reports/AGENT_EVAL_20_TASKS.md)、[`reports/AGENT_EVAL_10_TASKS.md`](reports/AGENT_EVAL_10_TASKS.md)、[`reports/AGENT_COMPARE_2_TASKS.md`](reports/AGENT_COMPARE_2_TASKS.md) 和 [`reports/AGENT_RETRIEVAL_COMPARE_CONTEXT_TASK.md`](reports/AGENT_RETRIEVAL_COMPARE_CONTEXT_TASK.md)。

## 项目能做什么

这个 harness 支持如下代码维护流程：

```text
任务 -> todo 计划 -> 工具调用 -> 文件/测试/Git 操作 -> trace.jsonl -> REVIEW.md / EVAL.md
```

当前能力：

- 文件、Shell、Git、测试、记忆、报告工具注册系统
- 写文件权限检查，以及使用 `shell=False` 执行的 Shell/Git allowlist 权限策略
- 需要显式确认的文件删除，并记录审计元数据
- 基于精确文本匹配的局部文件编辑
- pytest 执行，并记录返回码、耗时、目标和 timeout 元数据
- Git diff 检查，并能清晰处理“当前不是 Git 仓库”的情况
- Todo planning 和基础 todo 质量检查
- 支持注入模型客户端，用于确定性测试 agent loop
- 每次工具调用都会写入 JSONL trace
- 对临时性模型请求失败和非写工具 handler 失败进行 retry/backoff
- 基于失败 trace 事件生成语义 retry plan
- 工具失败后自动把 retry-plan 上下文反馈给模型循环
- 从长 trace 和 max-turn 停止中压缩上下文摘要
- 按 query 检索仓库上下文片段，并返回文件路径和行号
- 将成功工作流保存到 `skills/*.md`，并支持按 query 做相关性排序
- 对失败工具调用生成错误恢复建议
- 生成有证据来源的仓库审查报告
- 生成静态 HTML trace 报告
- 通过 MCP stdio server 暴露同一套带权限检查的工具注册表、部分只读资源和 prompt 模板
- 生成带每任务 trace 的确定性 Markdown/JSON 评估报告
- GitHub Actions CI 会运行测试、语法检查、benchmark、trace-report artifact 和 MCP 协议 smoke 检查
- 生成机器可读的权限策略报告，说明 workspace、Shell、Git 和 sandbox 边界

## 架构

```text
main.py
  -> harness.agent.run_agent()        模型驱动工具循环
  -> harness.review.inspect_repo()    确定性仓库检查
  -> harness.evaluation.run_evaluation() benchmark runner

harness.tools.ToolRegistry
  -> 权限检查
  -> 工具分发
  -> trace 记录

harness.trace.TraceLogger
  -> 追加写入 JSONL 事件
```

面向模型的工具都注册在 `harness/tools.py` 中。每个工具返回 `ToolResult`，包含 `ok`、`output` 和可选 `metadata`。`ToolRegistry.call(...)` 会先执行权限策略，再调用工具，并将结果写入 JSONL trace。

## 工具列表

| 工具 | 作用 |
|---|---|
| `todo_write` | 创建/更新任务计划，并记录 todo 质量元数据。 |
| `list_python_files` | 列出 Python 文件，忽略缓存和评估工作区。 |
| `read_file` | 读取工作区文件，支持指定行区间、行数/字符数限制和读缓存元数据。 |
| `context_pack` | 按任务 query 检索相关工作区片段，返回路径、行号和评分。 |
| `write_file` | 写文件，并记录 diff 元数据。 |
| `edit_file` | 替换只出现一次的精确文本块。 |
| `delete_file` | 只有显式确认时才删除单个文件；拒绝删除目录。 |
| `grep` | 按子串搜索文件。 |
| `permission_policy` | 报告写文件、Shell、Git 和 sandbox 权限边界。 |
| `shell` | 使用 `shell=False` 运行 allowlist 内的命令，并阻止 shell operator、force flag 和会修改状态的 Git 命令。 |
| `run_py_compile` | 检查 Python 语法。 |
| `run_tests` | 运行 pytest；当 `tests/` 下有 pytest 文件时默认跑 `tests/`，否则跑 workspace 根目录。 |
| `git_diff` | 在 Git worktree 内运行 `git diff -- .`。 |
| `compact_context` | 将 trace 压缩为目标、文件、错误和下一步。 |
| `recover_errors` | 对失败工具调用分类并给出恢复建议。 |
| `retry_plan` | 将失败 trace 事件转换成带建议工具的有序下一步计划。 |
| `save_memory` | 将可复用工作流保存到 `skills/*.md`。 |
| `list_memories` | 列出已保存的工作流记忆，可选按 query 相关性排序。 |
| `read_memory` | 读取某条工作流记忆。 |
| `cache_stats` | 报告读缓存命中/未命中指标。 |

## 运行方式

在项目目录中运行：

可选 editable 安装：

```powershell
python -m pip install -e ".[dev]"
mini-agent tools
```

```powershell
python main.py tools
python main.py manual
python main.py demo --task python_bugfix
python main.py --workspace . --trace artifacts/mcp_trace.jsonl mcp-server
python main.py --allow-write --fresh-trace inspect
python main.py trace-report --input trace.jsonl --output TRACE.html
python main.py eval --mode scripted
python main.py eval --mode scripted --json-output EVAL.json
python main.py eval --mode scripted --compare --task syntax_check
python main.py eval --mode scripted --compare-retrieval --task syntax_check
python main.py eval --mode agent --retrieval off --task python_bugfix
python main.py eval --mode scripted --category multi_file
```

本地 demo 流程：

```text
1. todo_write 创建修复计划。
2. run_tests 复现失败的 calculator 测试。
3. read_file 读取 calculator.py。
4. edit_file 修复 bug。
5. run_tests 验证修复。
6. git_diff 输出最终改动。
7. trace-report 把 JSONL trace 渲染成 HTML。
```

demo 会把生成结果写到 `artifacts/demo/python_bugfix/`。已提交的 demo 示例在 `reports/DEMO_python_bugfix.md` 和 `reports/DEMO_python_bugfix_TRACE.html`。

可选的模型驱动循环：

```powershell
python main.py --fresh-trace ask "List Python files, run tests, and summarize with sources."
python main.py eval --mode agent --memory on --context on --task python_bugfix
```

模型循环和 `eval --mode agent` 会在可用时读取 `.env` 中的变量，可以用 `.env.example` 作为模板。当前支持 Anthropic-compatible 客户端，也支持 DeepSeek/OpenAI-compatible chat-completions 客户端。agent 评估可能多次调用模型，调试单个 fixture 时建议加 `--task <task_id>`。

```text
MODEL_PROVIDER=deepseek
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
AGENT_EVAL_MAX_TURNS=12

# 或 Anthropic-compatible：
ANTHROPIC_API_KEY
ANTHROPIC_BASE_URL
MODEL_ID
```

建议先跑一个小规模真实 agent smoke：

```powershell
python main.py eval --mode agent --output artifacts/AGENT_EVAL.md --json-output artifacts/AGENT_EVAL.json --trace-dir artifacts/agent_eval_runs --task python_bugfix --task python_add_tests --task python_import_fix --task config_default_fix --task multi_file_service_fix
python main.py trace-report --input artifacts/agent_eval_runs/agent/python_bugfix.jsonl --output artifacts/AGENT_TRACE_python_bugfix.html
```

memory/context ablation 示例：

```powershell
python main.py eval --mode agent --compare --output artifacts/AGENT_COMPARE_2_TASKS.md --json-output artifacts/AGENT_COMPARE_2_TASKS.json --trace-dir artifacts/agent_compare_runs --task python_bugfix --task multi_file_service_fix
```

context retrieval ablation 示例：

```powershell
python main.py eval --mode agent --compare-retrieval --output artifacts/AGENT_RETRIEVAL_COMPARE_CONTEXT_TASK.md --json-output artifacts/AGENT_RETRIEVAL_COMPARE_CONTEXT_TASK.json --trace-dir artifacts/agent_retrieval_context_task_runs --task context_pack_retrieval
python main.py eval --mode agent --retrieval on --output artifacts/AGENT_RETRIEVAL_ON.md --json-output artifacts/AGENT_RETRIEVAL_ON.json --trace-dir artifacts/agent_retrieval_on_runs --task python_bugfix
python main.py eval --mode agent --retrieval off --output artifacts/AGENT_RETRIEVAL_OFF.md --json-output artifacts/AGENT_RETRIEVAL_OFF.json --trace-dir artifacts/agent_retrieval_off_runs --task python_bugfix
```

## 报告

- `REVIEW.md` 由 `python main.py --allow-write --fresh-trace inspect` 生成。
- `TRACE.html` 由 `python main.py trace-report` 生成。
- `EVAL.md` 由 `python main.py eval` 生成。
- `EVAL.json` 可以用 `python main.py eval --json-output EVAL.json` 生成。
- `artifacts/AGENT_EVAL.md` 和 `artifacts/AGENT_EVAL.json` 可以由上面的小规模真实 agent smoke 命令生成。
- `artifacts/AGENT_TRACE_<task>.html` 可以由任意单任务 agent trace 通过 `trace-report` 生成。
- `reports/DEMO_python_bugfix.md` 和 `reports/DEMO_python_bugfix_TRACE.html` 是已提交的本地 demo 展示文件。
- `reports/AGENT_EVAL.md` 是已提交的 DeepSeek `deepseek-chat` 真实 agent 报告，覆盖 10 个代表性 agent-mode 任务。
- `reports/AGENT_COMPARE_2_TASKS.md` 是已提交的 memory/context ablation 报告，覆盖 2 个代表性 agent-mode 任务。
- `reports/AGENT_RETRIEVAL_COMPARE_CONTEXT_TASK.md` 是已提交的 retrieval-on/off ablation 报告，覆盖 `context_pack_retrieval` 任务。
- `reports/AGENT_TRACE_python_add_tests.html` 和 `reports/AGENT_TRACE_multi_file_service_fix.html` 是这次真实 agent 运行生成并提交的 trace viewer 示例。
- `reports/AGENT_TRACE_retrieval_on_context_pack.html` 和 `reports/AGENT_TRACE_retrieval_off_context_pack.html` 展示 retrieval ablation 中开启和关闭 `context_pack` 的两条路径。
- `reports/README.md` 说明已提交的 demo 和真实 agent evaluation 展示文件。
- `trace.jsonl` 记录当前 inspect/ask 运行。
- `eval_runs/*.jsonl` 记录每个评估任务的独立 trace。

`REVIEW.md`、`TRACE.html`、`EVAL.json`、`COMPARE.json`、`trace.jsonl`、`eval_runs/` 和 `artifacts/` 是生成产物，会被 Git 忽略。`EVAL.md` 会保留为最新 benchmark 快照。

## MCP Server

harness 现在可以把同一套带权限检查的 `ToolRegistry` 暴露为最小 MCP stdio server：

```powershell
python main.py --workspace . --trace artifacts/mcp_trace.jsonl mcp-server
```

如果希望 MCP client 可以编辑已有文件，把 `--allow-write` 放在 `mcp-server` 前面：

```powershell
python main.py --workspace . --trace artifacts/mcp_trace.jsonl --allow-write mcp-server
```

当前支持的 MCP 方法包括：`initialize`、`notifications/initialized`、`ping`、`tools/list`、`tools/call`、`resources/list`、`resources/read`、`resources/templates/list`、`prompts/list` 和 `prompts/get`。`MCP.md` 里有消息示例和边界说明。

server 也支持 `resources/templates/list`，用于安全读取 workspace 文本资源，例如 `harness://workspace/README.md`。`.env`、`.git`、`artifacts` 和 `eval_runs` 等敏感或生成路径会被阻断。已提交的协议交互 transcript 在 `reports/MCP_SMOKE.md`。

如果要接入支持 MCP 的客户端，可以复制 `examples/mcp_config.example.json`，把 `/absolute/path/to/mini-coding-agent-harness` 替换成本地项目绝对路径。

## CI

`.github/workflows/ci.yml` 会运行项目快照所需的可复现检查：

- 从 `requirements.txt` 安装依赖
- 编译 `main.py`、`harness/` 和 `tests/`
- 运行 `python -m pytest`
- 运行完整 scripted benchmark，并生成 Markdown 和 JSON artifact
- 将一个 sample trace 渲染成 `TRACE.html`
- 运行 MCP 协议 smoke 检查，并上传 `MCP_SMOKE.md`

## 评估

当前 benchmark 有 **31 个任务**，全部是确定性任务。它包含 harness 能力检查、注入式 fake client agent-loop smoke test、隔离的代码维护 fixture、行区间文件读取、query-ranked context retrieval、静态 trace HTML 渲染、无 shell 命令执行、权限策略报告、多文件契约修复任务、语义 retry planning、memory 相关性排序，以及带 `src/` 目录的 package 结构 fixture。

任务覆盖：

- Python 语法检查
- pytest 测试执行
- 注入式 fake client agent-loop 模拟
- 上下文压缩
- 行区间文件读取
- query-ranked context pack 检索
- 静态 HTML trace 报告生成
- 错误恢复
- 语义 retry planning
- 工作流记忆列表
- 工作流记忆相关性排序
- Python bug 修复
- 添加缺失测试
- README 更新
- import/name mismatch 修复
- 配置默认值修复
- JSON 配置更新
- CLI 参数校验修复
- 环境变量默认值修复
- CSV 解析边界条件修复
- 日期格式修复
- 分页 off-by-one 修复
- 敏感 token 脱敏修复
- 无 shell 的 allowlist 命令执行和权限策略报告
- 路径规范化修复
- 依赖版本固定更新
- 可变默认参数修复
- 多文件 service/repository 契约修复
- 多文件 API handler/response 契约修复
- `src/` package 结构下的订单/价格跨文件修复

最新评估报告会跟踪：

- 评估模式
- memory 和 context-compaction 设置
- context retrieval 设置
- 成功率
- 平均工具调用次数
- 工具调用分布，包括 `context_pack` 和 `read_file`
- 平均耗时
- input/output tokens
- 估算模型成本
- 可选的机器可读 JSON 输出
- 失败工具调用次数
- 失败分类
- 每个任务的 trace 路径

可以用 `--compare` 对同一组任务运行四种配置：

```text
memory-on_context-on
memory-off_context-on
memory-on_context-off
memory-off_context-off
```

可以用 `--retrieval on|off` 控制 evaluation 时是否暴露 `context_pack`，用于做 retrieval ablation，而不改变其他 harness 行为。

可以用 `--compare-retrieval` 在相同 memory/context 设置下生成两行 retrieval-on/retrieval-off 对比报告。
对比报告会包含平均 `context_pack` 和 `read_file` 调用次数，方便不只看通过率，也看 retrieval 是否改变了工具使用结构。

可以用 `--task <task_id>` 或 `--category <category>` 运行一小部分任务，方便调试某个 fixture 或 agent 行为。当前分类包括 `agent_loop`、`code_maintenance`、`code_quality`、`configuration`、`documentation`、`memory`、`multi_file`、`recovery`、`security`、`tests` 和 `trace`。

当前诚实状态：这是一个 31 任务确定性 benchmark，并且已经有 query-ranked context retrieval、memory/context ablation 报告、注入式 agent-loop smoke test、静态 trace HTML 渲染、无 shell 命令执行、权限策略报告、CI validation，以及 DeepSeek/OpenAI-compatible 的真实 API agent 入口。当前已提交一份 DeepSeek `deepseek-chat` 真实 agent 报告，覆盖 10 个代表性 agent-mode 任务且 10/10 通过；同时提交了 2 个任务的 memory/context ablation，四种配置都通过。已提交的 `context_pack_retrieval` retrieval ablation 显示：retrieval-on 会真实调用 `context_pack` 并通过，retrieval-off 在工具不暴露时失败。完整 31 任务真实 API 对比数据还需要更大规模运行和分析后再作为广义 autonomous benchmark 成果声明。

## Git Baseline

这个项目应该在 Git worktree 中运行。`git_diff` 使用：

```powershell
git diff -- .
```

建立初始 baseline commit 后，后续工具修改和报告修改都可以通过 `git_diff` 检查。

## 当前限制

- 稳定 benchmark 快照仍然是 scripted，并包含注入式 agent-loop smoke test；真实 API 驱动的模型评估已支持入口，并有 10 任务报告、2 任务 memory/context ablation 和一个聚焦 retrieval-on/off ablation，但还需要完整任务集对比运行和更广泛的 retrieval 调优。
- workflow memory 可以按 query 排序并注入 agent 评估提示，但排序仍然是词法匹配，还不是 embedding 检索。
- max-turn 停止时会生成 context compaction 摘要，但还没有实现基于摘要的自动续跑。
- retry/backoff 已能处理临时性模型/API 失败和非写工具 handler 失败；retry_plan 会在工具失败后自动反馈给模型循环，但还不会自动执行修复。
- Shell/Git 权限检查已经使用 allowlist 和 `shell=False`，MCP 调用也走同一套策略，但还不是真正的 OS 沙箱。
- MCP 当前是 stdio-only；还没有实现 HTTP/SSE transport、OAuth 或 resource subscriptions。
- workflow memory 不是完整 RAG：当前是本地 Markdown 工作流记忆的词法相关性排序，还没有 embedding、向量库或 rerank。

## 下一步

1. 针对 31 个任务运行并调优真实 API 驱动的 `eval --mode agent`，再和 scripted 模式对比。
2. 增加更真实的仓库 fixture，覆盖嵌套 package、跨文件测试和依赖/配置交互。
3. 增加可选 MCP HTTP/SSE transport 和更完整的 resource subscriptions。
4. 为 shell execution 增加可选 OS 级沙箱。
5. 跟踪自动注入 retry_plan 是否能提升 `eval --mode agent` 成功率并降低工具调用次数。

