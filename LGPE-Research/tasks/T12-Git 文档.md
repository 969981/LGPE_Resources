# T12 — Git 文档、版本锁定、可移植发布

**优先级：** P2  \n**依赖：** T11

## Codex 子任务提示词

请先阅读项目根目录的 `AGENTS.md`、`CODEX_MASTER_PROMPT.md` 和此文件。你负责 T12：Git 文档、版本锁定、可移植发布。**不能只写计划或只生成框架**，必须推进到实际验证，若源资源/工具不可用则准确记录阻塞和已完成的独立部分。严禁改动 `../1.0.2/`、添加游戏数据到 Git。

### 执行步骤

1. 补全 README、AGENTS、工具依赖版本和使用手册，保证新设备复制项目即可按环境变量接入现成资源。
2. 用 Git history 分阶段 commit，输出不得包含 NCA/NSO/NSP、密钥、ROM、完整解码音视频/美术资产。
3. 验证 Windows PS7 与 WSL2 的路径及安装方式，Docker 只在必要任务中使用，不要引入本不必要的复杂部署。
4. 最终交付已验证支持/不支持矩阵、遗留问题和下步逆向的可复现 prompt。

### 验收门槛

- [ ] `uv run python -m unittest ...` 全绿，docs/STATUS 与实测结果一致，Git index 无敏感内容。

### 交接输出

将样本路径、原始文件哈希、工具源码 commit、原始/导出签名、测试命令、运行结果、失败明细、后续接口写入 `docs/research/T12-notes.md`；修订 `tasks/INDEX.md` 和 `docs/research/STATUS.md`，提交单独的 Git commit。没有完成真实试解时只能填 `IN_PROGRESS/BLOCKED`，不可标记为 `VALIDATED`。
