# 复制以下内容直接交给 Codex

你现在是 LGPE-Research 项目的首席逆向工程师兼技术任务协调者。工作目录为：
`X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\LGPE-Research`
原始游戏目录是本工程的父目录：
`X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\1.0.2\2b7730a9e56498bbafac2002d4908c6b_NCA\`
其中 `0/` 预计为 ExeFS，`1/` 预计为 RomFS。请在实际本地验证，禁止直接修改原件。

**重要：不是让你只写一个 AGENTS.md 或只建立目录。** 工程基础脚手架已经在 ZIP 里了，请阅读现有 README / AGENTS.md / tasks / docs 之后，马上运行工作流，对实际文件开展分析、验证和解析。若工具尚缺失，请安装/编译可合法获得的开源依赖，接通自动化接口，再开展代表性文件试解；不要在建完目录、复制了工具下载链接或只做了扫描后宣告任务完成。

## 最终目标

1. 针对 LGPE 1.0.2，实现从 **既有已提取的 ROMFS/EXEFS** 到结构化资料的可审计批量分析流程：识别格式→实际提取→实际解码→按原目录映射导出→校验→生成目录及技术文档。能转换的优先 JSON/CSV/PNG/WAV/glTF 等合理格式，不能转换的必须显示 UNKNOWN/UNSUPPORTED，并保留原二进制索引，绝不通过修改后缀假冒解码。
2. 一对一转换保证除扩展名外相对路径和文件名不变；容器类 GFPAK/ARC 以 `<原文件名>.contents/原内部路径` 来表达一对多，不任意重命名/打平，保存容器索引、内部路径、哈希与来源。
3. 分类研究 `.gfpak`, `.arc`, `.gfbmdl`, `.gfbanm`, `.gfbcol`, `.bntx`, `.ptcl`, `.wem`, `.bnk`, `.dat`, `.tbl`, `.bin`, `.amx` 等。优先打通档案包、文本、个人数据、遭遇数据、纹理和音频；其他按技术可行性逐步扩展。
4. 融合 pkNX (LGPE/GameManagerGG/EditorGG)、Switch-Toolbox、pokedat、read_swsh、vgmstream、Blender addon、Ghidra 等开源实现，建立来源版本、license、源码路径、命令与样本交叉验证，不从游戏资源树猜测结构字段。
5. 静态逆向 `main`、检测 C++ RTTI/函数/字段/加载链，后续研究野怪出现、遭遇权重、捕获判定、随机数与 PID/EC/闪光生成、交换通信、GO Park、存档接口。所有地址明确是 **Let's Go Pikachu 1.0.2**，做实际交叉引用，禁止混入其他版本/其他游戏地址。
6. 产出稳定的工程入口 `uv run lgpe ...`、PS7/WSL 兼容脚本、单测、失败重试、结构化结果 `manifests/*.csv/jsonl`, 文档 `docs/`, 可持续 Git 仓库，最终可一键重复执行整个流程。

## 已观察到的来源（不是格式已确认）

`bin/archive/pokemon/*.gfpak`、`bin/archive/field/*.gfpak`、`bin/pokelib/personal/personal_total.bin`、`bin/field/param/encount/encount_data_p.bin`、`.../encount_data_e.bin`、`bin/battle/ai_script/*.amx`、`bin/message/<Language>/{common,script}/*.{dat,tbl}`。上传的 tree 文件已经在 `docs/source_snapshot/pikachu.1.0.2.txt` (UTF-16)，覆盖 1.0.2 数据。先运行 `uv run lgpe tree-catalog` 并比对 `uv run lgpe scan` 的真文件清单；差异要解释。

## 可用环境

- Windows + PowerShell 7、uv、Git、.NET 10、Docker、WSL2 Ubuntu；可使用用户本机既有 Ghidra / IDA 等安装，但不要在默认路径不存在时就假装存在。
- 工具参考地址见 `tools/TOOLS.md`，可以执行 `scripts/Fetch-Tool-Sources.ps1` 拉取开源源码，记录 exact commit。依赖安装方式选择性最小化。
- 不要查找、下载或上传游戏 ROM / prod.keys / title.keys / 专有 SDK/商业 DLL；用户已有合法本地提取结果，本任务从这里开始。

## 立即执行，不要停在准备阶段

**Phase 0** 运行 doctor、snapshot inventory、真实字节扫描、plan、unit tests；生成 `docs/research/STATUS.md`，记录样本路径和基础统计；检查实际目录是否完全一致。没有文件则列出真正阻塞项，仍然改进不依赖源文件的基础设施和文档。

**Phase 1** 并行安排 3 个独立探索单元：A=GFPAK/ARC 容器真实提取；B=message dat/tbl、personal/encount、pkNX GameManagerGG；C=BNTX/model/animation/audio。每个单元先选 2~5 个实际样本，编写 smoke tests，比较原始与导出结果，不可仅 dry-run。

**Phase 2** 优先将 GFPAK 与文本解码做成批量非 GUI CLI；可复用 pkNX C# 源码或建立 .NET 10 小型 headless 工作器，不必重新发明已证实的算法。一次成功样例后再扩大到 20→全部兼容文件。记录失败原因并重试，不能大规模盲扫耗尽磁盘。

**Phase 3** 分别验证音频 `.wem`→`.wav`，BNTX→PNG，gfbmdl→模型，动画、粒子等格式，输出类型、数量和检查脚本。如果只有 GUI 工具，先写导出手册+ingest 适配，后续再自动化。

**Phase 4** ExeFS `main` 静态研究：提取/加载 NSO 段（注意当前 main 的格式）、配置 Ghidra Switch Loader、RTTI、交叉引用文本及个人/遭遇数据读入代码，逐步建立函数证据链。可参照已有的 PokeLDN LGPE 1.0.2 研究，但不同构建的地址不无证套用。

**Phase 5** 正式批处理、产物校验、覆盖率报表、失败清单/重试命令、工具版本锁定、回归测试、README 与文档整理，并提交 Git。

## 严格交付要求

- 每推进一阶段更新 `tasks/INDEX.md`、`docs/research/STATUS.md`，列出实际 `SCANNED / DECODED / FAILED / UNKNOWN` 数量，不要用计划冒充完成。
- 文件树拷贝之外，**至少实际尝试样本解码**。任何不能从本地实际访问/无法安装/有格式障碍的情况需提供精准证据与复现步骤。
- 允许合理分拆子 agent，但不要把整个计划拆成互不沟通的一堆提议。分别汇总提交 commit、处理冲突、统一格式和 manifest。
- 完整使用 `tasks/T00...T12` 作为拆分清单及验收标准。先做可运行部分，按实际发现调整任务顺序。
- 不为赶进度伪造解码结果，不做无证实偏移/布局推定，不把 pkNX 对其他版本的功能写成已在 LGPE 验证。

请从运行命令和文件验证开始，接着做可实际完成的自动化，持续推进研究，不要在只写文档后结束。
