# T10 — main 逆向/运行时加载、捕获、RNG、交换

**优先级：** P1  \n**依赖：** T00 T07

## Codex 子任务提示词

请先阅读项目根目录的 `AGENTS.md`、`CODEX_MASTER_PROMPT.md` 和此文件。你负责 T10：main 逆向/运行时加载、捕获、RNG、交换。**不能只写计划或只生成框架**，必须推进到实际验证，若源资源/工具不可用则准确记录阻塞和已完成的独立部分。严禁改动 `../1.0.2/`、添加游戏数据到 Git。

### 执行步骤

1. 确认 `0/main` NSO header/段/压缩，配置当前 Ghidra 版本兼容的 Switch Loader，创建 LGPE 1.0.2 独立工程。
2. 追踪 personal/encount/battle/GO Park 资源加载和解析函数，记录字符串/交叉引用/指针关系；使用 `main+offset` 表示版本化地址。
3. 沿实际代码追野怪创建、遭遇权重、捕获判定、性格/IV/PID/EC、闪光判定与 RNG 实例状态，区分推断与验证。
4. 网络研究可对照 PokeLDN LGPE 1.0.2 页面，验证对应 main hash 和布局，不得混用 SwSh/SV 的偏移/地址。
5. 不研究在线作弊/破坏性网络操作；静态研究优先，本地实验需明确授权和隔离。

### 验收门槛

- [ ] 提供函数表+调用链+基址假设+证据截图/反编译摘要；至少 1 条真实数据加载链可复查。

### 交接输出

将样本路径、原始文件哈希、工具源码 commit、原始/导出签名、测试命令、运行结果、失败明细、后续接口写入 `docs/research/T10-notes.md`；修订 `tasks/INDEX.md` 和 `docs/research/STATUS.md`，提交单独的 Git commit。没有完成真实试解时只能填 `IN_PROGRESS/BLOCKED`，不可标记为 `VALIDATED`。
