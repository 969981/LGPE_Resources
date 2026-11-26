# 道具与精灵球
[返回资源中心](README.md)

原始 bin/app/icon_item/itemdummy.arc；解包 timg/__Combined.bntx（499840 bytes），itemdummy.flyt。
180/180 BRTI 与 180 个 XML textureFile 名称匹配（仅去掉末尾 ^j）；179 个数字资源名和一个 item_dummy。全部 32x32、0x0501 RGB5A1、identity selectors。每项 payload 范围有效。独立 GOB 地址复验计算 180 个 alpha mask，均有非透明与透明像素；没有逐像素双解码对账。
精灵球候选 item_0001 至 item_0004；原始 ID 与语义仍需 item data / main 选择函数证据。模型候选另有 bin/archive/chara/data/ob/ob0201_00_masterball.gfpak、ob0202_00_ultraball.gfpak、ob0203_00_greatball.gfpak、ob0204_00_monsterball.gfpak。模型贴图不能代替 UI 图标。
