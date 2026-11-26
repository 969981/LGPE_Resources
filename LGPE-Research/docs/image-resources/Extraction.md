# 提取流程
[返回资源中心](README.md)

从 LGPE-Research 执行：
```powershell
uv sync
uv run python -m unittest discover -s tests -v
uv run python scripts/audit_image_resources.py
uv run python scripts/audit_image_resources.py --prefix bin/app/icon_item/ --png
uv run python scripts/audit_image_resources.py --prefix bin/app/icon_type/ --png
uv run python scripts/audit_image_resources.py --png
```
脚本重新读取原始 SARC/GFPAK、松散 BNTX、BFFNT sheet；GFPAK 不依赖扩展名，直接检查成员 magic。记录源 SHA256、成员 index/path/hash、BNTX hash、BRTI index/name/dimensions/format/selectors/payload offset/hash。PNG 为受限 RGB5A1/BC7 raw RGBA adapter；仅接受 identity selectors、单层、单 mip、block-linear，其他情况显式保留索引并标记不支持。输出 work/image-resources，默认不生成 PNG，不修改原始资源或生产 manifest；每次运行重写本地 JSONL；先保留上次报告再运行带 prefix 的任务。PNG 以尺寸、色彩空间和 RGBA 哈希命名，保留所有路径别名。原生 UI 裁切、材质、UV、遮罩、文字、运行时选择均未完成。新增脚本与测试尚未在本地 checkout 执行。
RGB5A1 通道掩码参考 BNTX-Editor dds.py 的 rgb5a1（R 低5位，G 5-9，B 10-14，A 15）；GOB 地址参考 Tegra block-linear 规则及已有 BNTX-Extractor。BC7 使用项目已锁定的 texture2ddecoder。独立解码器的实际像素 parity 后续执行。
