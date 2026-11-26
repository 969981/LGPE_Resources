# T00 — Windows 环境及已解包资源确认

**优先级：** P0  \n**依赖：** 无

## Codex 子任务提示词

请先阅读项目根目录的 `AGENTS.md`、`CODEX_MASTER_PROMPT.md` 和此文件。你负责 T00：Windows 环境及已解包资源确认。**不能只写计划或只生成框架**，必须推进到实际验证，若源资源/工具不可用则准确记录阻塞和已完成的独立部分。严禁改动 `../1.0.2/`、添加游戏数据到 Git。

### 执行步骤

1. 执行 `uv sync` 与 `uv run python -m unittest discover -s tests -v`；先检测真实 exe/romfs 目录和源文件，而不是依赖 tree 推断字节。
2. 执行 `uv run lgpe tree-catalog`、`uv run lgpe doctor`；记录 Windows/uv/dotnet/WSL/Ghidra 可用情况，PowerShell 与 WSL 路径映射。
3. 确认 0/ main 是可导入的 Switch NSO 等文件；1/bin 为 RomFS，不能无证直接认定未确认 NCA 类型。
4. 列出 X: 剩余空间、目录是否只读、主要样本大小，严禁复制整个 ROM 耗空间。

### 验收门槛

- [ ] 实测 doctor 状态和路径、tests 全绿，输出 `T00-notes.md` 含版本及遇到的障碍。
- [ ] 本机实物不存在时如实报告阻塞并记录 `NOT_RUN_ON_LOCAL_DUMP`。

### 交接输出

将样本路径、原始文件哈希、工具源码 commit、原始/导出签名、测试命令、运行结果、失败明细、后续接口写入 `docs/research/T00-notes.md`；修订 `tasks/INDEX.md` 和 `docs/research/STATUS.md`，提交单独的 Git commit。没有完成真实试解时只能填 `IN_PROGRESS/BLOCKED`，不可标记为 `VALIDATED`。
