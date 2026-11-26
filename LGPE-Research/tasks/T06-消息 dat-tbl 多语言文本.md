# T06 — 消息 dat/tbl 多语言文本

**优先级：** P0  \n**依赖：** T01 T03

## Codex 子任务提示词

请先阅读项目根目录的 `AGENTS.md`、`CODEX_MASTER_PROMPT.md` 和此文件。你负责 T06：消息 dat/tbl 多语言文本。**不能只写计划或只生成框架**，必须推进到实际验证，若源资源/工具不可用则准确记录阻塞和已完成的独立部分。严禁改动 `../1.0.2/`、添加游戏数据到 Git。

### 执行步骤

1. 使用 `message/English/common/bag.dat` + `bag.tbl` 与 `message/English/script/master_trainer.dat/.tbl` 作为样本。
2. 交叉查 `pkNX.Structures.Text.TextFile` / `pokedat --version=LGPE`，确认每条文本索引、标签、转义、语言、控制码。
3. 实现全语言批量读取，在 `decoded/.../message/...` 输出 `foo.json` 或 `foo.txt`；只有真实解码的结果可以使用新后缀。
4. 多语言统一索引/比较未翻译行、乱码、非法控制符；给出错误位置并保留原始数据证据。

### 验收门槛

- [ ] 至少英文和第二语言各 2 对真实读出，含控制码/换行的抽样一致性检查。
- [ ] 给出配对文件数、成功/失败比例及真实例子的哈希而不将大量版权文本提交 Git。

### 交接输出

将样本路径、原始文件哈希、工具源码 commit、原始/导出签名、测试命令、运行结果、失败明细、后续接口写入 `docs/research/T06-notes.md`；修订 `tasks/INDEX.md` 和 `docs/research/STATUS.md`，提交单独的 Git commit。没有完成真实试解时只能填 `IN_PROGRESS/BLOCKED`，不可标记为 `VALIDATED`。
