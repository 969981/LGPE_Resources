# LGPE ImageResourceCore

[返回资源中心](README.md) · [前轮记录](CoreIconValidation-20261126.md)

## 实际 CI 验收
[Run 45782517285](https://github.com/969981/LGPE_Resources/actions/runs/45782517285) 在 2026-11-26 08:22 UTC 成功。基准 da5bc965366f024d528d543f4313836c8e1c6588。3 单测通过；11/11 SARC；725/725 PNG roundtrip；544 唯一 RGBA（尺寸、色彩空间、内容）；BC7 324/324 Pillow vs texture2ddecoder 完全一致，max delta 0。报告 artifact 15098712699，ZIP sha256 1d032723758690cb24208614edbf275d57a39b52264212338b4939e7cef0524e。PNG 临时验证后删除，并未发布。

## 业务映射证据
原版 personal_total.bin (Git blob acbf72f76cc1bcf0fb3cdb57ef9cd8cef6f91b25) 82320 bytes/980 rows/84 stride。使用 +0x12 gender、+0x1c FormStatsIndex、+0x20 FormCount；按 base index 或 FormStatsIndex+form-1 关联。
221 个资源中 219 非000占位项全部符合 personal form bounds，196 个非占位 species/form pair。000 的两项不强行绑定个人数据。221/221 MONSNAME label 关联；179/179 ITEMNAME/ITEMINFO 关联，item_dummy 保留占位。Pikachu 25 FormCount=9, FormStatsIndex=959，form1–7 的 ratio=0，form8 ratio=127；form0/8 有 m/f；1–7 仅 m。Eevee 133 FormCount=2, FormStatsIndex=979。n 字符的17项对应 ratio255；m/f/s 为资源符号，不是原生 enum 映射。全部 palette 后缀 n，不推断异色策略。
属性图标 index0–17 与 typename 消息 index 同序，但标签 000–008,010–018；火图标9对应 TYPENAME_010。personal 原始 Type1/2 是连续编号（喷火龙9/2），不能将消息标签直接当 runtime TypeID。
三个 Resolver 仅精确资源键查询；未验证原生 fallback、性别 enum、异色、服装/搭档选择，不自动替换为其他图标。
## 本地执行
```powershell
uv run --with pillow python scripts/verify_core_icons.py --png-dir work/core-icons/png
uv run python scripts/build_core_icon_database.py
```
输出 work/core-icon-database.json，保存原始路径、BRTI index/name、尺寸、hash、中文名、道具描述、personal 索引及证据等级。数据库本地生成，不提交游戏图片/批量原文。
下一步从 exact main NSO 查找 icon_pokemon / poke_icon_ / item_%04 / typeIcon 等资源字符串及其 ARM64 xref；以真实 caller 参数流为准，验证原生 selector，不把上述静态关系冒充运行时等价。
