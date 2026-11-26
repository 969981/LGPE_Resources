# 全量容器审计

[返回资源中心](README.md)

Git tree 两个已解包目录返回 truncated=false：
| 类别 | 容器目录 | 具名 BNTX 路径 | 分类内 Git blob 去重 |
|---|---:|---:|---:|
| bin/app | 374 | 373 | 296 |
| bin/archive | 643 | 16614 | 6822 |
| 独立 BNTX（历史扫描） | — | 1344 | 未统计 |

SARC 8448 个已解包路径，包括 4363 BFLAN、1091 FLYT、1091 BFLYT、1015 FLAN、472 BFCPX、373 BNTX、22 BUSHVT、21 BNSH。staff_roll/bin/staff_roll_01.arc 没有已具名 Combined BNTX。
GFPAK 解包树 52358 路径（含 1685 JSON 衍生文件）；16614 BNTX、11111 BNSH_FSH、11111 BNSH_VSH、7366 无扩展名、3393 GFBANM、616 GFBANMCFG、308 GFBMDL、154 GFBPOKECFG。
GFPAK BNTX 分类：field 9853、pokemon 3666、chara 1863、background 1226、capture 6。
18,331 是历史独立文件与已具名内嵌路径之和，不是 BRTI 或独立图像数。跨分类去重及无扩展名 magic 仍需本地复验。
