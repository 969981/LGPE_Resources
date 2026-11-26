# T09 — Wwise 音频、SoundBank 及事件映射

**优先级：** P1  \n**依赖：** T01 T03

## Codex 子任务提示词

请先阅读项目根目录的 `AGENTS.md`、`CODEX_MASTER_PROMPT.md` 和此文件。你负责 T09：Wwise 音频、SoundBank 及事件映射。**不能只写计划或只生成框架**，必须推进到实际验证，若源资源/工具不可用则准确记录阻塞和已完成的独立部分。严禁改动 `../1.0.2/`、添加游戏数据到 Git。

### 执行步骤

1. 先执行 `uv run lgpe decode-audio --limit 5` 查看拟处理清单，安装并验证 vgmstream-cli 后增加 `--execute`。
2. 输出 `.wem→.wav`，检查 RIFF WAV、采样率、声道、非零样本和实际可播放性；做重复运行跳过。
3. 对 `.bnk` 使用 wwiser 读取事件、SoundBank、内嵌媒体与外部 WEM id 的关系；不能读出的 bank 记录为仅元数据。已扩展到 265 个本地 BNK/XML，静态关系生成 `manifests/wwise_event_media.jsonl`；外部 ID、未命中对象和未知名称明确保留为状态。
4. `.bseq`/`.wav` 逐个检查魔数，标准 WAV 原生可打开不能算解码成新格式。
5. 对 `.bseq` 验证实际 SESD 版本后，先用 5 个真实样本做结构解码和原始/导出比较，再按 20→全部兼容文件扩展。JSON 必须保留完整原始字节，分别报告二进制精确往返与结构化重解析相等；命令语义不明时保持 UNKNOWN。
6. 对已有 RomFS `.wav` 检查 RIFF/WAVE 格式标签；仅对实际 Microsoft ADPCM 样本运行 vgmstream 解成 PCM16 WAV。按路径镜像写入 `decoded/1.0.2/romfs/`，校验 PCM16、声道、采样率、源 `fact` 帧数、源/输出哈希与收据；原生 PCM 保持 UNKNOWN，不把后缀或已有文件当作解码证据。

### 验收门槛

- [x] 至少 5 个真实 WEM WAV 转换和 1 个 BNK metadata 实例；有大小/耗时/失败数。实际全量结果：1,134 WEM→WAV、265 BNK→XML，零批次失败/待处理。
- [x] `.bseq` 至少 5 个真实样本解码后扩展全量兼容集；实际 381 个 SESD v3 文件中 353 个得到结构 JSON、28 个 demo/cutscene parser 不支持项有原始异常记录；353 个语义重解析相等，输出 receipt 353/353 校验通过。命令语义、Wwise 播放关系和运行时序列概率仍未验证。
- [x] 实际 318 个 RomFS `.wav` 样本检查并批量验证；318 个均为 Microsoft ADPCM，298 个生成 PCM16 输出、20 个原有镜像输出经新鲜解码后字节相同并登记为 `DECODED_EXISTING_VERIFIED`，0 失败。318/318 输出与源路径、哈希、通道、采样率和 `fact` 帧数核验通过；证据见 `docs/research/T09-notes.md`。

### 交接输出

将样本路径、原始文件哈希、工具源码 commit、原始/导出签名、测试命令、运行结果、失败明细、后续接口写入 `docs/research/T09-notes.md`；修订 `tasks/INDEX.md` 和 `docs/research/STATUS.md`，提交单独的 Git commit。没有完成真实试解时只能填 `IN_PROGRESS/BLOCKED`，不可标记为 `VALIDATED`。
