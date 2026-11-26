# T04 — GFPAK 批量提取/嵌套资源

**优先级：** P0  \n**依赖：** T01 T03

## Codex 子任务提示词

请先阅读项目根目录的 `AGENTS.md`、`CODEX_MASTER_PROMPT.md` 和此文件。你负责 T04：GFPAK 批量提取/嵌套资源。**不能只写计划或只生成框架**，必须推进到实际验证，若源资源/工具不可用则准确记录阻塞和已完成的独立部分。严禁改动 `../1.0.2/`、添加游戏数据到 Git。

### 执行步骤

1. 用 `bin/archive/pokemon/pm0001_00.gfpak`、`field/area01.gfpak`、`archive/bag.gfpak` 作为多类别样本。
2. 从 pkNX/Toolbox 源码定位 GFPAK parser，识别 header、entry 表、路径名/hash、压缩标志、偏移长度及校验方式；不给没证据的字段命名。
3. 实现或封装稳定的 **headless** 命令，严格控制路径/输出尺寸；不以把 GUI 能打开当成批量成功。
4. 样例内层模型/纹理通过另一工具交叉验证；扩展到一批 20 包后再考虑 643 个候选包的全量处理。

### 验收门槛

- [ ] 至少 3 个不同目录的实际 GFPAK 包完整提取，内部条目数量/长度可核查；失败保留。
- [ ] 输出保留目录/内部文件名，工作器可批量、可停止恢复、可测试。

### 交接输出

将样本路径、原始文件哈希、工具源码 commit、原始/导出签名、测试命令、运行结果、失败明细、后续接口写入 `docs/research/T04-notes.md`；修订 `tasks/INDEX.md` 和 `docs/research/STATUS.md`，提交单独的 Git commit。没有完成真实试解时只能填 `IN_PROGRESS/BLOCKED`，不可标记为 `VALIDATED`。
