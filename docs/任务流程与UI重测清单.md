# MaaEOV 任务流程梳理与 UI 变更重测清单

> 自动生成自 `resource/base/pipeline/` 下 20 个流水线文件（`scripts/gen_flow_doc.py`，**请勿手改本文档**；改 pipeline 后重跑生成器，CI 会校验同步）。

> 基准分辨率：1280×720。所有坐标、ROI 均为该基准下的像素值，UI 改版后需逐项复核。

> 共解析到 **19** 个任务入口、**608** 个节点。

## 公共约定（所有任务共用）

- 每个节点的 `next` 列表中，以 `[JumpBack]_XXX` 开头的是**中断/弹窗保底处理**（服务器维护、断线重连、升级弹窗、领奖等），不属正常流程，故下方流程表默认只列**主链路**（`next` 首项）。
- `DirectHit` 节点**必定命中**，多用于「路由/播报/兜底」；`TemplateMatch`/`OCR` 节点按识别结果决定是否执行、再到 `next`。
- **UI 重测重点**：流程表里「识别」列即该步的 UI 依赖——模板图片需重新截图、OCR 文案需逐字核对、坐标需重新定位。任一变更都会导致该节点识别失败、任务卡死或错点。
- 同一节点跨任务复用时只在首次出现处展开，其余位置标 ↺；被多个任务复用的节点单独汇总在文末（改一处影响多处，需一并回归）。

---

## `#StartUp`（启动游戏）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `StartUp` | — | —(仅路由) | `_LaunchGame` |
| &nbsp;&nbsp;1 | `_LaunchGame` | — | StartApp | `_NavigateHomepage` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `_NavigateHomepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | `_EnsureHomepage` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `_EnsureHomepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | `~Homepage` / `_NavigateHomepage` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `~Homepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | （结束） |
| · | `_NavigateHomepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_UpdateGame`, `[JumpBack]_UnfinishedGame`, `[JumpBack]_ConfirmExitTheRoom`, `[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_CancelGeneral`, `[JumpBack]_Cancel1`, `[JumpBack]_Cancel2`, `[JumpBack]_Cancel3`, `[JumpBack]_Cancel4`, `[JumpBack]_ConfirmGeneral`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]_ConfirmSweepResult`, `[JumpBack]_CloseWindowsGeneral`, `[JumpBack]_CloseWindow1`, `[JumpBack]_CloseWindow2`, `[JumpBack]_SkipButton`, `[JumpBack]_LevelUp`, `[JumpBack]_HomeButton`, `[JumpBack]_BackButton`, `[JumpBack]_Login`, `[JumpBack]_EnterGame`, `[JumpBack]_ExitTheRoom`, `[JumpBack]_Loading`, `[JumpBack]_StartUpLoading`, `[JumpBack]_Escape`


## `#LiminalZone`（每周-阈限禁区）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `LiminalZone` | — | —(仅路由) | `LiminalZoneCompletedFromSystem` / `LiminalZoneFromSystem` |
| &nbsp;&nbsp;1 | `LiminalZoneCompletedFromSystem` | OCR['480/480'] roi=[199, 312, 223, 128] | —(仅路由) | （结束） |
| &nbsp;&nbsp;1 | `LiminalZoneFromSystem` | 模板[SystemPage/Settings.png] roi=[0, 559, 149, 149] | Click@[337, 362, 1, 1] | `SelectLevelFromLiminalZone` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `SelectLevelFromLiminalZone` | 模板[BCR/AtLiminalZone.png] roi=[45, 81, 147, 144] | —(仅路由) | `~LiminalZoneNA` / `LiminalZoneFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `~LiminalZoneNA` | 模板[BCR/LiminalZoneNA.png] roi=[859, 585, 140, 135] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `LiminalZoneFromLevel` | OCR['扫荡', '扫汤'] roi=[804, 591, 273, 129] | —(仅路由) | `_CancelLiminalZoneOverflow` / `LiminalZoneCompletedFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `_CancelLiminalZoneOverflow` | OCR['进行探索', '回收物'] roi=[222, 225, 834, 136] | —(仅路由) | `_Cancel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `_Cancel` | — | —(仅路由) | `_CancelGeneral` / `_Cancel1` / `_Cancel2` / `_Cancel3` / `_Cancel4` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `_CancelGeneral` | 模板[Utils/CancelGeneral.png] roi=[481, 318, 155, 153] | Click | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `_Cancel1` | OCR['取消'] roi=[469, 412, 174, 142] | Click | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `_Cancel2` | OCR['取消'] roi=[716, 586, 175, 134] | Click | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `_Cancel3` | OCR['取消'] roi=[465, 590, 150, 130] | Click | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `_Cancel4` | OCR['取消'] roi=[574, 448, 162, 125] | Click | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `LiminalZoneCompletedFromLevel` | OCR['480/480'] roi=[92, 620, 225, 100] | —(仅路由) | （结束） |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_ConfirmLiminalZoneResult`, `[JumpBack]LiminalZoneOutOfStamina`, `[JumpBack]_LevelUp`, `[JumpBack]_SweepMax`, `[JumpBack]_SweepFromLevel`, `[JumpBack]FarmSelectLevel`, `[JumpBack]LiminalZoneSelectLevel`, `[JumpBack]_NavigateLiminalZone`, `[JumpBack]_NavigateSystem`


## `#Farm`（清体力）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `Farm` | — | —(仅路由) | `SelectLevelFromBCR` |
| &nbsp;&nbsp;1 | `SelectLevelFromBCR` | OCR['主线故事'] roi=[1080, 607, 200, 113] | —(仅路由) | `~LevelNA` / `~LiminalZoneNA` / `FarmFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `~LevelNA` | OCR['重复行动'] roi=[804, 591, 273, 129] | —(仅路由) | （结束） |
| · | `~LiminalZoneNA` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `FarmFromLevel` | OCR['扫荡', '扫汤', '快速完成'] roi=[804, 591, 273, 129] | —(仅路由) | `_False` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `_False` | — | —(仅路由) | （结束） |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_ConfirmSweepResult`, `[JumpBack]_ConfirmLiminalZoneOverflow`, `[JumpBack]FarmOutOfStamina`, `[JumpBack]_LevelUp`, `[JumpBack]_SweepMax`, `[JumpBack]_SweepFromLevel`, `[JumpBack]FarmSelectLevel`, `[JumpBack]_NavigateBCR`


## `#CrisisMissionTickets`（危机行动调令）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `CrisisMissionTickets` | — | —(仅路由) | `CrisisMissionTicketsFromBCR` |
| &nbsp;&nbsp;1 | `CrisisMissionTicketsFromBCR` | OCR['主线故事'] roi=[1080, 607, 200, 113] | —(仅路由) | `CrisisMissionTicketsEnterCM` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `CrisisMissionTicketsEnterCM` | — | —(仅路由) | `检测危机行动调令HUD` / `CrisisMissionTicketsSkipped` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `检测危机行动调令HUD` | 模板[BCR/危机行动调令.png] roi=[1165, 15, 94, 45] thr=0.8 | —(仅路由) | `识别危机行动调令数` / `CrisisMissionTicketsSkipped` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `识别危机行动调令数` | OCR['[0-9]'] roi=[1210, 22, 30, 33] | Custom['记录危机行动调令数'] | `~危机行动调令为零` / `CrisisMissionTicketsFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `~危机行动调令为零` | Custom['危机行动调令为零'] | —(仅路由) | `CrisisMissionTicketsSkipped` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `CrisisMissionTicketsSkipped` | DirectHit | —(仅路由) | `_HomeButton` / `~Homepage` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `_HomeButton` | 模板[Utils/HomeButton.png] roi=[245, 0, 148, 143] | Click | （结束） |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `CrisisMissionTicketsFromLevel` | OCR['快速完成'] roi=[804, 591, 273, 129] | Click | `CrisisMissonTicketsSweepStrategy` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `CrisisMissonTicketsSweepStrategy` | 模板[BCR/AtSweep.png] roi=[148, 176, 308, 292] | —(仅路由) | `设置危机行动战斗次数` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `设置危机行动战斗次数` | DirectHit | Custom['设置危机行动战斗次数'] | `点击出发` / `CrisisMissionTicketsSkipped` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `点击出发` | OCR['出发'] roi=[740, 480, 400, 165] | Click | `~等待快速完成结果` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~等待快速完成结果` | OCR['快速完成结果', '完成次数', '认知度'] roi=[0, 0, 1280, 720] | —(仅路由) | `点击确定` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `点击确定` | OCR['确定', '确认退出'] roi=[940, 600, 340, 120] | Click | `退出关卡详情页` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;11 | `退出关卡详情页` | 模板[当期活动/主界面图标.png] roi=[11, 2, 413, 84] thr=0.85 | Click | `返回主界面` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;12 | `返回主界面` | 模板[当期活动/主界面图标.png] roi=[11, 2, 413, 84] thr=0.85 | Click | （结束） |
| · | `CrisisMissionTicketsSkipped` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `CrisisMissionTicketsSkipped` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `CrisisMissionTicketsSkipped` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_ConfirmSweepResult`, `[JumpBack]_LevelUp`, `[JumpBack]CrisisMissionTicketsSelectLevel`, `[JumpBack]_NavigateCrisisMission`, `[JumpBack]_NavigateBCR`


## `#TheRoom`（事务所（解读仪式））

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `TheRoom` | — | —(仅路由) | `Ritual` |
| &nbsp;&nbsp;1 | `Ritual` | — | —(仅路由) | `RitualCompleted` / `RitualCompleted_NoKey2Archive` / `RitualCompleted_NoKey2Agent` / `RitualNoAmulet` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `RitualCompleted` | 模板[TheRoom/RitualCompleted.png] roi=[620, 420, 377, 179] | —(仅路由) | `SellAmulet` / `RitualDone` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `SellAmulet` | — | —(仅路由) | `AmuletSoldOut` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `AmuletSoldOut` | OCR['^0/'] roi=[721, 0, 180, 136] | —(仅路由) | `_NavigateTheRoom` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `_NavigateTheRoom` | 模板[TheRoom/Ritual.png] roi=[1115, 566, 159, 154] thr=0.8 | —(仅路由) | `_EnsureTheRoom` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `_EnsureTheRoom` | 模板[TheRoom/Ritual.png] roi=[1115, 566, 159, 154] | —(仅路由) | `_ServerMaintenance` / `_ConfrimReconnect` / `_CancelExitTheRoom` / `_CloseMeditationLog` / `~TheRoom` / `_NavigateTheRoom` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `_ServerMaintenance` | OCR['维护'] roi=[485, 227, 311, 133] | —(仅路由) | `_ConfirmServerMaintenance` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `_ConfirmServerMaintenance` | 模板[Utils/ConfirmMiddle.png] roi=[558, 1, 164, 719] | Click | `_LaunchGame` |
| · | `_LaunchGame` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `_ConfrimReconnect` | OCR['回来', '继续游玩'] roi=[437, 234, 404, 135] | —(仅路由) | `_ConfirmMiddle` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `_ConfirmMiddle` | 模板[Utils/ConfirmMiddle.png] roi=[558, 1, 164, 719] | Click | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `_CancelExitTheRoom` | OCR['离开'] roi=[502, 223, 267, 142] | —(仅路由) | `_Cancel` |
| · | `_Cancel` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `_CloseMeditationLog` | OCR['冥', '想'] roi=[511, 0, 257, 150] | —(仅路由) | `_Escape` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `_Escape` | — | Click@[318, 36, 1, 1] | `~ConfirmGeneral` / `~ConfirmSweepResult` / `~CancelGeneral` / `~Cancel1` / `~Cancel2` / `~Cancel3` / `~CloseWindowsGeneral` / `~CloseWindow1` / `~CloseWindow2` / `~ConfirmMiddle` / `~SkipButton` / `~LevelUp` / `~HomeButton` / `~BackButton` / `~Login` / `~EnterGame` / `~StartUpLoading` / `~Loading` / `~Homepage` / `~TheRoom` / `_Escape1` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~ConfirmGeneral` | 模板[Utils/ConfirmGeneral.png] roi=[644, 320, 158, 152] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~ConfirmSweepResult` | OCR['确定'] roi=[1014, 611, 162, 109] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~CancelGeneral` | 模板[Utils/CancelGeneral.png] roi=[481, 318, 155, 153] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~Cancel1` | OCR['取消'] roi=[469, 412, 174, 142] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~Cancel2` | OCR['取消'] roi=[716, 586, 175, 134] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~Cancel3` | OCR['取消'] roi=[465, 590, 150, 130] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~CloseWindowsGeneral` | 模板[Utils/CloseWindows.png] roi=[1081, 29, 142, 143] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~CloseWindow1` | 模板[Utils/CloseWindow1.png] roi=[1102, 143, 130, 135] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~CloseWindow2` | 模板[Utils/CloseWindow2.png] roi=[1163, 25, 117, 148] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~ConfirmMiddle` | 模板[Utils/ConfirmMiddle.png] roi=[558, 1, 164, 719] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~SkipButton` | 模板[Utils/SkipButton.png] roi=[1026, 21, 185, 130] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~LevelUp` | OCR['行动力恢复'] roi=[827, 207, 207, 133] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~HomeButton` | 模板[Utils/HomeButton.png] roi=[245, 0, 148, 143] thr=0.8 | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~BackButton` | 模板[Utils/BackButton.png] roi=[48, 0, 151, 143] thr=0.8 | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~Login` | 模板[StartUp/Login.png] roi=[495, 431, 291, 129] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~EnterGame` | OCR['点', '击', '开', '始', '游', '戏'] roi=[522, 489, 239, 79] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~StartUpLoading` | OCR加载 roi=[521, 429, 235, 141] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~Loading` | 模板[Utils/Loading.png] roi=[0, 0, 425, 123] | —(仅路由) | （结束） |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~TheRoom` | 模板[TheRoom/Ritual.png] roi=[1115, 566, 159, 154] thr=0.8 | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `_Escape1` | — | Click@[318, 36, 1, 1] | `~ConfirmGeneral` / `~ConfirmSweepResult` / `~CancelGeneral` / `~Cancel1` / `~Cancel2` / `~Cancel3` / `~CloseWindowsGeneral` / `~CloseWindow1` / `~CloseWindow2` / `~ConfirmMiddle` / `~SkipButton` / `~LevelUp` / `~HomeButton` / `~BackButton` / `~Login` / `~EnterGame` / `~StartUpLoading` / `~Loading` / `~Homepage` / `~TheRoom` / `_Escape2` |
| · | `~ConfirmGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmSweepResult` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CancelGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel3` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindowsGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmMiddle` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~SkipButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~LevelUp` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~HomeButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~BackButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Login` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~EnterGame` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~StartUpLoading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Loading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~TheRoom` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `_Escape2` | — | Click@[318, 36, 1, 1] | `~ConfirmGeneral` / `~ConfirmSweepResult` / `~CancelGeneral` / `~Cancel1` / `~Cancel2` / `~Cancel3` / `~CloseWindowsGeneral` / `~CloseWindow1` / `~CloseWindow2` / `~ConfirmMiddle` / `~SkipButton` / `~LevelUp` / `~HomeButton` / `~BackButton` / `~Login` / `~EnterGame` / `~StartUpLoading` / `~Loading` / `~Homepage` / `~TheRoom` / `_Escape3` |
| · | `~ConfirmGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmSweepResult` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CancelGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel3` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindowsGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmMiddle` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~SkipButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~LevelUp` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~HomeButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~BackButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Login` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~EnterGame` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~StartUpLoading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Loading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~TheRoom` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;11 | `_Escape3` | — | Click@[318, 36, 1, 1] | `~ConfirmGeneral` / `~ConfirmSweepResult` / `~CancelGeneral` / `~Cancel1` / `~Cancel2` / `~Cancel3` / `~CloseWindowsGeneral` / `~CloseWindow1` / `~CloseWindow2` / `~ConfirmMiddle` / `~SkipButton` / `~LevelUp` / `~HomeButton` / `~BackButton` / `~Login` / `~EnterGame` / `~StartUpLoading` / `~Loading` / `~Homepage` / `~TheRoom` / `_Escape4` |
| · | `~ConfirmGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmSweepResult` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CancelGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel3` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindowsGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmMiddle` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~SkipButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~LevelUp` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~HomeButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~BackButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Login` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~EnterGame` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~StartUpLoading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Loading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~TheRoom` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;12 | `_Escape4` | — | Click@[318, 36, 1, 1] | `~ConfirmGeneral` / `~ConfirmSweepResult` / `~CancelGeneral` / `~Cancel1` / `~Cancel2` / `~Cancel3` / `~CloseWindowsGeneral` / `~CloseWindow1` / `~CloseWindow2` / `~ConfirmMiddle` / `~SkipButton` / `~LevelUp` / `~HomeButton` / `~BackButton` / `~Login` / `~EnterGame` / `~StartUpLoading` / `~Loading` / `~Homepage` / `~TheRoom` / `_Escape5` |
| · | `~ConfirmGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmSweepResult` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CancelGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel3` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindowsGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmMiddle` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~SkipButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~LevelUp` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~HomeButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~BackButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Login` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~EnterGame` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~StartUpLoading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Loading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~TheRoom` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `_Escape5` | — | Click@[318, 36, 1, 1] | `~ConfirmGeneral` / `~ConfirmSweepResult` / `~CancelGeneral` / `~Cancel1` / `~Cancel2` / `~Cancel3` / `~CloseWindowsGeneral` / `~CloseWindow1` / `~CloseWindow2` / `~ConfirmMiddle` / `~SkipButton` / `~LevelUp` / `~HomeButton` / `~BackButton` / `~Login` / `~EnterGame` / `~StartUpLoading` / `~Loading` / `~Homepage` / `~TheRoom` / `_Escape6` |
| · | `~ConfirmGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmSweepResult` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CancelGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel3` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindowsGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmMiddle` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~SkipButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~LevelUp` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~HomeButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~BackButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Login` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~EnterGame` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~StartUpLoading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Loading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~TheRoom` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;14 | `_Escape6` | — | Click@[318, 36, 1, 1] | `~ConfirmGeneral` / `~ConfirmSweepResult` / `~CancelGeneral` / `~Cancel1` / `~Cancel2` / `~Cancel3` / `~CloseWindowsGeneral` / `~CloseWindow1` / `~CloseWindow2` / `~ConfirmMiddle` / `~SkipButton` / `~LevelUp` / `~HomeButton` / `~BackButton` / `~Login` / `~EnterGame` / `~StartUpLoading` / `~Loading` / `~Homepage` / `~TheRoom` / `_Escape7` |
| · | `~ConfirmGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmSweepResult` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CancelGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel3` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindowsGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmMiddle` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~SkipButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~LevelUp` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~HomeButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~BackButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Login` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~EnterGame` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~StartUpLoading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Loading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~TheRoom` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;15 | `_Escape7` | — | Click@[318, 36, 1, 1] | `~ConfirmGeneral` / `~ConfirmSweepResult` / `~CancelGeneral` / `~Cancel1` / `~Cancel2` / `~Cancel3` / `~CloseWindowsGeneral` / `~CloseWindow1` / `~CloseWindow2` / `~ConfirmMiddle` / `~SkipButton` / `~LevelUp` / `~HomeButton` / `~BackButton` / `~Login` / `~EnterGame` / `~StartUpLoading` / `~Loading` / `~Homepage` / `~TheRoom` / `_Escape8` |
| · | `~ConfirmGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmSweepResult` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CancelGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel3` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindowsGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmMiddle` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~SkipButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~LevelUp` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~HomeButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~BackButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Login` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~EnterGame` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~StartUpLoading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Loading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~TheRoom` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;16 | `_Escape8` | — | Click@[318, 36, 1, 1] | `~ConfirmGeneral` / `~ConfirmSweepResult` / `~CancelGeneral` / `~Cancel1` / `~Cancel2` / `~Cancel3` / `~CloseWindowsGeneral` / `~CloseWindow1` / `~CloseWindow2` / `~ConfirmMiddle` / `~SkipButton` / `~LevelUp` / `~HomeButton` / `~BackButton` / `~Login` / `~EnterGame` / `~StartUpLoading` / `~Loading` / `~Homepage` / `~TheRoom` / `_Escape9` |
| · | `~ConfirmGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmSweepResult` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CancelGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel3` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindowsGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmMiddle` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~SkipButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~LevelUp` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~HomeButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~BackButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Login` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~EnterGame` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~StartUpLoading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Loading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~TheRoom` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;17 | `_Escape9` | — | StopApp | `~ConfirmGeneral` / `~ConfirmSweepResult` / `~CancelGeneral` / `~Cancel1` / `~Cancel2` / `~Cancel3` / `~CloseWindowsGeneral` / `~CloseWindow1` / `~CloseWindow2` / `~ConfirmMiddle` / `~SkipButton` / `~LevelUp` / `~HomeButton` / `~BackButton` / `~Login` / `~EnterGame` / `~StartUpLoading` / `~Loading` / `~Homepage` / `~TheRoom` / `_Escape_Wait` |
| · | `~ConfirmGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmSweepResult` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CancelGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel3` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindowsGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmMiddle` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~SkipButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~LevelUp` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~HomeButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~BackButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Login` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~EnterGame` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~StartUpLoading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Loading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~TheRoom` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;18 | `_Escape_Wait` | — | StartApp | `~ConfirmGeneral` / `~ConfirmSweepResult` / `~CancelGeneral` / `~Cancel1` / `~Cancel2` / `~Cancel3` / `~CloseWindowsGeneral` / `~CloseWindow1` / `~CloseWindow2` / `~ConfirmMiddle` / `~SkipButton` / `~LevelUp` / `~HomeButton` / `~BackButton` / `~Login` / `~EnterGame` / `~StartUpLoading` / `~Loading` / `~Homepage` / `~TheRoom` |
| · | `~ConfirmGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmSweepResult` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CancelGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Cancel3` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindowsGeneral` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~CloseWindow2` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~ConfirmMiddle` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~SkipButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~LevelUp` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~HomeButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~BackButton` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Login` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~EnterGame` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~StartUpLoading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Loading` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~TheRoom` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~TheRoom` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_NavigateTheRoom` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `RitualDone` | DirectHit | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `RitualCompleted_NoKey2Archive` | OCR['追加档案残片'] roi=[879, 584, 247, 135] | —(仅路由) | `SellAmulet` / `RitualDone` |
| · | `SellAmulet` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `RitualDone` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `RitualCompleted_NoKey2Agent` | OCR['加速'] roi=[125, 500, 182, 126] | —(仅路由) | `SellAmulet` / `RitualDone` |
| · | `SellAmulet` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `RitualDone` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `RitualNoAmulet` | OCR['不足'] roi=[123, 500, 185, 127] | —(仅路由) | `SellAmulet` / `RitualDone` |
| · | `SellAmulet` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `RitualDone` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_CancelExitTheRoom`, `[JumpBack]_CancelKey2ArchivePieces`, `[JumpBack]_CancelKey2Agent`, `[JumpBack]_CloseSellAmulet`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]_CloseMeditationLog`, `[JumpBack]_CloseRitualResult`, `[JumpBack]_ExitTheRoomStorage`, `[JumpBack]_ExitRitual`, `[JumpBack]_ExitRitualAgentSelect`, `[JumpBack]_Loading`, `[JumpBack]_TheRoomFromHome`, `[JumpBack]_NavigateHomepage`, `[JumpBack]NextAmulet`, `[JumpBack]_NavigateTheRoomStorage`, `[JumpBack]Key2Agent`, `[JumpBack]RitualUseAllKeys`, `[JumpBack]Key2ArchivePieces`, `[JumpBack]RitualRewardSelect`, `[JumpBack]NextRitual`, `[JumpBack]_NavigateRitual`


## `#UrbanPatrol`（市区巡逻）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `UrbanPatrol` | — | —(仅路由) | `DailyCollabPtsCollected` |
| &nbsp;&nbsp;1 | `DailyCollabPtsCollected` | OCR已 roi=[1052, 516, 166, 124] | —(仅路由) | `_False` |
| · | `_False` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]SelectAllFriends`, `[JumpBack]_NavigateMutualAid`, `[JumpBack]CollectDailyCollabPts`, `[JumpBack]_NavigateUrbanPatrol`


## `#CollectRewards`（领取任务奖励）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `CollectRewards` | — | —(仅路由) | `DailyReward` |
| &nbsp;&nbsp;1 | `DailyReward` | — | —(仅路由) | `CollectDailyReward` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `CollectDailyReward` | 模板[Mission/AtDailyMission.png] roi=[677, 0, 214, 135] | Click@[1151, 669, 1, 1] | `CollectWeeklyReward` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `CollectWeeklyReward` | 模板[Mission/AtWeeklyMission.png] roi=[867, 0, 209, 131] | Click@[1151, 669, 1, 1] | （结束） |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateWeeklyMission`, `[JumpBack]_NavigateDailyMission`


## `#CountermeasureProtocol`（领取应对协议）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `CountermeasureProtocol` | — | —(仅路由) | `ProtocolFullLevel` / `CollectProtocolWeekly` |
| &nbsp;&nbsp;1 | `ProtocolFullLevel` | OCR['已满级'] roi=[550, 65, 171, 133] | —(仅路由) | `_StopTask` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `_StopTask` | — | StopTask | （结束） |
| &nbsp;&nbsp;1 | `CollectProtocolWeekly` | 模板[Protocol/AtProtocolWeekly.png] roi=[556, 135, 186, 134] | Click@[1103, 640, 1, 1] | `CollectProtocolSpecial` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `CollectProtocolSpecial` | 模板[Protocol/AtProtocolSpecial.png] roi=[927, 135, 184, 133] | Click@[1103, 640, 1, 1] | `CollectProtocolReward` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `CollectProtocolReward` | 模板[Protocol/AtProtocolReward.png] roi=[414, 172, 172, 195] | Click@[1103, 640, 1, 1] | （结束） |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateProtocolReward`, `[JumpBack]_NavigateProtocolSpecial`, `[JumpBack]_NavigateProtocolWeekly`


## `#Mailbox`（领取邮件）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `Mailbox` | — | —(仅路由) | `CollectMail` |
| &nbsp;&nbsp;1 | `CollectMail` | 模板[Mailbox/CollectMail.png] roi=[55, 586, 229, 132] | Click | （结束） |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateMailbox`


## `#Supplies`（补给站）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `Supplies` | — | —(仅路由) | `DailyGiftCollected` |
| &nbsp;&nbsp;1 | `DailyGiftCollected` | OCR['明日可领取'] roi=[234, 142, 1045, 496] | —(仅路由) | `EventSupplies` / `SilverMedalRedeemRecord` / `SilverMedalRedeemOffer` / `SilverMedalRedeemAcc` / `VioletMedalRedeemRecord` / `_Done` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `EventSupplies` | OCR['活动货柜'] roi=[36, 348, 201, 131] | —(仅路由) | `FindEventGift` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `FindEventGift` | OCR['当期热卖', '活动货品'] roi=[220, 40, 188, 125] | —(仅路由) | `NoEventGift` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `NoEventGift` | OCR['^可领取'] roi=[234, 142, 1045, 496] | —(仅路由) | `SilverMedalRedeemRecord` / `SilverMedalRedeemOffer` / `SilverMedalRedeemAcc` / `VioletMedalRedeemRecord` / `_Done` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `SilverMedalRedeemRecord` | — | —(仅路由) | `SilverMedalRedeemRecordOutOfMedal` / `SilverMedalRedeemRecordComplete` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `SilverMedalRedeemRecordOutOfMedal` | 模板[Utils/Tips.png] roi=[868, 95, 142, 300] | —(仅路由) | `SilverMedalRedeemOffer` / `SilverMedalRedeemAcc` / `VioletMedalRedeemRecord` / `_Done` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `SilverMedalRedeemOffer` | — | —(仅路由) | `SilverMedalRedeemOfferOutOfMedal` / `SilverMedalRedeemOfferComplete` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `SilverMedalRedeemOfferOutOfMedal` | 模板[Utils/Tips.png] roi=[868, 95, 142, 300] | —(仅路由) | `SilverMedalRedeemAcc` / `VioletMedalRedeemRecord` / `_Done` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `SilverMedalRedeemAcc` | — | —(仅路由) | `SilverMedalRedeemAccOutOfMedal` / `SilverMedalRedeemAccComplete` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `SilverMedalRedeemAccOutOfMedal` | 模板[Utils/Tips.png] roi=[868, 95, 142, 300] | —(仅路由) | `VioletMedalRedeemRecord` / `_Done` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;11 | `VioletMedalRedeemRecord` | — | —(仅路由) | `VioletMedalRedeemRecordAtVioletMedal` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;12 | `VioletMedalRedeemRecordAtVioletMedal` | 模板[Supplies/AtVioletMedal.png] roi=[697, 28, 269, 148] | —(仅路由) | `VioletMedalRedeemRecordOutOfMedal` / `VioletMedalRedeemRecordComplete` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `VioletMedalRedeemRecordOutOfMedal` | 模板[Utils/Tips.png] roi=[868, 95, 142, 300] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `VioletMedalRedeemRecordComplete` | OCR['剩余购买次数0'] roi=[876, 151, 230, 125] | Click@[652, 512, 1, 1] | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;11 | `_Done` | DirectHit | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `SilverMedalRedeemAccComplete` | OCR['剩余购买次数0'] roi=[876, 151, 230, 125] | Click@[652, 512, 1, 1] | `VioletMedalRedeemRecord` / `_Done` |
| · | `VioletMedalRedeemRecord` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_Done` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `VioletMedalRedeemRecord` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_Done` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `SilverMedalRedeemOfferComplete` | OCR['剩余购买次数0'] roi=[876, 151, 230, 125] | Click@[652, 512, 1, 1] | `SilverMedalRedeemAcc` / `VioletMedalRedeemRecord` / `_Done` |
| · | `SilverMedalRedeemAcc` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `VioletMedalRedeemRecord` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_Done` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SilverMedalRedeemAcc` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `VioletMedalRedeemRecord` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_Done` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `SilverMedalRedeemRecordComplete` | OCR['剩余购买次数0'] roi=[876, 151, 230, 125] | Click@[652, 512, 1, 1] | `SilverMedalRedeemOffer` / `SilverMedalRedeemAcc` / `VioletMedalRedeemRecord` / `_Done` |
| · | `SilverMedalRedeemOffer` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SilverMedalRedeemAcc` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `VioletMedalRedeemRecord` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_Done` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SilverMedalRedeemOffer` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SilverMedalRedeemAcc` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `VioletMedalRedeemRecord` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_Done` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SilverMedalRedeemRecord` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SilverMedalRedeemOffer` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SilverMedalRedeemAcc` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `VioletMedalRedeemRecord` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_Done` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]VioletMedalRedeemRecordMax`, `[JumpBack]VioletMedalRedeemRecordFound`, `[JumpBack]_Cancel4`, `[JumpBack]_VioletMedalTail`, `[JumpBack]_NavigateVioletMedal`, `[JumpBack]SilverMedalRedeemAccMax`, `[JumpBack]SilverMedalRedeemAccFound`, `[JumpBack]_SilverMedalTail`, `[JumpBack]_NavigateSilverMedal`, `[JumpBack]SilverMedalRedeemOfferMax`, `[JumpBack]SilverMedalRedeemOfferFound`, `[JumpBack]SilverMedalRedeemRecordMax`, `[JumpBack]SilverMedalRedeemRecordFound`, `[JumpBack]CollectEventGift`, `[JumpBack]_NavigateEventSupplies`, `[JumpBack]DailyGift`, `[JumpBack]_NavigateReinforcementSupplies`


## `#ExternalRecruit`（外部招募）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `ExternalRecruit` | — | —(仅路由) | `ManageExternalRecruit` |
| &nbsp;&nbsp;1 | `ManageExternalRecruit` | OCR['外部招募'] roi=[325, 322, 290, 153] | —(仅路由) | `ExternalRecruitOutofOffer` / `ExternalRecruitQueueFull` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `ExternalRecruitOutofOffer` | OCR道具不足 roi=[929, 112, 186, 125] | —(仅路由) | `_NavigateHomepage` / `~Homepage` |
| · | `_NavigateHomepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `ExternalRecruitQueueFull` | OCR['任务已满'] roi=[906, 475, 202, 137] | —(仅路由) | `_NavigateHomepage` / `~Homepage` |
| · | `_NavigateHomepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]_RecruitResult`, `[JumpBack]ExternalRecruitMax`, `[JumpBack]ExternalRecruitProceed`, `[JumpBack]ExternalRecruitAcc`, `[JumpBack]_NavigateExternalRecruit`


## `#ShutDown`（退出游戏）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `ShutDown` | — | —(仅路由) | `_ExitGame` |
| &nbsp;&nbsp;1 | `_ExitGame` | — | StopApp | （结束） |



## `#DailyStaminaBonus`（活动-每日行动补给）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `DailyStaminaBonus` | — | —(仅路由) | `CollectStaminaBonusNoon` |
| &nbsp;&nbsp;1 | `CollectStaminaBonusNoon` | OCR['每日行动'] roi=[419, 24, 446, 170] | Click@[431, 584, 1, 1] | `CollectStaminaBonusEvening` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `CollectStaminaBonusEvening` | OCR['每日行动'] roi=[419, 24, 446, 170] | Click@[708, 582, 1, 1] | （结束） |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateStaminaBonus`


## `#JointBlockade`（联线封锁）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `JointBlockade` | — | —(仅路由) | `JointBlockadeCompleteFromSystem` / `JointBlockadeFromSystem` |
| &nbsp;&nbsp;1 | `JointBlockadeCompleteFromSystem` | OCR['108/108'] roi=[0, 483, 168, 128] | —(仅路由) | （结束） |
| &nbsp;&nbsp;1 | `JointBlockadeFromSystem` | OCR['联线封锁'] roi=[0, 458, 189, 128] | Click | `~JointBlockadeNA` / `JointBlockadeCompleteFromLevel` / `JointBlockadeTicketsCompleteFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `~JointBlockadeNA` | 模板[BCR/JointBlockadeNA.png] roi=[792, 576, 133, 136] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `JointBlockadeCompleteFromLevel` | OCR['108/108'] roi=[106, 554, 218, 135] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `JointBlockadeTicketsCompleteFromLevel` | OCR['^0'] roi=[1161, 0, 119, 92] | —(仅路由) | （结束） |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]ConfirmDiscardJointBlockadeUnfinishedGame`, `[JumpBack]_ConfirmJointBlockadeResult`, `[JumpBack]_SweepConfirm`, `[JumpBack]_SweepFromLevel`, `[JumpBack]JointBlockadeUnfinishedGame`, `[JumpBack]_NavigateJointBlockade`, `[JumpBack]_NavigateSystem`


## `#ShortTermCheckIn`（活动-短期支援补贴）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `ShortTermCheckIn` | — | —(仅路由) | `CollectShortTermCheckIn` / `~ShortTermCheckIn` |
| &nbsp;&nbsp;1 | `CollectShortTermCheckIn` | OCR['点击领取'] roi=[1035, 117, 179, 547] | Click | （结束） |
| &nbsp;&nbsp;1 | `~ShortTermCheckIn` | OCR['短期支援'] roi=[254, 377, 396, 190] | —(仅路由) | （结束） |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateShortTermCheckIn`


## `#当期活动`（当期活动）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `当期活动` | — | —(仅路由) | `进入活动页` |
| &nbsp;&nbsp;1 | `进入活动页` | OCR['剩余'] roi=[1045, 212, 235, 194] | Click | `选择危险地带` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `选择危险地带` | 模板[当期活动/危险地带.png] roi=[0, 0, 1280, 720] thr=0.9 | Click | `选择危险地带关卡` / `_危险地带平移1` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `选择危险地带关卡` | 模板[当期活动/危险地带_CS110.png] roi=[0, 0, 1280, 720] thr=0.87 | Click | `点击快速完成` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `点击快速完成` | OCR['快速完成'] roi=[700, 600, 400, 120] | Click | `行动力判定` / `行动次数确定` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `行动力判定` | OCR['时'] roi=[454, 189, 608, 165] | Click@offset[0, 70, 0, 0] | `行动次数确定` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `行动次数确定` | OCR['快速完成次数'] roi=[640, 365, 240, 40] | Click@[955, 457, 1, 1] | `点击出发` |
| · | `点击出发` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `行动次数确定` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `_危险地带平移1` | 模板[当期活动/危险地带_地图标题.png] roi=[0, 0, 640, 240] thr=0.85 | Swipe | `选择危险地带关卡` / `_危险地带平移2` |
| · | `选择危险地带关卡` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `_危险地带平移2` | 模板[当期活动/危险地带_地图标题.png] roi=[0, 0, 640, 240] thr=0.85 | Swipe | `选择危险地带关卡` |
| · | `选择危险地带关卡` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateHomepage`


## `#往期活动`（往期活动）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `往期活动` | — | —(仅路由) | `进入作战` / `点击往期活动` |
| &nbsp;&nbsp;1 | `进入作战` | OCR['作战'] roi=[850, 300, 360, 200] | Click | `点击往期活动` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `点击往期活动` | 模板[往期活动/往期活动.png] roi=[421, 0, 859, 154] thr=0.8 | Click | `~已切换到往期活动` / `点击往期活动_重试2` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `~已切换到往期活动` | 模板[往期活动/往期活动标志.png] roi=[47, 65, 484, 89] thr=0.85 | —(仅路由) | `进入往期活动内部流程` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `进入往期活动内部流程` | DirectHit | —(仅路由) | `~识别往日行动调令` / `选择往期活动` / `往左滑动` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `~识别往日行动调令` | OCR['[0-6]'] roi=[351, 92, 173, 48] | —(仅路由) | `记录往日行动调令数` / `选择往期活动` / `往左滑动` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `记录往日行动调令数` | OCR[] roi=[351, 92, 173, 48] | Custom['记录往日行动调令数'] | `~调令为零` / `选择往期活动` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `~调令为零` | Custom['调令为零'] | —(仅路由) | `退出往期活动失败` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `退出往期活动失败` | 模板[当期活动/主界面图标.png] roi=[11, 2, 413, 84] thr=0.85 | Click | `_NavigateHomepage` / `~Homepage` |
| · | `_NavigateHomepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `选择往期活动` | 模板[往期活动/在月光之下.png] roi=[0, 147, 1280, 442] thr=0.8 | Click | `进入该往期活动事件` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `进入该往期活动事件` | DirectHit | —(仅路由) | `进入该往期活动事件_未适配` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `进入该往期活动事件_未适配` | DirectHit | —(仅路由) | （结束） |
| · | `选择往期活动` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `往左滑动` | — | Swipe | `选择往期活动_重试2` / `往左滑动2` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `选择往期活动_重试2` | 模板[往期活动/在月光之下.png] roi=[0, 147, 1280, 442] thr=0.8 | Click | `进入该往期活动事件` |
| · | `进入该往期活动事件` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `往左滑动2` | — | Swipe | `选择往期活动_重试3` / `往左滑动3` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `选择往期活动_重试3` | 模板[往期活动/在月光之下.png] roi=[0, 147, 1280, 442] thr=0.8 | Click | `进入该往期活动事件` |
| · | `进入该往期活动事件` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `往左滑动3` | — | Swipe | `选择往期活动_重试4` / `退出往期活动失败` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `选择往期活动_重试4` | 模板[往期活动/在月光之下.png] roi=[0, 147, 1280, 442] thr=0.8 | Click | `进入该往期活动事件` |
| · | `进入该往期活动事件` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `退出往期活动失败` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `选择往期活动` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `往左滑动` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `点击往期活动_重试2` | 模板[往期活动/往期活动.png] roi=[421, 0, 859, 154] thr=0.8 | Click | `~已切换到往期活动_重试2` / `点击往期活动_重试3` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `~已切换到往期活动_重试2` | 模板[往期活动/往期活动标志.png] roi=[47, 65, 484, 89] thr=0.85 | —(仅路由) | `进入往期活动内部流程` |
| · | `进入往期活动内部流程` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `点击往期活动_重试3` | 模板[往期活动/往期活动.png] roi=[421, 0, 859, 154] thr=0.8 | Click | `~已切换到往期活动_重试3` / `退出往期活动失败` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `~已切换到往期活动_重试3` | 模板[往期活动/往期活动标志.png] roi=[47, 65, 484, 89] thr=0.85 | —(仅路由) | `进入往期活动内部流程` |
| · | `进入往期活动内部流程` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `退出往期活动失败` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `点击往期活动` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateHomepage`


## `#自动推图`（自动推图）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `自动推图` | — | —(仅路由) | `播报前提` |
| &nbsp;&nbsp;1 | `播报前提` | DirectHit | Custom['播报进度'] | `播报开始` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `播报开始` | DirectHit | Custom['播报进度'] | `巡检关卡` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `巡检关卡` | DirectHit | —(仅路由) | `识别未完成关卡` / `推图完成` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `识别未完成关卡` | 模板[自动推图/未完成关卡.png] roi=[0, 0, 1280, 720] thr=0.8 | Click | `巡检出发` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `巡检出发` | DirectHit | —(仅路由) | `识别出发` / `巡检出发2` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `识别出发` | OCR['出发'] roi=[784, 588, 496, 132] | Click | `等待编队出现` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `等待编队出现` | DirectHit | —(仅路由) | `巡检编队` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `巡检编队` | DirectHit | —(仅路由) | `编队调整检测` / `点击跳过介绍` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `编队调整检测` | 模板[自动推图/编队调整_文字.png] roi=[1000, 439, 280, 132] thr=0.7 | Click | `~进入编队选择` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `~进入编队选择` | 模板[自动推图/编队选择关闭.png] roi=[1085, 39, 95, 98] thr=0.85 | —(仅路由) | `选择出战队伍` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;11 | `选择出战队伍` | 模板[自动推图/战斗编队1.png] roi=[166, 350, 146, 80] thr=0.85 | Click@offset[799, 0, 0, 0] | `点击关闭编队` / `选择出战队伍_重试` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;12 | `点击关闭编队` | 模板[自动推图/编队选择关闭.png] roi=[1085, 39, 95, 98] thr=0.85 | Click | `点击开始作战` / `点击关闭编队_重试` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `点击开始作战` | 模板[自动推图/开始作战.png] roi=[1036, 593, 197, 111] thr=0.85 | Click | `~战斗界面已加载` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;14 | `~战斗界面已加载` | 模板[自动推图/auto.png] roi=[790, 10, 140, 80] thr=0.7 | —(仅路由) | `点击自动战斗` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;15 | `点击自动战斗` | 模板[自动推图/auto.png] roi=[790, 10, 140, 80] thr=0.7 | Click | `点击自动确认` / `点击自动确认_重试` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;16 | `点击自动确认` | 模板[自动推图/自动战斗确认.png] roi=[425, 220, 410, 231] thr=0.8 | Click | `自动战斗已开启` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;17 | `自动战斗已开启` | DirectHit | —(仅路由) | `等待战斗结束` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;18 | `等待战斗结束` | DirectHit | —(仅路由) | `点击未满星结算` / `~战斗胜利_标题` / `~战斗胜利_战利品` / `~战斗失败_标题` / `~战斗失败_条件` / `~战斗失败_退出` / `等待战斗结束_间隔` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;19 | `点击未满星结算` | 模板[自动推图/战斗未满星结算.png] roi=[804, 406, 451, 234] thr=0.8 | Click | `播报未满星` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;20 | `播报未满星` | DirectHit | Custom['播报进度'] | `连点退出并重扫` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;21 | `连点退出并重扫` | DirectHit | Custom['连点退出'] | `播报开始` |
| · | `播报开始` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;19 | `~战斗胜利_标题` | OCR['战斗胜利'] roi=[873, 114, 401, 280] | —(仅路由) | `播报胜利` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;20 | `播报胜利` | DirectHit | Custom['播报进度'] | `连点退出并重扫` |
| · | `连点退出并重扫` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;19 | `~战斗胜利_战利品` | 模板[自动推图/战斗胜利战利品.png] roi=[1086, 409, 166, 71] thr=0.8 | —(仅路由) | `播报胜利` |
| · | `播报胜利` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;19 | `~战斗失败_标题` | OCR['战斗失败'] roi=[855, 110, 425, 160] | —(仅路由) | `处理战斗失败` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;20 | `处理战斗失败` | DirectHit | Custom['播报进度'] | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;19 | `~战斗失败_条件` | 模板[自动推图/战斗失败条件.png] roi=[1088, 203, 122, 153] thr=0.8 | —(仅路由) | `处理战斗失败` |
| · | `处理战斗失败` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;19 | `~战斗失败_退出` | 模板[自动推图/战斗失败退出.png] roi=[957, 598, 257, 64] thr=0.8 | —(仅路由) | `处理战斗失败` |
| · | `处理战斗失败` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;19 | `等待战斗结束_间隔` | DirectHit | —(仅路由) | `等待战斗结束` |
| · | `等待战斗结束` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;16 | `点击自动确认_重试` | 模板[自动推图/自动战斗确认.png] roi=[425, 220, 410, 231] thr=0.8 | Click | `自动战斗已开启` |
| · | `自动战斗已开启` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `点击关闭编队_重试` | 模板[自动推图/编队选择关闭.png] roi=[1085, 39, 95, 98] thr=0.85 | Click | `点击开始作战` |
| · | `点击开始作战` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;12 | `选择出战队伍_重试` | 模板[自动推图/战斗编队1.png] roi=[166, 350, 146, 80] thr=0.85 | Click@offset[799, 0, 0, 0] | `点击关闭编队` / `选择出战队伍_失败停止` |
| · | `点击关闭编队` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `选择出战队伍_失败停止` | DirectHit | —(仅路由) | `点击关闭编队` |
| · | `点击关闭编队` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `点击跳过介绍` | DirectHit | Click@[1218, 273, 1, 1] | `巡检编队` |
| · | `巡检编队` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `巡检出发2` | DirectHit | —(仅路由) | `识别出发` / `巡检出发3` |
| · | `识别出发` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `巡检出发3` | DirectHit | —(仅路由) | `识别出发` / `巡检出发4` |
| · | `识别出发` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `巡检出发4` | DirectHit | —(仅路由) | `识别出发` / `识别出发失败处理` |
| · | `识别出发` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `识别出发失败处理` | DirectHit | Custom['存失败截图'] | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `推图完成` | DirectHit | Custom['播报进度'] | （结束） |



## `#SeaOfCognition`（认知海域（开发中））

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `SeaOfCognition` | — | —(仅路由) | `SoCResume` |
| &nbsp;&nbsp;1 | `SoCResume` | DirectHit | —(仅路由) | `SoCClaim` / `SoCContinue` / `SoCStartBattle` / `SoCInBattleBuff` / `SoCInBattleBuffOCR` / `SoCInspirationNode` / `SoCInspirationNodeOCR` / `SoCState_GB1` / `SoCState_GB0` / `SoCContinueDive` / `SoCDeepDive` / `SoCDeepDiveFree` / `SoCFallbackStart` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `SoCClaim` | OCR['[领領]取', '[确確][认認]'] roi=[0, 0, 1280, 720] | Click | `SoCAtBCR` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `SoCAtBCR` | 模板[SeaOfCognition/认知海域图标.png] roi=[0, 500, 1280, 220] thr=0.8 | Click | `SoCSelectLayer` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `SoCSelectLayer` | OCR['[梦夢][渊淵][层層]'] roi=[0, 0, 1280, 720] | Click | `SoCStartDive` / `SoCContinueDive` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `SoCStartDive` | OCR['开始下[潜潛]'] roi=[820, 545, 460, 175] | Click | `SoCResume` / `SoCDeepDive` / `SoCDeepDiveFree` / `SoCDeepDiveFallback` |
| · | `SoCResume` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `SoCDeepDive` | OCR['深[潜潛]指引'] roi=[0, 0, 1280, 720] | Click | `SoCTeamEnter` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `SoCTeamEnter` | 模板[SeaOfCognition/进入海域.png] roi=[0, 0, 1280, 720] thr=0.8 | Click | `SoCInspirationNode` / `SoCInspirationNodeOCR` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `SoCInspirationNode` | 模板[SeaOfCognition/认知海域灵感节点.png] roi=[192, 159, 358, 556] thr=0.8 | —(仅路由) | `SoCInspirationClick` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `SoCInspirationClick` | OCR['[灵靈]感[节節][点點]'] roi=[0, 0, 1280, 720] | Click | `SoCGBLoop` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `SoCGBLoop` | — | —(仅路由) | `SoCGBPickAvailable` / `SoCGBSwipe` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;11 | `SoCGBPickAvailable` | DirectHit | Custom['None'] | `SoCGBContinue` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;12 | `SoCGBContinue` | 模板[SeaOfCognition/BuffContinue.png] roi=[450, 600, 380, 100] thr=0.8 | Click | `SoCInBattleBuff` / `SoCInBattleBuffOCR` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `SoCInBattleBuff` | 模板[SeaOfCognition/局内buff选择.png] roi=None thr=0.8 | Click@[472, 344, 1, 1] | `SoCInBattleBuff2nd` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;14 | `SoCInBattleBuff2nd` | DirectHit | Click@[472, 344, 1, 1] | `SoCInBattleBuffConfirm` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;15 | `SoCInBattleBuffConfirm` | 模板[SeaOfCognition/QiFa.png] roi=None thr=0.8 | Click | `SoCStartBattle` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;16 | `SoCStartBattle` | 模板[SeaOfCognition/认知海域开始作战.png] roi=None thr=0.8 | Click | `SoCAutoBattle` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;17 | `SoCAutoBattle` | DirectHit | Custom['SoCAwaitBattle'] | `SoCContinue` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;18 | `SoCContinue` | 模板[SeaOfCognition/战斗完成继续.png] roi=[950, 600, 330, 120] thr=0.8 | Click | `SoCAfterContinue` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;19 | `SoCAfterContinue` | DirectHit | —(仅路由) | `SoCState_GB1` / `SoCState_GB0` / `SoCNodeLoop` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;20 | `SoCState_GB1` | OCR['剩余可选灵感'] roi=[400, 560, 500, 110] | —(仅路由) | `SoCGBSwipe` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;21 | `SoCGBSwipe` | DirectHit | Swipe | `SoCGBLoop` |
| · | `SoCGBLoop` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;20 | `SoCState_GB0` | 模板[SeaOfCognition/剩余可选灵感0.png] roi=None thr=0.8 | —(仅路由) | `SoCGBLoop` |
| · | `SoCGBLoop` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;20 | `SoCNodeLoop` | — | —(仅路由) | `SoCInBattleBuff` / `SoCInBattleBuffOCR` / `SoCClaim` |
| · | `SoCInBattleBuff` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;21 | `SoCInBattleBuffOCR` | OCR['请选择一个短暂灵感'] roi=[850, 0, 430, 50] | Click@[472, 344, 1, 1] | `SoCInBattleBuff2nd` |
| · | `SoCInBattleBuff2nd` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCClaim` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInBattleBuffOCR` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCGBSwipe` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `SoCInspirationNodeOCR` | OCR['[灵靈]感[节節][点點]'] roi=[192, 159, 358, 556] | —(仅路由) | `SoCInspirationClick` |
| · | `SoCInspirationClick` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `SoCDeepDiveFree` | OCR['自由探索', '自由', '探索'] roi=[0, 0, 1280, 720] | Click | `SoCTeamEnter` |
| · | `SoCTeamEnter` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `SoCDeepDiveFallback` | DirectHit | Click@[351, 581, 1, 1] | `SoCTeamEnter` |
| · | `SoCTeamEnter` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `SoCContinueDive` | 模板[SeaOfCognition/认知海域继续下潜.png] roi=[820, 545, 460, 175] thr=0.8 | Click | `SoCInspirationNode` / `SoCInspirationNodeOCR` / `SoCState_GB1` / `SoCState_GB0` / `SoCInBattleBuff` / `SoCInBattleBuffOCR` / `SoCStartBattle` / `SoCClaim` / `SoCContinue` / `SoCInspirationFallback` |
| · | `SoCInspirationNode` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInspirationNodeOCR` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCState_GB1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCState_GB0` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInBattleBuff` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInBattleBuffOCR` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCStartBattle` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCClaim` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCContinue` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `SoCInspirationFallback` | DirectHit | Click@[351, 581, 1, 1] | `SoCInBattleBuff` / `SoCInBattleBuffOCR` |
| · | `SoCInBattleBuff` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInBattleBuffOCR` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCContinue` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCStartBattle` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInBattleBuff` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInBattleBuffOCR` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInspirationNode` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInspirationNodeOCR` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCState_GB1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCState_GB0` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCContinueDive` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCDeepDive` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCDeepDiveFree` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `SoCFallbackStart` | DirectHit | —(仅路由) | `SoCAtBCR` |
| · | `SoCAtBCR` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]_LevelUp`, `[JumpBack]_SeaOfCognitionReward`, `[JumpBack]_SoCGBAbandonConfirm`, `[JumpBack]_SoCNoTicket`, `[JumpBack]_NavigateBCR`, `[JumpBack]_BCRHead`, `[JumpBack]_BCRTail`, `[JumpBack]_NavigateHomepage`, `[JumpBack]_CloseWindows`

---

## 跨任务复用节点（共 7 个，改版回归时需一并验证）

| 节点 | 定义文件 | 复用任务数 | 复用任务 |
|------|---------|-----------|---------|
| `~Homepage` | Shared.json | 5 | 事务所（解读仪式）、危机行动调令、启动游戏、外部招募、往期活动 |
| `_NavigateHomepage` | Shared.json | 3 | 启动游戏、外部招募、往期活动 |
| `_Cancel` | Shared.json | 2 | 事务所（解读仪式）、每周-阈限禁区 |
| `_False` | Shared.json | 2 | 市区巡逻、清体力 |
| `_LaunchGame` | Shared.json | 2 | 事务所（解读仪式）、启动游戏 |
| `~LiminalZoneNA` | Shared.json | 2 | 每周-阈限禁区、清体力 |
| `点击出发` | Shared.json | 2 | 危机行动调令、当期活动 |
