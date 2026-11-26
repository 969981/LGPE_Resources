# LGPE 原版图片资源中心

版本：Let's Go Pikachu 1.0.2；基准提交 74bcb0f16db16ecb0498d23fd28d9346cff3193e。

## 导航
- [核心图标 CI 与 Resolver](ImageResourceCore.md) · [[ImageResourceCore]]
- [核心图标二轮验收](CoreIconValidation-20261126.md) · [[CoreIconValidation-20261126]]
- [全量容器审计](ContainerAudit.md) · [[ContainerAudit]]
- [宝可梦图标](PokemonIcons.md) · [[PokemonIcons]]
- [道具与精灵球](ItemBallIcons.md) · [[ItemBallIcons]]
- [属性图标](TypeIcons.md) · [[TypeIcons]]
- [提取流程与证据级别](Extraction.md) · [[Extraction]]
- [上一轮解包报告](../research/UNPACK-AUDIT-20261126.md)

状态：CI 725/725 PNG 往返一致，324/324 BC7 双解码器一致；详见 ImageResourceCore.md。道具 RGB5A1 180 项进行了独立 GOB 地址计算和 alpha/颜色统计；未生成、逐图验收全部 PNG。宝可梦为 XML 名称证据；大文件 connector 未返回完整字节。不要将模型纹理、原始图标、最终合成图混为一类。
