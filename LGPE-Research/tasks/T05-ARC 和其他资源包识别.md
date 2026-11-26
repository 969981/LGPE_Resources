# T05 — ARC 和其他资源包识别

**优先级：** P1  \n**依赖：** T04

## Codex 子任务提示词

请先阅读项目根目录的 `AGENTS.md`、`CODEX_MASTER_PROMPT.md` 和此文件。你负责 T05：ARC 和其他资源包识别。**不能只写计划或只生成框架**，必须推进到实际验证，若源资源/工具不可用则准确记录阻塞和已完成的独立部分。严禁改动 `../1.0.2/`、添加游戏数据到 Git。

### 执行步骤

1. 选 `bin/app/battle/bin/battle_command_00.arc` 和不同 UI ARC，先检查 actual header，确认是否 SARC 或另一种自定义容器。
2. 参考 Switch-Toolbox 已支持格式并寻找源码分派器；记录识别规则和假阳性测试。
3. 仅对确认的格式增加解包器，一对多保留内部路径，输出扩展名/二次解码按实际证据进行。

### 验收门槛

- [ ] 至少 2 个 ARC 样本的真实识别与解析结果，无法支持则记录 UNSUPPORTED 而非改后缀。

### 交接输出

将样本路径、原始文件哈希、工具源码 commit、原始/导出签名、测试命令、运行结果、失败明细、后续接口写入 `docs/research/T05-notes.md`；修订 `tasks/INDEX.md` 和 `docs/research/STATUS.md`，提交单独的 Git commit。没有完成真实试解时只能填 `IN_PROGRESS/BLOCKED`，不可标记为 `VALIDATED`。
