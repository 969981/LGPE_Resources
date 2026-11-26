# 2026-11-26 核心图标验收（二轮）
[返回资源中心](README.md)

## 实际远端二进制证据

基准提交 c7dff0170ad62eb2788f7036677993d76c6aa171；原始数据未改动。
九个属性 Combined BNTX 均实际读取，139392 bytes/容器，36 BRTI/容器，324/324 与同语言 FLYT 名称匹配（去掉末尾 ^u）。44x44 图形共162，96x32 文字共162，全部 0x2001。所有有效 BC7 块经 GOB 地址转换后按完整字节比较，图形18份唯一（9语言共享），文字158份唯一，合计176。不是 RGBA 去重结果。
道具 Combined BNTX 180项经独立正向 GOB 地址及逆向地址排列比对，180/180 线性 RGB5A1 字一致；按 R低5、G5、B10、A15 的候选通道映射扩展为 RGBA8，180/180 唯一；不透明像素89–816/1024。逐项 CRC32 在 [item-rgb5a1-20261126.csv](evidence/item-rgb5a1-20261126.csv)。这是远端实际计算；未执行 Pillow 独立通道验证或持久化PNG。
宝可梦221 FLYT 名称已知，2.75 MiB BNTX 仍无法通过 connector 完整取回：fetch_blob 返回 UnicodeDecodeError，fetch_file 不提供完整 base64。不得认定已完成像素验收。

## 代码修正
tile mode 实际位于 BRTI+0x10 的 byte，1=block-linear，0=pitch。旧实现读 +0x12 flags；虽然样本 flags=0 使旧代码偶然接受实际 tiled 样本，但不正确。参考 pinned BNTX-Extractor 2c08e8e55fcc666ba6568a102f36dabd6c584e25 的 BRTIInfo 和 swizzle.py。
新增 verify_core_icons.py 直接读取11个原始 SARC；核对 FLYT/BRTI 名称、道具远端 CRC、Pillow PNG round-trip 和 BC7 Pillow vs texture2ddecoder 差异；PNG 默认仅临时产生，显式 --png-dir 可本地导出。不会将游戏图片提交 Git。BC7 差异统计不隐瞒；PASS 是 PNG round-trip，不等于两个 BC7 解码器像素一致。若差异非零需后续独立判定。
运行：
```powershell
uv sync
uv run --with pillow python scripts/verify_core_icons.py --png-dir work/core-icons/png
```
其余 7366 个无扩展名成员仍须全量 magic 扫描；运行 [Extraction](Extraction.md) 中的脚本。本轮不宣称全部 GFPAK 重新解包。
