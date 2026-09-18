# MaaEOV 任务流程梳理与 UI 变更重测清单

> 自动生成自 `resource/base/pipeline/` 下 3 个流水线文件（Tasks.json / 推图.json / 认知海域.json）。

> 基准分辨率：1280×720。所有坐标、ROI 均为该基准下的像素值，UI 改版后需逐项复核。

> 共解析到 **19** 个任务入口、**613** 个节点。


## 公共约定（所有任务共用）

- 每个节点的 `next` 列表中，以 `[JumpBack]_XXX` 开头的是**中断/弹窗保底处理**（服务器维护、断线重连、升级弹窗、领奖等），不属正常流程，故下方流程表默认只列**主链路**（`next` 首项）。
- `DirectHit` 节点**必定命中**，多用于「路由/播报/兜底」；`TemplateMatch`/`OCR` 节点按识别结果决定是否执行、再到 `next`。
- **UI 重测重点**：流程表里「识别」列即该步的 UI 依赖——模板图片需重新截图、OCR 文案需逐字核对、坐标需重新定位。任一变更都会导致该节点识别失败、任务卡死或错点。
- 共享导航节点（`_NavigateBCR` / `_BCRHead` / `_BCRTail` / `_NavigateHomepage` / `_ServerMaintenance` / `_ConfrimReconnect` / `_ConfirmMiddle` / `_LevelUp` / `_CloseWindows` / `_SeaOfCognitionReward`）被多数任务复用，单独在文末列出。


---
# 各任务流程


## #StartUp

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#StartUp` | — | —(仅路由) | `_LaunchGame` |
| &nbsp;&nbsp;1 | `_LaunchGame` | — | StartApp | `_NavigateHomepage` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `_NavigateHomepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | `_EnsureHomepage` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `_EnsureHomepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | `~Homepage` / `_NavigateHomepage` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `~Homepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | （结束） |
| · | `_NavigateHomepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_BackButton`, `[JumpBack]_Cancel1`, `[JumpBack]_Cancel2`, `[JumpBack]_Cancel3`, `[JumpBack]_Cancel4`, `[JumpBack]_CancelGeneral`, `[JumpBack]_CloseWindow1`, `[JumpBack]_CloseWindow2`, `[JumpBack]_CloseWindowsGeneral`, `[JumpBack]_ConfirmExitTheRoom`, `[JumpBack]_ConfirmGeneral`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]_ConfirmSweepResult`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_EnterGame`, `[JumpBack]_Escape`, `[JumpBack]_ExitTheRoom`, `[JumpBack]_HomeButton`, `[JumpBack]_LevelUp`, `[JumpBack]_Loading`, `[JumpBack]_Login`, `[JumpBack]_ServerMaintenance`, `[JumpBack]_SkipButton`, `[JumpBack]_StartUpLoading`, `[JumpBack]_UnfinishedGame`, `[JumpBack]_UpdateGame`


## #ShutDown

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#ShutDown` | — | —(仅路由) | `_ExitGame` |
| &nbsp;&nbsp;1 | `_ExitGame` | — | StopApp | （结束） |

## #Farm

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#Farm` | — | —(仅路由) | `Farm` |
| &nbsp;&nbsp;1 | `Farm` | — | —(仅路由) | `SelectLevelFromBCR` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `SelectLevelFromBCR` | OCR['主线故事'] roi=[1080, 607, 200, 113] | —(仅路由) | `~LevelNA` / `~LiminalZoneNA` / `FarmFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `~LevelNA` | OCR['重复行动'] roi=[804, 591, 273, 129] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `~LiminalZoneNA` | 模板[BCR/LiminalZoneNA.png] roi=[859, 585, 140, 135] thr=None | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `FarmFromLevel` | OCR['扫荡', '扫汤', '快速完成'] roi=[804, 591, 273, 129] | —(仅路由) | `_False` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `_False` | — | —(仅路由) | （结束） |

> 该任务挂载的中断保底：`[JumpBack]FarmOutOfStamina`, `[JumpBack]FarmSelectLevel`, `[JumpBack]_ConfirmLiminalZoneOverflow`, `[JumpBack]_ConfirmSweepResult`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_LevelUp`, `[JumpBack]_NavigateBCR`, `[JumpBack]_ServerMaintenance`, `[JumpBack]_SweepFromLevel`, `[JumpBack]_SweepMax`


## #CrisisMissionTickets

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#CrisisMissionTickets` | — | —(仅路由) | `CrisisMissionTickets` |
| &nbsp;&nbsp;1 | `CrisisMissionTickets` | — | —(仅路由) | `CrisisMissionTicketsFromBCR` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `CrisisMissionTicketsFromBCR` | OCR['主线故事'] roi=[1080, 607, 200, 113] | —(仅路由) | `~LevelNA` / `CrisisMissionTicketsFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `~LevelNA` | OCR['重复行动'] roi=[804, 591, 273, 129] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `CrisisMissionTicketsFromLevel` | OCR['快速完成'] roi=[804, 591, 273, 129] | —(仅路由) | `CrisisMissionTicketsCompletedFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `CrisisMissionTicketsCompletedFromLevel` | OCR['^0'] roi=[1161, 0, 119, 92] | —(仅路由) | （结束） |

> 该任务挂载的中断保底：`[JumpBack]CrisisMissionTicketsSelectLevel`, `[JumpBack]CrisisMissonTicketsSweepStrategy`, `[JumpBack]_ConfirmSweepResult`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_LevelUp`, `[JumpBack]_NavigateBCR`, `[JumpBack]_ServerMaintenance`, `[JumpBack]_SweepFromLevel`


## #LiminalZone

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#LiminalZone` | — | —(仅路由) | `LiminalZone` |
| &nbsp;&nbsp;1 | `LiminalZone` | — | —(仅路由) | `LiminalZoneCompletedFromSystem` / `LiminalZoneFromSystem` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `LiminalZoneCompletedFromSystem` | OCR['480/480'] roi=[199, 312, 223, 128] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `LiminalZoneFromSystem` | 模板[SystemPage/Settings.png] roi=[0, 559, 149, 149] thr=None | Click@[337, 362, 1, 1] | `SelectLevelFromLiminalZone` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `SelectLevelFromLiminalZone` | 模板[BCR/AtLiminalZone.png] roi=[45, 81, 147, 144] thr=None | —(仅路由) | `~LiminalZoneNA` / `LiminalZoneFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `~LiminalZoneNA` | 模板[BCR/LiminalZoneNA.png] roi=[859, 585, 140, 135] thr=None | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `LiminalZoneFromLevel` | OCR['扫荡', '扫汤'] roi=[804, 591, 273, 129] | —(仅路由) | `_CancelLiminalZoneOverflow` / `LiminalZoneCompletedFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `_CancelLiminalZoneOverflow` | OCR['进行探索', '回收物'] roi=[222, 225, 834, 136] | —(仅路由) | `_Cancel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `_Cancel` | — | —(仅路由) | `_CancelGeneral` / `_Cancel1` / `_Cancel2` / `_Cancel3` / `_Cancel4` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `LiminalZoneCompletedFromLevel` | OCR['480/480'] roi=[92, 620, 225, 100] | —(仅路由) | （结束） |

> 该任务挂载的中断保底：`[JumpBack]FarmSelectLevel`, `[JumpBack]LiminalZoneOutOfStamina`, `[JumpBack]LiminalZoneSelectLevel`, `[JumpBack]_ConfirmLiminalZoneResult`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_LevelUp`, `[JumpBack]_NavigateLiminalZone`, `[JumpBack]_NavigateSystem`, `[JumpBack]_ServerMaintenance`, `[JumpBack]_SweepFromLevel`, `[JumpBack]_SweepMax`


## #TheRoom

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#TheRoom` | — | —(仅路由) | `Ritual` |
| &nbsp;&nbsp;1 | `Ritual` | — | —(仅路由) | `RitualCompleted` / `RitualCompleted_NoKey2Archive` / `RitualCompleted_NoKey2Agent` / `RitualNoAmulet` |

> 该任务挂载的中断保底：`[JumpBack]Key2Agent`, `[JumpBack]Key2ArchivePieces`, `[JumpBack]NextRitual`, `[JumpBack]RitualRewardSelect`, `[JumpBack]RitualUseAllKeys`, `[JumpBack]_CloseRitualResult`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateRitual`, `[JumpBack]_ServerMaintenance`


## #UrbanPatrol

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#UrbanPatrol` | — | —(仅路由) | `UrbanPatrol` |
| &nbsp;&nbsp;1 | `UrbanPatrol` | — | —(仅路由) | `DailyCollabPtsCollected` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `DailyCollabPtsCollected` | OCR['已'] roi=[1052, 516, 166, 124] | —(仅路由) | `_False` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `_False` | — | —(仅路由) | （结束） |

> 该任务挂载的中断保底：`[JumpBack]CollectDailyCollabPts`, `[JumpBack]SelectAllFriends`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateMutualAid`, `[JumpBack]_NavigateUrbanPatrol`, `[JumpBack]_ServerMaintenance`


## #CollectRewards

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#CollectRewards` | — | —(仅路由) | `DailyReward` |
| &nbsp;&nbsp;1 | `DailyReward` | — | —(仅路由) | `CollectDailyReward` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `CollectDailyReward` | 模板[Mission/AtDailyMission.png] roi=[677, 0, 214, 135] thr=None | Click@[1151, 669, 1, 1] | `CollectWeeklyReward` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `CollectWeeklyReward` | 模板[Mission/AtWeeklyMission.png] roi=[867, 0, 209, 131] thr=None | Click@[1151, 669, 1, 1] | （结束） |

> 该任务挂载的中断保底：`[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateDailyMission`, `[JumpBack]_NavigateWeeklyMission`, `[JumpBack]_ServerMaintenance`


## #CountermeasureProtocol

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#CountermeasureProtocol` | — | —(仅路由) | `CountermeasureProtocol` |
| &nbsp;&nbsp;1 | `CountermeasureProtocol` | — | —(仅路由) | `ProtocolFullLevel` / `CollectProtocolWeekly` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `ProtocolFullLevel` | OCR['已满级'] roi=[550, 65, 171, 133] | —(仅路由) | `_StopTask` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `_StopTask` | — | StopTask | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `CollectProtocolWeekly` | 模板[Protocol/AtProtocolWeekly.png] roi=[556, 135, 186, 134] thr=None | Click@[1103, 640, 1, 1] | `CollectProtocolSpecial` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `CollectProtocolSpecial` | 模板[Protocol/AtProtocolSpecial.png] roi=[927, 135, 184, 133] thr=None | Click@[1103, 640, 1, 1] | `CollectProtocolReward` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `CollectProtocolReward` | 模板[Protocol/AtProtocolReward.png] roi=[414, 172, 172, 195] thr=None | Click@[1103, 640, 1, 1] | （结束） |

> 该任务挂载的中断保底：`[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateProtocolReward`, `[JumpBack]_NavigateProtocolSpecial`, `[JumpBack]_NavigateProtocolWeekly`, `[JumpBack]_ServerMaintenance`


## #Mailbox

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#Mailbox` | — | —(仅路由) | `Mailbox` |
| &nbsp;&nbsp;1 | `Mailbox` | — | —(仅路由) | `CollectMail` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `CollectMail` | 模板[Mailbox/CollectMail.png] roi=[55, 586, 229, 132] thr=None | Click(匹配框中心) | （结束） |

> 该任务挂载的中断保底：`[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateMailbox`, `[JumpBack]_ServerMaintenance`


## #ExternalRecruit

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#ExternalRecruit` | — | —(仅路由) | `ExternalRecruit` |
| &nbsp;&nbsp;1 | `ExternalRecruit` | — | —(仅路由) | `ManageExternalRecruit` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `ManageExternalRecruit` | OCR['外部招募'] roi=[325, 322, 290, 153] | —(仅路由) | `ExternalRecruitOutofOffer` / `ExternalRecruitQueueFull` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `ExternalRecruitOutofOffer` | OCR['道', '具', '不', '足'] roi=[929, 112, 186, 125] | —(仅路由) | `_NavigateHomepage` / `~Homepage` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `_NavigateHomepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | `_EnsureHomepage` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `_EnsureHomepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | `~Homepage` / `_NavigateHomepage` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `~Homepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | （结束） |
| · | `_NavigateHomepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `ExternalRecruitQueueFull` | OCR['任务已满'] roi=[906, 475, 202, 137] | —(仅路由) | `_NavigateHomepage` / `~Homepage` |
| · | `_NavigateHomepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]ExternalRecruitAcc`, `[JumpBack]ExternalRecruitMax`, `[JumpBack]ExternalRecruitProceed`, `[JumpBack]_BackButton`, `[JumpBack]_Cancel1`, `[JumpBack]_Cancel2`, `[JumpBack]_Cancel3`, `[JumpBack]_Cancel4`, `[JumpBack]_CancelGeneral`, `[JumpBack]_CloseWindow1`, `[JumpBack]_CloseWindow2`, `[JumpBack]_CloseWindowsGeneral`, `[JumpBack]_ConfirmExitTheRoom`, `[JumpBack]_ConfirmGeneral`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]_ConfirmSweepResult`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_EnterGame`, `[JumpBack]_Escape`, `[JumpBack]_ExitTheRoom`, `[JumpBack]_HomeButton`, `[JumpBack]_LevelUp`, `[JumpBack]_Loading`, `[JumpBack]_Login`, `[JumpBack]_NavigateExternalRecruit`, `[JumpBack]_RecruitResult`, `[JumpBack]_ServerMaintenance`, `[JumpBack]_SkipButton`, `[JumpBack]_StartUpLoading`, `[JumpBack]_UnfinishedGame`, `[JumpBack]_UpdateGame`


## #Supplies

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#Supplies` | — | —(仅路由) | `Supplies` |
| &nbsp;&nbsp;1 | `Supplies` | — | —(仅路由) | `DailyGiftCollected` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `DailyGiftCollected` | OCR['明日可领取'] roi=[234, 142, 1045, 496] | —(仅路由) | `EventSupplies` / `SilverMedalRedeemRecord` / `SilverMedalRedeemOffer` / `SilverMedalRedeemAcc` / `VioletMedalRedeemRecord` |

> 该任务挂载的中断保底：`[JumpBack]DailyGift`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateReinforcementSupplies`, `[JumpBack]_ServerMaintenance`


## #DailyStaminaBonus

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#DailyStaminaBonus` | — | —(仅路由) | `DailyStaminaBonus` |
| &nbsp;&nbsp;1 | `DailyStaminaBonus` | — | —(仅路由) | `CollectStaminaBonusNoon` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `CollectStaminaBonusNoon` | OCR['每日行动'] roi=[419, 24, 446, 170] | Click@[431, 584, 1, 1] | `CollectStaminaBonusEvening` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `CollectStaminaBonusEvening` | OCR['每日行动'] roi=[419, 24, 446, 170] | Click@[708, 582, 1, 1] | （结束） |

> 该任务挂载的中断保底：`[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateStaminaBonus`, `[JumpBack]_ServerMaintenance`


## #ShortTermCheckIn

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#ShortTermCheckIn` | — | —(仅路由) | `ShortTermCheckIn` |
| &nbsp;&nbsp;1 | `ShortTermCheckIn` | — | —(仅路由) | `CollectShortTermCheckIn` / `~ShortTermCheckIn` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `CollectShortTermCheckIn` | OCR['点击领取'] roi=[1035, 117, 179, 547] | Click(匹配框中心) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `~ShortTermCheckIn` | OCR['短期支援'] roi=[254, 377, 396, 190] | —(仅路由) | （结束） |

> 该任务挂载的中断保底：`[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateShortTermCheckIn`, `[JumpBack]_ServerMaintenance`


## #JointBlockade

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#JointBlockade` | — | —(仅路由) | `JointBlockade` |
| &nbsp;&nbsp;1 | `JointBlockade` | — | —(仅路由) | `JointBlockadeCompleteFromSystem` / `JointBlockadeFromSystem` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `JointBlockadeCompleteFromSystem` | OCR['108/108'] roi=[0, 483, 168, 128] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `JointBlockadeFromSystem` | OCR['联线封锁'] roi=[0, 458, 189, 128] | Click(匹配框中心) | `~JointBlockadeNA` / `JointBlockadeCompleteFromLevel` / `JointBlockadeTicketsCompleteFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `~JointBlockadeNA` | 模板[BCR/JointBlockadeNA.png] roi=[792, 576, 133, 136] thr=None | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `JointBlockadeCompleteFromLevel` | OCR['108/108'] roi=[106, 554, 218, 135] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `JointBlockadeTicketsCompleteFromLevel` | OCR['^0'] roi=[1161, 0, 119, 92] | —(仅路由) | （结束） |

> 该任务挂载的中断保底：`[JumpBack]ConfirmDiscardJointBlockadeUnfinishedGame`, `[JumpBack]JointBlockadeUnfinishedGame`, `[JumpBack]_ConfirmJointBlockadeResult`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateJointBlockade`, `[JumpBack]_NavigateSystem`, `[JumpBack]_ServerMaintenance`, `[JumpBack]_SweepConfirm`, `[JumpBack]_SweepFromLevel`


## #当期活动

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#当期活动` | — | —(仅路由) | `当期活动` |
| &nbsp;&nbsp;1 | `当期活动` | — | —(仅路由) | `进入活动页` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `进入活动页` | OCR['剩余'] roi=[1045, 212, 240, 194] | Click(匹配框中心) | `选择关卡` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `选择关卡` | OCR['被诅咒的信仰'] roi=[870, 350, 380, 230] | Click(匹配框中心) | `选择小关卡` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `选择小关卡` | OCR['SL11[0O]'] roi=[0, 0, 1280, 720] | Click(匹配框中心) | `点击快速完成` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `点击快速完成` | OCR['快速完成'] roi=[700, 600, 400, 120] | Click(匹配框中心) | `行动力判定` / `行动次数确定` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `行动力判定` | OCR['时'] roi=[454, 189, 608, 165] | Click+offset[0, 70, 0, 0] | `行动次数确定` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `行动次数确定` | OCR['快速完成次数'] roi=[640, 365, 240, 40] | Click@[955, 457, 1, 1] | `点击出发` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `点击出发` | OCR['出发'] roi=[740, 480, 400, 165] | Click(匹配框中心) | `~等待快速完成结果` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `~等待快速完成结果` | OCR['快速完成结果'] roi=[0, 0, 1280, 720] | —(仅路由) | `点击确定` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `点击确定` | OCR['确定', '确认退出'] roi=[940, 600, 340, 120] | Click(匹配框中心) | `退出关卡详情页` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;11 | `退出关卡详情页` | 模板[当期活动/主界面图标.png] roi=[11, 2, 413, 84] thr=0.85 | Click(匹配框中心) | `返回主界面` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;12 | `返回主界面` | 模板[当期活动/主界面图标.png] roi=[11, 2, 413, 84] thr=0.85 | Click(匹配框中心) | （结束） |
| · | `行动次数确定` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateHomepage`, `[JumpBack]_ServerMaintenance`


## #往期活动

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#往期活动` | — | —(仅路由) | `往期活动` |
| &nbsp;&nbsp;1 | `往期活动` | — | —(仅路由) | `进入作战` / `点击往期活动` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `进入作战` | OCR['作战'] roi=[850, 300, 360, 200] | Click(匹配框中心) | `点击往期活动` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `点击往期活动` | 模板[往期活动/往期活动.png] roi=[421, 0, 859, 154] thr=0.85 | Click(匹配框中心) | `~已切换到往期活动` / `点击往期活动_重试2` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `~已切换到往期活动` | 模板[往期活动/往期活动标志.png] roi=[47, 65, 484, 89] thr=0.85 | —(仅路由) | `进入往期活动内部流程` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `进入往期活动内部流程` | DirectHit(必中) | —(仅路由) | `~识别往日行动调令` / `选择往期活动` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `~识别往日行动调令` | OCR['[0-6]'] roi=[351, 92, 173, 48] | —(仅路由) | `记录往日行动调令数` / `选择往期活动` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `记录往日行动调令数` | OCR[] roi=[351, 92, 173, 48] | Custom[记录往日行动调令数] | `~调令为零` / `选择往期活动` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `~调令为零` | Custom | —(仅路由) | `退出往期活动失败` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `退出往期活动失败` | 模板[当期活动/主界面图标.png] roi=[11, 2, 413, 84] thr=0.85 | Click(匹配框中心) | `返回主界面_往期活动失败` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `返回主界面_往期活动失败` | 模板[当期活动/主界面图标.png] roi=[11, 2, 413, 84] thr=0.85 | Click(匹配框中心) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `选择往期活动` | 模板[往期活动/在月光之下.png] roi=[0, 147, 1280, 442] thr=0.8 | Click(匹配框中心) | `进入该往期活动事件` / `往左滑动` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `进入该往期活动事件` | DirectHit(必中) | —(仅路由) | `进入该往期活动事件_未适配` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `进入该往期活动事件_未适配` | DirectHit(必中) | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `往左滑动` | — | Swipe [1270, 368, 1, 1]→[10, 368, 1, 1] d=500 | `选择往期活动_重试2` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `选择往期活动_重试2` | 模板[往期活动/在月光之下.png] roi=[0, 147, 1280, 442] thr=0.8 | Click(匹配框中心) | `进入该往期活动事件` / `往左滑动2` |
| · | `进入该往期活动事件` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;11 | `往左滑动2` | — | Swipe [1270, 368, 1, 1]→[10, 368, 1, 1] d=500 | `选择往期活动_重试3` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;12 | `选择往期活动_重试3` | 模板[往期活动/在月光之下.png] roi=[0, 147, 1280, 442] thr=0.8 | Click(匹配框中心) | `进入该往期活动事件` / `往左滑动3` |
| · | `进入该往期活动事件` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `往左滑动3` | — | Swipe [1270, 368, 1, 1]→[10, 368, 1, 1] d=500 | `选择往期活动_重试4` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;14 | `选择往期活动_重试4` | 模板[往期活动/在月光之下.png] roi=[0, 147, 1280, 442] thr=0.8 | Click(匹配框中心) | `进入该往期活动事件` / `退出往期活动失败` |
| · | `选择往期活动` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `选择往期活动` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `点击往期活动_重试2` | 模板[往期活动/往期活动.png] roi=[421, 0, 859, 154] thr=0.85 | Click(匹配框中心) | `~已切换到往期活动_重试2` / `点击往期活动_重试3` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `~已切换到往期活动_重试2` | 模板[往期活动/往期活动标志.png] roi=[47, 65, 484, 89] thr=0.85 | —(仅路由) | `进入往期活动内部流程` |
| · | `进入往期活动内部流程` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `点击往期活动_重试3` | 模板[往期活动/往期活动.png] roi=[421, 0, 859, 154] thr=0.85 | Click(匹配框中心) | `~已切换到往期活动_重试3` / `退出往期活动失败` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `~已切换到往期活动_重试3` | 模板[往期活动/往期活动标志.png] roi=[47, 65, 484, 89] thr=0.85 | —(仅路由) | `进入往期活动内部流程` |
| · | `进入往期活动内部流程` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `退出往期活动失败` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `点击往期活动` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ConfrimReconnect`, `[JumpBack]_NavigateHomepage`, `[JumpBack]_ServerMaintenance`


## #自动推图

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `#自动推图` | — | —(仅路由) | `播报前提` |
| &nbsp;&nbsp;1 | `播报前提` | DirectHit(必中) | Custom[播报进度] | `播报开始` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `播报开始` | DirectHit(必中) | Custom[播报进度] | `巡检关卡` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `巡检关卡` | DirectHit(必中) | —(仅路由) | `识别未完成关卡` / `推图完成` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `识别未完成关卡` | 模板[自动推图/未完成关卡.png] roi=[0, 0, 1280, 720] thr=0.8 | Click(匹配框中心) | `巡检出发` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `巡检出发` | DirectHit(必中) | —(仅路由) | `识别出发` / `巡检出发2` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `识别出发` | OCR['出发'] roi=[784, 588, 496, 149] | Click(匹配框中心) | `等待编队出现` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `等待编队出现` | DirectHit(必中) | —(仅路由) | `巡检编队` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `巡检编队` | DirectHit(必中) | —(仅路由) | `编队调整检测` / `点击跳过介绍` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `编队调整检测` | 模板[自动推图/编队调整_文字.png] roi=[1000, 439, 304, 132] thr=0.7 | Click(匹配框中心) | `~进入编队选择` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `~进入编队选择` | 模板[自动推图/编队选择关闭.png] roi=[1085, 39, 95, 98] thr=0.85 | —(仅路由) | `选择出战队伍` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;11 | `选择出战队伍` | 模板[自动推图/战斗编队1.png] roi=[166, 350, 146, 80] thr=0.85 | Click+offset[799, 0, 0, 0] | `点击关闭编队` / `选择出战队伍_重试` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;12 | `点击关闭编队` | 模板[自动推图/编队选择关闭.png] roi=[1085, 39, 95, 98] thr=0.85 | Click(匹配框中心) | `点击开始作战` / `点击关闭编队_重试` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `点击开始作战` | 模板[自动推图/开始作战.png] roi=[1036, 593, 197, 111] thr=0.85 | Click(匹配框中心) | `~战斗界面已加载` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;14 | `~战斗界面已加载` | 模板[自动推图/auto.png] roi=[790, 10, 140, 80] thr=0.7 | —(仅路由) | `点击自动战斗` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `点击关闭编队_重试` | 模板[自动推图/编队选择关闭.png] roi=[1085, 39, 95, 98] thr=0.85 | Click(匹配框中心) | `点击开始作战` |
| · | `点击开始作战` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;12 | `选择出战队伍_重试` | 模板[自动推图/战斗编队1.png] roi=[166, 350, 146, 80] thr=0.85 | Click+offset[799, 0, 0, 0] | `点击关闭编队` / `选择出战队伍_失败停止` |
| · | `点击关闭编队` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `选择出战队伍_失败停止` | DirectHit(必中) | —(仅路由) | `点击关闭编队` |
| · | `点击关闭编队` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `点击跳过介绍` | DirectHit(必中) | Click@[1218, 273, 1, 1] | `巡检编队` |
| · | `巡检编队` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `巡检出发2` | DirectHit(必中) | —(仅路由) | `识别出发` / `巡检出发3` |
| · | `识别出发` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `巡检出发3` | DirectHit(必中) | —(仅路由) | `识别出发` / `巡检出发4` |
| · | `识别出发` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `巡检出发4` | DirectHit(必中) | —(仅路由) | `识别出发` / `识别出发失败处理` |
| · | `识别出发` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `识别出发失败处理` | DirectHit(必中) | Custom[存失败截图] | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `推图完成` | DirectHit(必中) | Custom[播报进度] | （结束） |

## #SeaOfCognition

> 入口 `#SeaOfCognition` 经 `SoCResume` 路由（可在任意中途界面续跑，14 个候选状态见下方模板/OCR 表与节点索引）。

> 下面给出**首次从 BCR 开始的完整主链路**（覆盖步骤 0→12），UI 改版重测按此顺序逐节点核对即可。

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路) |
|----|------|------------------|------|----------------|
| 0 | `SoCFallbackStart` | DirectHit(必中) | —(仅路由) | `SoCAtBCR` |
| 1 | `SoCAtBCR` | 模板[SeaOfCognition/认知海域图标.png] roi=[0, 500, 1280, 220] thr=0.8 | Click(匹配框中心) | `SoCSelectLayer` |
| 2 | `SoCSelectLayer` | OCR['[梦夢][渊淵][层層]'] roi=[0, 0, 1280, 720] | Click(匹配框中心) | `SoCStartDive` / `SoCContinueDive` |
| 3 | `SoCStartDive` | OCR['开始下[潜潛]'] roi=[820, 545, 460, 175] | Click(匹配框中心) | `SoCResume` / `SoCDeepDive` / `SoCDeepDiveFree` / `SoCDeepDiveFallback` |
| 4 | `SoCDeepDive` | OCR['深[潜潛]指引'] roi=[0, 0, 1280, 720] | Click(匹配框中心) | `SoCTeamEnter` |
| 5 | `SoCTeamEnter` | 模板[SeaOfCognition/进入海域.png] roi=[0, 0, 1280, 720] thr=0.8 | Click(匹配框中心) | `SoCInspirationNode` / `SoCInspirationNodeOCR` |
| 6 | `SoCInspirationNode` | 模板[SeaOfCognition/认知海域灵感节点.png] roi=[192, 159, 358, 556] thr=0.8 | —(仅路由) | `SoCInspirationClick` |
| 7 | `SoCInspirationClick` | OCR['[灵靈]感[节節][点點]'] roi=[0, 0, 1280, 720] | Click(匹配框中心) | `SoCGBLoop` |
| 8 | `SoCGBLoop` | — | —(仅路由) | `SoCGBPickAvailable` / `SoCGBSwipe` |
| 9 | `SoCGBPickAvailable` | DirectHit(必中) | Custom[None] | `SoCGBContinue` |
| 10 | `SoCGBSwipe` | DirectHit(必中) | Swipe [1270, 360]→[870, 360] d=800 | `SoCGBLoop` |
| 11 | `SoCGBContinue` | 模板[SeaOfCognition/BuffContinue.png] roi=[450, 600, 380, 100] thr=0.8 | Click(匹配框中心) | `SoCInBattleBuff` / `SoCInBattleBuffOCR` |
| 12 | `SoCInBattleBuff` | 模板[SeaOfCognition/局内buff选择.png] roi=None thr=0.8 | Click@[472, 344, 1, 1] | `SoCInBattleBuff2nd` |
| 13 | `SoCInBattleBuff2nd` | DirectHit(必中) | Click@[472, 344, 1, 1] | `SoCInBattleBuffConfirm` |
| 14 | `SoCInBattleBuffConfirm` | 模板[SeaOfCognition/QiFa.png] roi=None thr=0.8 | Click(匹配框中心) | `SoCStartBattle` |
| 15 | `SoCStartBattle` | 模板[SeaOfCognition/认知海域开始作战.png] roi=None thr=0.8 | Click(匹配框中心) | `SoCAutoBattle` |
| 16 | `SoCAutoBattle` | DirectHit(必中) | Custom[SoCAwaitBattle] | `SoCContinue` |
| 17 | `SoCContinue` | 模板[SeaOfCognition/战斗完成继续.png] roi=[950, 600, 330, 120] thr=0.8 | Click(匹配框中心) | `SoCAfterContinue` |
| 18 | `SoCAfterContinue` | DirectHit(必中) | —(仅路由) | `SoCState_GB1` / `SoCState_GB0` / `SoCNodeLoop` |
| 19 | `SoCNodeLoop` | — | —(仅路由) | `SoCInBattleBuff` / `SoCInBattleBuffOCR` / `SoCClaim` |
| 20 | `SoCClaim` | OCR['[领領]取', '[确確][认認]'] roi=[0, 0, 1280, 720] | Click(匹配框中心) | `SoCAtBCR` |
| 21 | `SoCDone` | DirectHit(必中) | —(仅路由) | （结束/循环） |

> 挂载的中断保底：`[JumpBack]_ConfirmMiddle`, `[JumpBack]_ConfrimReconnect`, `[JumpBack]_LevelUp`, `[JumpBack]_NavigateBCR`, `[JumpBack]_ServerMaintenance`


---
# 公共共享节点（被多个任务复用）


### `_NavigateBCR`

- 识别：OCR['主线故事'] roi=[1080, 607, 200, 113]
- 动作：—(仅路由)
- 后续：`~BCR` / `[JumpBack]_ServerMaintenance` / `[JumpBack]_ConfrimReconnect` / `[JumpBack]_ConfirmMiddle` / `[JumpBack]_LevelUp` / `[JumpBack]_BCRFromHome` / `[JumpBack]_NavigateHomepage`

### `_BCRHead`

- 识别：—
- 动作：Swipe [10, 360, 1, 1]→[1270, 360, 1, 1] d=500
- 后续：

### `_BCRTail`

- 识别：—
- 动作：Swipe [1270, 360, 1, 1]→[10, 360, 1, 1] d=500
- 后续：

### `_NavigateHomepage`

- 识别：模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8
- 动作：—(仅路由)
- 后续：`_EnsureHomepage` / `[JumpBack]_UpdateGame` / `[JumpBack]_UnfinishedGame` / `[JumpBack]_ConfirmExitTheRoom` / `[JumpBack]_ServerMaintenance` / `[JumpBack]_ConfrimReconnect` / `[JumpBack]_CancelGeneral` / `[JumpBack]_Cancel1` / `[JumpBack]_Cancel2` / `[JumpBack]_Cancel3` / `[JumpBack]_Cancel4` / `[JumpBack]_ConfirmGeneral` / `[JumpBack]_ConfirmMiddle` / `[JumpBack]_ConfirmSweepResult` / `[JumpBack]_CloseWindowsGeneral` / `[JumpBack]_CloseWindow1` / `[JumpBack]_CloseWindow2` / `[JumpBack]_SkipButton` / `[JumpBack]_LevelUp` / `[JumpBack]_HomeButton` / `[JumpBack]_BackButton` / `[JumpBack]_Login` / `[JumpBack]_EnterGame` / `[JumpBack]_ExitTheRoom` / `[JumpBack]_Loading` / `[JumpBack]_StartUpLoading` / `[JumpBack]_Escape`

### `_ServerMaintenance`

- 识别：OCR['维护'] roi=[485, 227, 311, 133]
- 动作：—(仅路由)
- 后续：`_ConfirmServerMaintenance`

### `_ConfrimReconnect`

- 识别：OCR['回来', '继续游玩'] roi=[437, 234, 404, 135]
- 动作：—(仅路由)
- 后续：`_ConfirmMiddle`

### `_ConfirmMiddle`

- 识别：模板[Utils/ConfirmMiddle.png] roi=[558, 1, 164, 719] thr=None
- 动作：Click(匹配框中心)
- 后续：

### `_LevelUp`

- 识别：OCR['行动力恢复'] roi=[827, 207, 207, 133]
- 动作：Click@[318, 36, 1, 1]
- 后续：

### `_CloseWindows`

- 识别：—
- 动作：—(仅路由)
- 后续：`_CloseWindowsGeneral` / `_CloseWindow1` / `_CloseWindow2`

### `_SeaOfCognitionReward`

- 识别：OCR['获取物资'] roi=[380, 30, 520, 190]
- 动作：Click@[640, 650, 1, 1]
- 后续：

---
# 模板图片依赖汇总（UI 改版后需重新截图的项）

| 模板图片 | 被以下任务使用 |
|---------|----------------|
| `BCR/AtLiminalZone.png` | #LiminalZone |
| `BCR/JointBlockadeNA.png` | #JointBlockade |
| `BCR/LiminalZoneNA.png` | #Farm、#LiminalZone |
| `Homepage/SystemButton.png` | #ExternalRecruit、#StartUp |
| `Mailbox/CollectMail.png` | #Mailbox |
| `Mission/AtDailyMission.png` | #CollectRewards |
| `Mission/AtWeeklyMission.png` | #CollectRewards |
| `Protocol/AtProtocolReward.png` | #CountermeasureProtocol |
| `Protocol/AtProtocolSpecial.png` | #CountermeasureProtocol |
| `Protocol/AtProtocolWeekly.png` | #CountermeasureProtocol |
| `SystemPage/Settings.png` | #LiminalZone |
| `当期活动/主界面图标.png` | #当期活动、#往期活动 |
| `往期活动/在月光之下.png` | #往期活动 |
| `往期活动/往期活动.png` | #往期活动 |
| `往期活动/往期活动标志.png` | #往期活动 |
| `自动推图/auto.png` | #自动推图 |
| `自动推图/开始作战.png` | #自动推图 |
| `自动推图/战斗编队1.png` | #自动推图 |
| `自动推图/未完成关卡.png` | #自动推图 |
| `自动推图/编队调整_文字.png` | #自动推图 |
| `自动推图/编队选择关闭.png` | #自动推图 |

---
# OCR 文案依赖汇总（UI 改版后需逐字核对的项）

| OCR 期望文案 | 被以下任务使用 |
|-------------|----------------|
| 108/108 | #JointBlockade |
| 480/480 | #LiminalZone |
| SL11[0O] | #当期活动 |
| [0-6] | #往期活动 |
| ^0 | #CrisisMissionTickets、#JointBlockade |
| 不 | #ExternalRecruit |
| 主线故事 | #CrisisMissionTickets、#Farm |
| 任务已满 | #ExternalRecruit |
| 作战 | #往期活动 |
| 具 | #ExternalRecruit |
| 出发 | #当期活动、#自动推图 |
| 剩余 | #当期活动 |
| 回收物 | #LiminalZone |
| 外部招募 | #ExternalRecruit |
| 已 | #UrbanPatrol |
| 已满级 | #CountermeasureProtocol |
| 快速完成 | #CrisisMissionTickets、#Farm、#当期活动 |
| 快速完成次数 | #当期活动 |
| 快速完成结果 | #当期活动 |
| 扫汤 | #Farm、#LiminalZone |
| 扫荡 | #Farm、#LiminalZone |
| 时 | #当期活动 |
| 明日可领取 | #Supplies |
| 每日行动 | #DailyStaminaBonus |
| 点击领取 | #ShortTermCheckIn |
| 短期支援 | #ShortTermCheckIn |
| 确定 | #当期活动 |
| 确认退出 | #当期活动 |
| 联线封锁 | #JointBlockade |
| 被诅咒的信仰 | #当期活动 |
| 足 | #ExternalRecruit |
| 进行探索 | #LiminalZone |
| 道 | #ExternalRecruit |
| 重复行动 | #CrisisMissionTickets、#Farm |

---
# 完整节点索引（全部节点 → 识别 / 动作）

> 任一任务流程里出现的节点，都可在本表查到其 UI 依赖；路由/必中节点（DirectHit）标注「必中」。

| 节点 | 识别 | 动作 |
|------|------|------|
| `#CollectRewards` | — | —(仅路由) |
| `#CountermeasureProtocol` | — | —(仅路由) |
| `#CrisisMissionTickets` | — | —(仅路由) |
| `#DailyStaminaBonus` | — | —(仅路由) |
| `#ExternalRecruit` | — | —(仅路由) |
| `#Farm` | — | —(仅路由) |
| `#JointBlockade` | — | —(仅路由) |
| `#LiminalZone` | — | —(仅路由) |
| `#Mailbox` | — | —(仅路由) |
| `#SeaOfCognition` | — | —(仅路由) |
| `#ShortTermCheckIn` | — | —(仅路由) |
| `#ShutDown` | — | —(仅路由) |
| `#StartUp` | — | —(仅路由) |
| `#Supplies` | — | —(仅路由) |
| `#TheRoom` | — | —(仅路由) |
| `#UrbanPatrol` | — | —(仅路由) |
| `#当期活动` | — | —(仅路由) |
| `#往期活动` | — | —(仅路由) |
| `#自动推图` | — | —(仅路由) |
| `AmuletSoldOut` | OCR['^0/'] roi=[721, 0, 180, 136] | —(仅路由) |
| `CloseUseStaminaItem` | OCR['下次恢复时间'] roi=[452, 12, 207, 125] | Click@[1080, 327, 1, 1] |
| `CollectCollabPts` | 模板[Mission/AtMutualAid.png] roi=[59, 47, 248, 134] thr=None | Click@[1079, 604, 1, 1] |
| `CollectDailyCollabPts` | 模板[Mission/AtUrbanPatrol.png] roi=[1053, 0, 219, 136] thr=None | Click@[1133, 577, 1, 1] |
| `CollectDailyGift` | OCR['^可领取'] roi=[234, 142, 1045, 496] | Click(匹配框中心) |
| `CollectDailyReward` | 模板[Mission/AtDailyMission.png] roi=[677, 0, 214, 135] thr=None | Click@[1151, 669, 1, 1] |
| `CollectEventGift` | OCR['^可领取'] roi=[234, 142, 1045, 496] | Click(匹配框中心) |
| `CollectMail` | 模板[Mailbox/CollectMail.png] roi=[55, 586, 229, 132] thr=None | Click(匹配框中心) |
| `CollectProtocolReward` | 模板[Protocol/AtProtocolReward.png] roi=[414, 172, 172, 195] thr=None | Click@[1103, 640, 1, 1] |
| `CollectProtocolSpecial` | 模板[Protocol/AtProtocolSpecial.png] roi=[927, 135, 184, 133] thr=None | Click@[1103, 640, 1, 1] |
| `CollectProtocolWeekly` | 模板[Protocol/AtProtocolWeekly.png] roi=[556, 135, 186, 134] thr=None | Click@[1103, 640, 1, 1] |
| `CollectShortTermCheckIn` | OCR['点击领取'] roi=[1035, 117, 179, 547] | Click(匹配框中心) |
| `CollectStaminaBonusEvening` | OCR['每日行动'] roi=[419, 24, 446, 170] | Click@[708, 582, 1, 1] |
| `CollectStaminaBonusNoon` | OCR['每日行动'] roi=[419, 24, 446, 170] | Click@[431, 584, 1, 1] |
| `CollectWeeklyReward` | 模板[Mission/AtWeeklyMission.png] roi=[867, 0, 209, 131] thr=None | Click@[1151, 669, 1, 1] |
| `ConfirmDiscardJointBlockadeUnfinishedGame` | OCR['结束本次联线封锁'] roi=[498, 184, 288, 136] | Click@[714, 450, 1, 1] |
| `ConfirmExternalRecruit` | — | Click@[771, 479, 1, 1] |
| `ConfirmFilmRedeem` | OCR['胶卷兑换', '胶卷兌换'] roi=[563, 68, 245, 140] | Click@[809, 657, 1, 1] |
| `ConfirmRitual` | OCR['探员需求'] roi=[187, 0, 197, 129] | Click@[217, 562, 1, 1] |
| `ConfirmRitualUseKeys` | 模板[TheRoom/AtUseKeys.png] roi=[432, 195, 136, 135] thr=None | Click@[806, 509, 1, 1] |
| `ConfirmSellAmulet` | OCR['分解数量'] roi=[530, 166, 217, 137] | Click@[787, 461, 1, 1] |
| `ConfirmUseStaminaItem` | OCR['确定'] roi=[668, 547, 161, 137] | Click(匹配框中心) |
| `CountermeasureProtocol` | — | —(仅路由) |
| `CrisisMissionTickets` | — | —(仅路由) |
| `CrisisMissionTicketsCompletedFromLevel` | OCR['^0'] roi=[1161, 0, 119, 92] | —(仅路由) |
| `CrisisMissionTicketsFromBCR` | OCR['主线故事'] roi=[1080, 607, 200, 113] | —(仅路由) |
| `CrisisMissionTicketsFromLevel` | OCR['快速完成'] roi=[804, 591, 273, 129] | —(仅路由) |
| `CrisisMissionTicketsSelectLevel` | — | —(仅路由) |
| `CrisisMissonTicketsSweepStrategy` | 模板[BCR/AtSweep.png] roi=[148, 176, 308, 292] thr=None | —(仅路由) |
| `DailyCollabPtsCollected` | OCR['已'] roi=[1052, 516, 166, 124] | —(仅路由) |
| `DailyGift` | OCR['资源礼包'] roi=[220, 40, 188, 125] | —(仅路由) |
| `DailyGiftCollected` | OCR['明日可领取'] roi=[234, 142, 1045, 496] | —(仅路由) |
| `DailyReward` | — | —(仅路由) |
| `DailyStaminaBonus` | — | —(仅路由) |
| `EnterSellAmulet` | 模板[TheRoom/AtStorage.png] roi=[603, 0, 144, 145] thr=None | Click@[1040, 691, 1, 1] |
| `EventSupplies` | OCR['活动货柜'] roi=[36, 348, 201, 131] | —(仅路由) |
| `ExternalRecruit` | — | —(仅路由) |
| `ExternalRecruitAcc` | 模板[Recruit/Accelerate.png] roi=[709, 480, 136, 140] thr=None | Click(匹配框中心) |
| `ExternalRecruitMax` | 模板[Recruit/ExternalRecruitMax.png] roi=[755, 302, 148, 143] thr=None | Click(匹配框中心) |
| `ExternalRecruitOutofOffer` | OCR['道', '具', '不', '足'] roi=[929, 112, 186, 125] | —(仅路由) |
| `ExternalRecruitProceed` | OCR['启动招募', '招募成功'] roi=[903, 477, 198, 135] | Click(匹配框中心) |
| `ExternalRecruitQueueFull` | OCR['任务已满'] roi=[906, 475, 202, 137] | —(仅路由) |
| `Farm` | — | —(仅路由) |
| `FarmFromLevel` | OCR['扫荡', '扫汤', '快速完成'] roi=[804, 591, 273, 129] | —(仅路由) |
| `FarmOutOfStamina` | OCR['下次恢复时间'] roi=[452, 12, 207, 125] | —(仅路由) |
| `FarmSelectLevel` | — | —(仅路由) |
| `FarmUseExpiringItem` | OCR['小时'] roi=[539, 320, 166, 128] | Click@[628, 545, 1, 1] |
| `FilmRedeem` | — | —(仅路由) |
| `FilmRedeemOutOfFilm` | 模板[Utils/Tips.png] roi=[868, 95, 142, 300] thr=None | —(仅路由) |
| `FindEventGift` | OCR['当期热卖', '活动货品'] roi=[220, 40, 188, 125] | —(仅路由) |
| `JointBlockade` | — | —(仅路由) |
| `JointBlockadeCompleteFromLevel` | OCR['108/108'] roi=[106, 554, 218, 135] | —(仅路由) |
| `JointBlockadeCompleteFromSystem` | OCR['108/108'] roi=[0, 483, 168, 128] | —(仅路由) |
| `JointBlockadeFromSystem` | OCR['联线封锁'] roi=[0, 458, 189, 128] | Click(匹配框中心) |
| `JointBlockadeTicketsCompleteFromLevel` | OCR['^0'] roi=[1161, 0, 119, 92] | —(仅路由) |
| `JointBlockadeUnfinishedGame` | OCR['中途放弃'] roi=[468, 557, 185, 130] | StopTask |
| `Key2Agent` | 模板[TheRoom/Key2Agent.png] roi=[513, 278, 133, 136] thr=None | —(仅路由) |
| `Key2AgentOutOfKey` | ColorMatch | —(仅路由) |
| `Key2ArchivePieces` | OCR['追加档案残片'] roi=[879, 584, 247, 135] | Click(匹配框中心) |
| `LiminalZone` | — | —(仅路由) |
| `LiminalZoneCompletedFromLevel` | OCR['480/480'] roi=[92, 620, 225, 100] | —(仅路由) |
| `LiminalZoneCompletedFromSystem` | OCR['480/480'] roi=[199, 312, 223, 128] | —(仅路由) |
| `LiminalZoneFromLevel` | OCR['扫荡', '扫汤'] roi=[804, 591, 273, 129] | —(仅路由) |
| `LiminalZoneFromSystem` | 模板[SystemPage/Settings.png] roi=[0, 559, 149, 149] thr=None | Click@[337, 362, 1, 1] |
| `LiminalZoneOutOfStamina` | OCR['下次恢复时间'] roi=[452, 12, 207, 125] | —(仅路由) |
| `LiminalZoneSelectLevel` | — | —(仅路由) |
| `LiminalZoneUseStaminaItem` | 模板[BCR/StaminaItemInc.png] roi=[566, 482, 127, 128] thr=None | Click(匹配框中心) |
| `Mailbox` | — | —(仅路由) |
| `ManageExternalRecruit` | OCR['外部招募'] roi=[325, 322, 290, 153] | —(仅路由) |
| `NextAmulet` | 模板[TheRoom/AtStorage.png] roi=[603, 0, 144, 145] thr=None | Click@[715, 123, 1, 1] |
| `NextRitual` | 模板[TheRoom/AtRitual.png] roi=[0, 29, 308, 288] thr=None | Click@[420, 207, 1, 1] |
| `NoEventGift` | OCR['^可领取'] roi=[234, 142, 1045, 496] | —(仅路由) |
| `ProtocolFullLevel` | OCR['已满级'] roi=[550, 65, 171, 133] | —(仅路由) |
| `Ritual` | — | —(仅路由) |
| `RitualCompleted` | 模板[TheRoom/RitualCompleted.png] roi=[620, 420, 377, 179] thr=None | —(仅路由) |
| `RitualCompleted_NoKey2Agent` | OCR['加速'] roi=[125, 500, 182, 126] | —(仅路由) |
| `RitualCompleted_NoKey2Archive` | OCR['追加档案残片'] roi=[879, 584, 247, 135] | —(仅路由) |
| `RitualNoAmulet` | OCR['不足'] roi=[123, 500, 185, 127] | —(仅路由) |
| `RitualRewardDust` | OCR['探员需求'] roi=[187, 0, 197, 129] | Click@[1179, 415, 1, 1] |
| `RitualRewardFund` | OCR['探员需求'] roi=[187, 0, 197, 129] | Click@[1179, 240, 1, 1] |
| `RitualRewardSample` | OCR['探员需求'] roi=[187, 0, 197, 129] | Click@[1179, 501, 1, 1] |
| `RitualRewardSelect` | OCR['探员需求'] roi=[187, 0, 197, 129] | —(仅路由) |
| `RitualRewardTape` | OCR['探员需求'] roi=[187, 0, 197, 129] | Click@[1179, 329, 1, 1] |
| `RitualUseAllKeys` | 模板[TheRoom/AtUseKeys.png] roi=[432, 195, 136, 135] thr=None | Click@[772, 410, 1, 1] |
| `SelectAllFriends` | 模板[Mission/AtMutualAid.png] roi=[59, 47, 248, 134] thr=None | Click@[840, 109, 1, 1] |
| `SelectAmuletCount` | OCR['分解数量'] roi=[530, 166, 217, 137] | Click@[1037, 344, 1, 1] |
| `SelectLevelFromBCR` | OCR['主线故事'] roi=[1080, 607, 200, 113] | —(仅路由) |
| `SelectLevelFromLiminalZone` | 模板[BCR/AtLiminalZone.png] roi=[45, 81, 147, 144] thr=None | —(仅路由) |
| `SellAmulet` | — | —(仅路由) |
| `SendCollabPts` | 模板[Mission/AtMutualAid.png] roi=[59, 47, 248, 134] thr=None | Click@[1081, 205, 1, 1] |
| `ShortTermCheckIn` | — | —(仅路由) |
| `SilverMedalRedeemAcc` | — | —(仅路由) |
| `SilverMedalRedeemAccComplete` | OCR['剩余购买次数0'] roi=[876, 151, 230, 125] | Click@[652, 512, 1, 1] |
| `SilverMedalRedeemAccConfirm` | OCR['急务招聘书'] roi=[481, 134, 260, 141] | Click@[941, 512, 1, 1] |
| `SilverMedalRedeemAccFound` | OCR['急务招聘书'] roi=[234, 142, 1045, 496] | Click(匹配框中心) |
| `SilverMedalRedeemAccMax` | OCR['急务招聘书'] roi=[481, 134, 260, 141] | Click@[1016, 395, 1, 1] |
| `SilverMedalRedeemAccOutOfMedal` | 模板[Utils/Tips.png] roi=[868, 95, 142, 300] thr=None | —(仅路由) |
| `SilverMedalRedeemOffer` | — | —(仅路由) |
| `SilverMedalRedeemOfferComplete` | OCR['剩余购买次数0'] roi=[876, 151, 230, 125] | Click@[652, 512, 1, 1] |
| `SilverMedalRedeemOfferConfirm` | OCR['外部招聘书'] roi=[481, 134, 260, 141] | Click@[941, 512, 1, 1] |
| `SilverMedalRedeemOfferFound` | OCR['外部招聘书'] roi=[234, 142, 1045, 496] | Click(匹配框中心) |
| `SilverMedalRedeemOfferMax` | OCR['外部招聘书'] roi=[481, 134, 260, 141] | Click@[1016, 395, 1, 1] |
| `SilverMedalRedeemOfferOutOfMedal` | 模板[Utils/Tips.png] roi=[868, 95, 142, 300] thr=None | —(仅路由) |
| `SilverMedalRedeemRecord` | — | —(仅路由) |
| `SilverMedalRedeemRecordComplete` | OCR['剩余购买次数0'] roi=[876, 151, 230, 125] | Click@[652, 512, 1, 1] |
| `SilverMedalRedeemRecordConfirm` | OCR['银锡信息数据'] roi=[480, 135, 289, 138] | Click@[941, 512, 1, 1] |
| `SilverMedalRedeemRecordFound` | OCR['银锡信息数据'] roi=[234, 142, 1045, 496] | Click(匹配框中心) |
| `SilverMedalRedeemRecordMax` | OCR['银锡信息数据'] roi=[480, 135, 289, 138] | Click@[1016, 395, 1, 1] |
| `SilverMedalRedeemRecordOutOfMedal` | 模板[Utils/Tips.png] roi=[868, 95, 142, 300] thr=None | —(仅路由) |
| `SoCAfterContinue` | DirectHit(必中) | —(仅路由) |
| `SoCAtBCR` | 模板[SeaOfCognition/认知海域图标.png] roi=[0, 500, 1280, 220] thr=0.8 | Click(匹配框中心) |
| `SoCAutoBattle` | DirectHit(必中) | Custom[SoCAwaitBattle] |
| `SoCClaim` | OCR['[领領]取', '[确確][认認]'] roi=[0, 0, 1280, 720] | Click(匹配框中心) |
| `SoCContinue` | 模板[SeaOfCognition/战斗完成继续.png] roi=[950, 600, 330, 120] thr=0.8 | Click(匹配框中心) |
| `SoCContinueDive` | 模板[SeaOfCognition/认知海域继续下潜.png] roi=[820, 545, 460, 175] thr=0.8 | Click(匹配框中心) |
| `SoCDeepDive` | OCR['深[潜潛]指引'] roi=[0, 0, 1280, 720] | Click(匹配框中心) |
| `SoCDeepDiveFallback` | DirectHit(必中) | Click@[351, 581, 1, 1] |
| `SoCDeepDiveFree` | OCR['自由探索', '自由', '探索'] roi=[0, 0, 1280, 720] | Click(匹配框中心) |
| `SoCDone` | DirectHit(必中) | —(仅路由) |
| `SoCFallbackStart` | DirectHit(必中) | —(仅路由) |
| `SoCGBContinue` | 模板[SeaOfCognition/BuffContinue.png] roi=[450, 600, 380, 100] thr=0.8 | Click(匹配框中心) |
| `SoCGBDone` | DirectHit(必中) | —(仅路由) |
| `SoCGBLoop` | — | —(仅路由) |
| `SoCGBPickAvailable` | DirectHit(必中) | Custom[None] |
| `SoCGBSwipe` | DirectHit(必中) | Swipe [1270, 360]→[870, 360] d=800 |
| `SoCInBattleBuff` | 模板[SeaOfCognition/局内buff选择.png] roi=None thr=0.8 | Click@[472, 344, 1, 1] |
| `SoCInBattleBuff2nd` | DirectHit(必中) | Click@[472, 344, 1, 1] |
| `SoCInBattleBuffConfirm` | 模板[SeaOfCognition/QiFa.png] roi=None thr=0.8 | Click(匹配框中心) |
| `SoCInBattleBuffOCR` | OCR['请选择一个短暂灵感'] roi=[850, 0, 430, 50] | Click@[472, 344, 1, 1] |
| `SoCInspirationClick` | OCR['[灵靈]感[节節][点點]'] roi=[0, 0, 1280, 720] | Click(匹配框中心) |
| `SoCInspirationFallback` | DirectHit(必中) | Click@[351, 581, 1, 1] |
| `SoCInspirationNode` | 模板[SeaOfCognition/认知海域灵感节点.png] roi=[192, 159, 358, 556] thr=0.8 | —(仅路由) |
| `SoCInspirationNodeOCR` | OCR['[灵靈]感[节節][点點]'] roi=[192, 159, 358, 556] | —(仅路由) |
| `SoCNodeLoop` | — | —(仅路由) |
| `SoCResume` | DirectHit(必中) | —(仅路由) |
| `SoCSelectLayer` | OCR['[梦夢][渊淵][层層]'] roi=[0, 0, 1280, 720] | Click(匹配框中心) |
| `SoCStartBattle` | 模板[SeaOfCognition/认知海域开始作战.png] roi=None thr=0.8 | Click(匹配框中心) |
| `SoCStartDive` | OCR['开始下[潜潛]'] roi=[820, 545, 460, 175] | Click(匹配框中心) |
| `SoCState_GB0` | 模板[SeaOfCognition/剩余可选灵感0.png] roi=None thr=0.8 | —(仅路由) |
| `SoCState_GB1` | OCR['剩余可选灵感'] roi=[400, 560, 500, 110] | —(仅路由) |
| `SoCTeamEnter` | 模板[SeaOfCognition/进入海域.png] roi=[0, 0, 1280, 720] thr=0.8 | Click(匹配框中心) |
| `Supplies` | — | —(仅路由) |
| `UrbanPatrol` | — | —(仅路由) |
| `UrbanPatrolPuchase` | 模板[Mission/AtUrbanPatrol.png] roi=[1053, 0, 219, 136] thr=None | Click@[241, 522, 1, 1] |
| `VioletMedalRedeemRecord` | — | —(仅路由) |
| `VioletMedalRedeemRecordAtVioletMedal` | 模板[Supplies/AtVioletMedal.png] roi=[697, 28, 269, 148] thr=None | —(仅路由) |
| `VioletMedalRedeemRecordComplete` | OCR['剩余购买次数0'] roi=[876, 151, 230, 125] | Click@[652, 512, 1, 1] |
| `VioletMedalRedeemRecordConfirm` | OCR['银锡信息数据'] roi=[480, 135, 289, 138] | Click@[941, 512, 1, 1] |
| `VioletMedalRedeemRecordFound` | OCR['银锡信息数据'] roi=[234, 142, 1045, 496] | Click(匹配框中心) |
| `VioletMedalRedeemRecordMax` | OCR['银锡信息数据'] roi=[480, 135, 289, 138] | Click@[1016, 395, 1, 1] |
| `VioletMedalRedeemRecordOutOfMedal` | 模板[Utils/Tips.png] roi=[868, 95, 142, 300] thr=None | —(仅路由) |
| `WaitExternalRecruitResult` | — | —(仅路由) |
| `_AgentSelectFromRitual` | 模板[TheRoom/AtRitual.png] roi=[0, 29, 308, 288] thr=None | Click@[420, 207, 1, 1] |
| `_AppraisalFromBCR` | 模板[BCR/Appraisal.png] roi=[745, 600, 217, 120] thr=None | Click(匹配框中心) |
| `_ApprasialHead` | OCR['火线特攻', '虎胆龙威', '巅峰时刻', '铜墙铁壁'] roi=[0, 407, 1280, 142] | —(仅路由) |
| `_ApprasialTail` | OCR['火线特攻', '虎胆龙威', '巅峰时刻', '铜墙铁壁'] roi=[0, 407, 1280, 142] | —(仅路由) |
| `_BCRFromHome` | 模板[['Homepage/BCR_default.png', 'Homepage/BCR_compact.png']] roi=[750, 58, 530, 578] thr=None | Click(匹配框中心) |
| `_BCRHead` | — | Swipe [10, 360, 1, 1]→[1270, 360, 1, 1] d=500 |
| `_BCRTail` | — | Swipe [1270, 360, 1, 1]→[10, 360, 1, 1] d=500 |
| `_BackButton` | 模板[Utils/BackButton.png] roi=[48, 0, 151, 143] thr=None | Click(匹配框中心) |
| `_Cancel` | — | —(仅路由) |
| `_Cancel1` | OCR['取消'] roi=[469, 412, 174, 142] | Click(匹配框中心) |
| `_Cancel2` | OCR['取消'] roi=[716, 586, 175, 134] | Click(匹配框中心) |
| `_Cancel3` | OCR['取消'] roi=[465, 590, 150, 130] | Click(匹配框中心) |
| `_Cancel4` | OCR['取消'] roi=[574, 448, 162, 125] | Click(匹配框中心) |
| `_CancelExitTheRoom` | OCR['离开'] roi=[502, 223, 267, 142] | —(仅路由) |
| `_CancelExternalRecruitPopup` | OCR['启动招募', '加速完成'] roi=[524, 177, 231, 137] | —(仅路由) |
| `_CancelFilmRedeem` | OCR['胶卷兑换', '胶卷兌换'] roi=[563, 68, 245, 140] | —(仅路由) |
| `_CancelGeneral` | 模板[Utils/CancelGeneral.png] roi=[481, 318, 155, 153] thr=None | Click(匹配框中心) |
| `_CancelKey2Agent` | 模板[TheRoom/Key2Agent.png] roi=[513, 278, 133, 136] thr=None | —(仅路由) |
| `_CancelKey2ArchivePieces` | 模板[TheRoom/AtUseKeys.png] roi=[432, 195, 136, 135] thr=None | —(仅路由) |
| `_CancelLiminalZoneOverflow` | OCR['进行探索', '回收物'] roi=[222, 225, 834, 136] | —(仅路由) |
| `_CloseMeditationLog` | OCR['冥', '想'] roi=[511, 0, 257, 150] | —(仅路由) |
| `_CloseMutualAid` | OCR['互助'] roi=[52, 38, 260, 149] | —(仅路由) |
| `_CloseRitualResult` | OCR['解读结果'] roi=[46, 43, 361, 172] | —(仅路由) |
| `_CloseSellAmulet` | OCR['分解数量'] roi=[530, 166, 217, 137] | —(仅路由) |
| `_CloseWindow1` | 模板[Utils/CloseWindow1.png] roi=[1102, 143, 130, 135] thr=None | Click(匹配框中心) |
| `_CloseWindow2` | 模板[Utils/CloseWindow2.png] roi=[1163, 25, 117, 148] thr=None | Click(匹配框中心) |
| `_CloseWindows` | — | —(仅路由) |
| `_CloseWindowsGeneral` | 模板[Utils/CloseWindows.png] roi=[1081, 29, 142, 143] thr=None | Click(匹配框中心) |
| `_Confirm` | — | —(仅路由) |
| `_ConfirmExitTheRoom` | OCR['离开'] roi=[502, 223, 267, 142] | —(仅路由) |
| `_ConfirmGeneral` | 模板[Utils/ConfirmGeneral.png] roi=[644, 320, 158, 152] thr=None | Click(匹配框中心) |
| `_ConfirmJointBlockadeResult` | OCR['封锁完成', '终止探索'] roi=[110, 34, 461, 199] | Click(匹配框中心) |
| `_ConfirmLiminalZoneOverflow` | OCR['进行探索', '回收物'] roi=[222, 225, 834, 136] | —(仅路由) |
| `_ConfirmLiminalZoneResult` | OCR['探索'] roi=[121, 31, 454, 192] | Click(匹配框中心) |
| `_ConfirmMiddle` | 模板[Utils/ConfirmMiddle.png] roi=[558, 1, 164, 719] thr=None | Click(匹配框中心) |
| `_ConfirmServerMaintenance` | 模板[Utils/ConfirmMiddle.png] roi=[558, 1, 164, 719] thr=None | Click(匹配框中心) |
| `_ConfirmSweepResult` | OCR['确定'] roi=[1014, 611, 162, 109] | Click(匹配框中心) |
| `_ConfrimReconnect` | OCR['回来', '继续游玩'] roi=[437, 234, 404, 135] | —(仅路由) |
| `_CorridorFromLiminalZone` | OCR['回廊'] roi=[1, 217, 1279, 157] | Click(匹配框中心) |
| `_CorridorNA` | OCR['回'] roi=[1, 217, 1279, 157] | —(仅路由) |
| `_CrisisMissionFromSideQuest` | 模板[BCR/CrisisMission.png] roi=[0, 106, 1280, 498] thr=None | Click(匹配框中心) |
| `_CrisisMissionHead` | 模板[BCR/AtCrisisMission.png] roi=[1122, 0, 142, 130] thr=None | Swipe [188, 155, 1, 1]→[188, 720, 1, 1] d=500 |
| `_CrisisMissionTail` | 模板[BCR/AtCrisisMission.png] roi=[1122, 0, 142, 130] thr=None | Swipe [188, 675, 1, 1]→[188, 100, 1, 1] d=500 |
| `_DailyFromMission` | 模板[Mission/DailyMission.png] roi=[677, 0, 214, 135] thr=None | Click(匹配框中心) |
| `_DailyStaminaBonusNA` | OCR['每日签到'] roi=[94, 87, 198, 131] | —(仅路由) |
| `_DailyStaminaBonusNAFromEvent` | OCR['领取体力'] roi=[88, 112, 182, 542] | StopTask |
| `_DiscFromAppraisal` | OCR['火线特攻'] roi=[0, 401, 1280, 155] | Click(匹配框中心) |
| `_DiscardUnfinishedGame` | — | —(仅路由) |
| `_DustFromPrepared` | 模板[BCR/PreparedDust.png] roi=[43, 60, 1159, 534] thr=0.8 | Click(匹配框中心) |
| `_EagleFromAppraisal` | OCR['铜墙铁壁'] roi=[0, 401, 1280, 155] | Click(匹配框中心) |
| `_EliteMissionFromCrisisMission` | OCR['特级行动'] roi=[167, 40, 180, 124] | Click(匹配框中心) |
| `_EnsureHomepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) |
| `_EnsureTheRoom` | 模板[TheRoom/Ritual.png] roi=[1115, 566, 159, 154] thr=None | —(仅路由) |
| `_EnterGame` | OCR['开始游戏'] roi=[522, 489, 239, 79] | Click(匹配框中心) |
| `_Escape` | — | Click@[318, 36, 1, 1] |
| `_Escape1` | — | Click@[318, 36, 1, 1] |
| `_Escape2` | — | Click@[318, 36, 1, 1] |
| `_Escape3` | — | Click@[318, 36, 1, 1] |
| `_Escape4` | — | Click@[318, 36, 1, 1] |
| `_Escape5` | — | Click@[318, 36, 1, 1] |
| `_Escape6` | — | Click@[318, 36, 1, 1] |
| `_Escape7` | — | Click@[318, 36, 1, 1] |
| `_Escape8` | — | Click@[318, 36, 1, 1] |
| `_Escape9` | — | StopApp |
| `_Escape_Wait` | — | StartApp |
| `_EventFromHome` | 模板[Homepage/Event.png] roi=[121, 79, 59, 60] thr=None | Click(匹配框中心) |
| `_EventLevelFromOngoingMission` | OCR['活动'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_EventLevelNA` | OCR['活动'] roi=[78, 89, 91, 587] | —(仅路由) |
| `_EventSuppliesFromSupplies` | OCR['活动货柜'] roi=[76, 141, 129, 528] | Click(匹配框中心) |
| `_ExitGame` | — | StopApp |
| `_ExitRitual` | 模板[TheRoom/AtRitual.png] roi=[0, 29, 308, 288] thr=None | —(仅路由) |
| `_ExitRitualAgentSelect` | OCR['探员需求'] roi=[187, 0, 197, 129] | —(仅路由) |
| `_ExitTheRoom` | 模板[TheRoom/ExitTheRoom.png] roi=[47, 0, 147, 144] thr=None | Click(匹配框中心) |
| `_ExitTheRoomStorage` | 模板[TheRoom/AtStorage.png] roi=[603, 0, 144, 145] thr=None | —(仅路由) |
| `_ExternalRecruitFromRecruit` | 模板[Recruit/ExternalRecruit.png] roi=[36, 106, 182, 614] thr=None | Click(匹配框中心) |
| `_False` | — | —(仅路由) |
| `_FilmRedeemFromMeritRedeem` | 模板[Supplies/FilmRedeem.png] roi=[190, 615, 354, 105] thr=None | Click(匹配框中心) |
| `_FindCorridorFromLiminalZone` | 模板[BCR/AtLiminalZone.png] roi=[45, 81, 147, 144] thr=None | —(仅路由) |
| `_FindEventLevelFromOngoingMission` | 模板[BCR/AtOngoingMission.png] roi=[0, 66, 467, 114] thr=0.8 | —(仅路由) |
| `_FindExternalRecruitFromRecruit` | OCR['招募规则'] roi=[223, 181, 1057, 493] | —(仅路由) |
| `_FindProtocolFromHome` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) |
| `_FundFromPrepared` | 模板[BCR/PreparedFund.png] roi=[43, 60, 1159, 534] thr=0.8 | Click(匹配框中心) |
| `_G301FromAppraisalLion` | OCR['G301'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_G302FromAppraisalLion` | OCR['G302'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_G401FromAppraisalWolf` | OCR['G401'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_G402FromAppraisalWolf` | OCR['G402'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_G501FromAppraisalEagle` | OCR['G501'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_G502FromAppraisalEagle` | OCR['G502'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_G601FromAppraisalDisc` | OCR['G601'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_G602FromAppraisalDisc` | OCR['G602'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_G603FromAppraisalDisc` | OCR['G603'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_G604FromAppraisalDisc` | OCR['G604'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_HomeButton` | 模板[Utils/HomeButton.png] roi=[245, 0, 148, 143] thr=None | Click(匹配框中心) |
| `_JointBlockadeFromBCR` | OCR['联线封锁'] roi=[152, 612, 187, 108] | Click(匹配框中心) |
| `_LaunchGame` | — | StartApp |
| `_LevelUp` | OCR['行动力恢复'] roi=[827, 207, 207, 133] | Click@[318, 36, 1, 1] |
| `_LiminalZoneFromBCR` | 模板[BCR/LiminalZone.png] roi=[437, 600, 210, 120] thr=None | Click(匹配框中心) |
| `_LiminalZoneHead` | 模板[BCR/AtLiminalZone.png] roi=[45, 81, 147, 144] thr=None | —(仅路由) |
| `_LiminalZoneTail` | 模板[BCR/AtLiminalZone.png] roi=[45, 81, 147, 144] thr=None | —(仅路由) |
| `_LionFromAppraisal` | OCR['虎胆龙威'] roi=[0, 401, 1280, 155] | Click(匹配框中心) |
| `_Loading` | 模板[Utils/Loading.png] roi=[0, 0, 425, 123] thr=None | —(仅路由) |
| `_Login` | 模板[StartUp/Login.png] roi=[495, 431, 291, 129] thr=None | Click(匹配框中心) |
| `_MailboxFromHome` | 模板[Homepage/Mailbox.png] roi=[331, 616, 62, 61] thr=None | Click(匹配框中心) |
| `_MeritRedeemFromSupplies` | OCR['嘉奖兑换', '嘉奖兌换'] roi=[76, 141, 129, 528] | Click(匹配框中心) |
| `_MissionFromHome` | 模板[Homepage/Mission.png] roi=[741, 590, 146, 130] thr=None | Click(匹配框中心) |
| `_MissionFromProtocol` | OCR['任务'] roi=[66, 284, 148, 141] | Click(匹配框中心) |
| `_MutualAidFromUrbanPatrol` | 模板[Mission/MutualAid.png] roi=[922, 596, 237, 124] thr=None | Click(匹配框中心) |
| `_NavigateAppraisal` | OCR['火线特攻', '虎胆龙威', '巅峰时刻', '铜墙铁壁'] roi=[0, 407, 1280, 142] | —(仅路由) |
| `_NavigateAppraisalDisc` | OCR['火线特攻'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateAppraisalEagle` | OCR['铜墙铁壁'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateAppraisalLion` | OCR['虎胆龙威'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateAppraisalWolf` | OCR['巅峰时刻'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateBCR` | OCR['主线故事'] roi=[1080, 607, 200, 113] | —(仅路由) |
| `_NavigateCorridor` | OCR['回廊\\d+区'] roi=[47, 42, 173, 131] | —(仅路由) |
| `_NavigateCrisisMission` | 模板[BCR/AtCrisisMission.png] roi=[1122, 0, 142, 130] thr=0.8 | —(仅路由) |
| `_NavigateDailyMission` | 模板[Mission/AtDailyMission.png] roi=[677, 0, 214, 135] thr=0.8 | —(仅路由) |
| `_NavigateEliteMission` | 模板[BCR/AtEliteMission.png] roi=[0, 66, 467, 114] thr=0.8 | —(仅路由) |
| `_NavigateEvent` | OCR['每日签到'] roi=[94, 87, 198, 131] | —(仅路由) |
| `_NavigateEventLevel` | OCR['活动'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateEventSupplies` | OCR['当期热卖', '活动货品'] roi=[220, 40, 188, 125] | —(仅路由) |
| `_NavigateExternalRecruit` | OCR['外部招募'] roi=[325, 322, 290, 153] | —(仅路由) |
| `_NavigateFilmRedeem` | OCR['胶卷兑换', '胶卷兌换'] roi=[563, 68, 245, 140] | —(仅路由) |
| `_NavigateG301` | 模板[BCR/AtG301.png] roi=[1013, 23, 267, 208] thr=0.8 | —(仅路由) |
| `_NavigateG302` | 模板[BCR/AtG302.png] roi=[1013, 23, 267, 208] thr=0.8 | —(仅路由) |
| `_NavigateG401` | 模板[BCR/AtG401.png] roi=[1013, 23, 267, 208] thr=0.8 | —(仅路由) |
| `_NavigateG402` | 模板[BCR/AtG402.png] roi=[1013, 23, 267, 208] thr=0.8 | —(仅路由) |
| `_NavigateG501` | 模板[BCR/AtG501.png] roi=[1013, 23, 267, 208] thr=0.8 | —(仅路由) |
| `_NavigateG502` | 模板[BCR/AtG502.png] roi=[1013, 23, 267, 208] thr=0.8 | —(仅路由) |
| `_NavigateG601` | 模板[BCR/AtG601.png] roi=[0, 51, 471, 444] thr=None | —(仅路由) |
| `_NavigateG602` | 模板[BCR/AtG602.png] roi=[0, 51, 471, 444] thr=None | —(仅路由) |
| `_NavigateG603` | 模板[BCR/AtG603.png] roi=[0, 51, 471, 444] thr=None | —(仅路由) |
| `_NavigateG604` | 模板[BCR/AtG604.png] roi=[0, 51, 471, 444] thr=None | —(仅路由) |
| `_NavigateHomepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) |
| `_NavigateJointBlockade` | 模板[BCR/AtJointBlockade.png] roi=[1120, 0, 146, 132] thr=None | —(仅路由) |
| `_NavigateLiminalZone` | 模板[BCR/AtLiminalZone.png] roi=[45, 81, 147, 144] thr=0.8 | —(仅路由) |
| `_NavigateMailbox` | 模板[Mailbox/CollectMail.png] roi=[55, 586, 229, 132] thr=None | —(仅路由) |
| `_NavigateMeritRedeem` | OCR['银心奖章'] roi=[228, 36, 189, 132] | —(仅路由) |
| `_NavigateMission` | OCR['任务'] roi=[454, 0, 286, 137] | —(仅路由) |
| `_NavigateMutualAid` | 模板[Mission/AtMutualAid.png] roi=[59, 47, 248, 134] thr=0.8 | —(仅路由) |
| `_NavigateObsoleteNexus` | OCR['废弃枢纽'] roi=[47, 42, 173, 131] | —(仅路由) |
| `_NavigateOngoingMission` | 模板[BCR/AtOngoingMission.png] roi=[0, 66, 467, 114] thr=0.8 | —(仅路由) |
| `_NavigatePrepared` | OCR['公平交易'] roi=[118, 407, 255, 142] | —(仅路由) |
| `_NavigatePreparedDust` | OCR['诡形物语'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigatePreparedFund` | OCR['公平交易'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigatePreparedTape` | OCR['共时性'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateProtocol` | OCR['协议'] roi=[382, 0, 180, 130] | —(仅路由) |
| `_NavigateProtocolMission` | OCR['任务'] roi=[559, 139, 181, 126] | —(仅路由) |
| `_NavigateProtocolReward` | 模板[Protocol/AtProtocolReward.png] roi=[414, 172, 172, 195] thr=0.8 | —(仅路由) |
| `_NavigateProtocolSpecial` | 模板[Protocol/AtProtocolSpecial.png] roi=[927, 135, 184, 133] thr=0.8 | —(仅路由) |
| `_NavigateProtocolWeekly` | 模板[Protocol/AtProtocolWeekly.png] roi=[556, 135, 186, 134] thr=0.8 | —(仅路由) |
| `_NavigateReceptionRoom` | OCR['会客间'] roi=[47, 42, 173, 131] | —(仅路由) |
| `_NavigateRecruit` | OCR['招募规则'] roi=[223, 181, 1057, 493] | —(仅路由) |
| `_NavigateReinforcementSupplies` | OCR['资源礼包'] roi=[220, 40, 188, 125] | —(仅路由) |
| `_NavigateRitual` | 模板[TheRoom/AtRitual.png] roi=[0, 29, 308, 288] thr=0.8 | —(仅路由) |
| `_NavigateRitualSelectAgent` | OCR['探员需求'] roi=[187, 0, 197, 129] | —(仅路由) |
| `_NavigateRitualUseKeys` | OCR['追加档案残片'] roi=[879, 584, 247, 135] | —(仅路由) |
| `_NavigateS001` | OCR['混合体Ⅰ', '混合体I$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS002` | OCR['混合体Ⅱ', '混合体II$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS003` | OCR['混合体Ⅲ', '混合体III$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS101` | OCR['奇点列车Ⅰ', '奇点列车I$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS102` | OCR['奇点列车Ⅱ', '奇点列车II$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS103` | OCR['奇点列车Ⅲ', '奇点列车III$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS201` | OCR['洛伦佐Ⅰ', '洛伦佐I$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS202` | OCR['洛伦佐Ⅱ', '洛伦佐II$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS203` | OCR['洛伦佐Ⅲ', '洛伦佐III$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS301` | OCR['乐园梦魇Ⅰ', '乐园梦魇I$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS302` | OCR['乐园梦魇Ⅱ', '乐园梦魇II$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS303` | OCR['乐园梦魇Ⅲ', '乐园梦魇III$', '乐园梦魔IⅢ'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS401` | OCR['总控一号Ⅰ', '总控一号I$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS402` | OCR['总控一号Ⅱ', '总控一号II$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS501` | OCR['幻影人偶Ⅰ', '幻影人偶I$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS502` | OCR['幻影人偶Ⅱ', '幻影人偶II$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateS701` | OCR['罪与罚'] roi=[821, 70, 240, 115] | —(仅路由) |
| `_NavigateShortTermCheckIn` | OCR['短期支援'] roi=[254, 377, 396, 190] | —(仅路由) |
| `_NavigateSideQuest` | 模板[BCR/CrisisMission.png] roi=[46, 79, 404, 535] thr=None | —(仅路由) |
| `_NavigateSilverMedal` | 模板[Supplies/AtSilverMedal.png] roi=[180, 29, 268, 145] thr=0.8 | —(仅路由) |
| `_NavigateStaminaBonus` | OCR['每日行动'] roi=[419, 24, 446, 170] | —(仅路由) |
| `_NavigateSupplies` | 模板[Supplies/AtSupplies.png] roi=[0, 65, 331, 655] thr=0.8 | —(仅路由) |
| `_NavigateSystem` | 模板[SystemPage/Settings.png] roi=[0, 559, 149, 149] thr=0.8 | —(仅路由) |
| `_NavigateTheRoom` | 模板[TheRoom/Ritual.png] roi=[1115, 566, 159, 154] thr=0.8 | —(仅路由) |
| `_NavigateTheRoomStorage` | 模板[TheRoom/AtStorage.png] roi=[603, 0, 144, 145] thr=0.8 | —(仅路由) |
| `_NavigateUrbanPatrol` | 模板[Mission/AtUrbanPatrol.png] roi=[1053, 0, 219, 136] thr=0.8 | —(仅路由) |
| `_NavigateVioletMedal` | 模板[Supplies/AtVioletMedal.png] roi=[697, 28, 269, 148] thr=0.8 | —(仅路由) |
| `_NavigateWeeklyMission` | 模板[Mission/AtWeeklyMission.png] roi=[867, 0, 209, 131] thr=0.8 | —(仅路由) |
| `_ObsoleteNexusFromLiminalZone` | OCR['废弃枢纽'] roi=[1, 217, 1279, 157] | Click(匹配框中心) |
| `_OngoingMissionFromCrisisMission` | OCR['常驻行动'] roi=[14, 38, 181, 128] | Click(匹配框中心) |
| `_OutOfFilm` | 模板[Utils/Tips.png] roi=[868, 95, 142, 153] thr=None | —(仅路由) |
| `_PreparedFromBCR` | 模板[BCR/Prepared.png] roi=[902, 601, 216, 119] thr=None | Click(匹配框中心) |
| `_ProtocolFromHome` | 模板[Homepage/Protocol.png] roi=[0, 45, 278, 538] thr=None | Click(匹配框中心) |
| `_ProtocolNA` | 模板[Homepage/Protocol.png] roi=[0, 45, 278, 538] thr=None | —(仅路由) |
| `_ReceptionRoomFromLiminalZone` | OCR['会客间'] roi=[1, 217, 1279, 157] | Click(匹配框中心) |
| `_RecruitFromHome` | 模板[['Homepage/Recruit_default.png', 'Homepage/Recruit_compact.png']] roi=[750, 58, 530, 578] thr=None | Click(匹配框中心) |
| `_RecruitHead` | OCR['招募规则'] roi=[223, 181, 1057, 493] | Swipe [127, 163, 1, 1]→[127, 683, 1, 1] d=500 |
| `_RecruitResult` | 模板[['Recruit/RecruitResultR.png', 'Recruit/RecruitResultG.png', 'Recruit/RecruitResultB.png']] roi=[223, 457, 158, 160] thr=None | Click(匹配框中心) |
| `_RecruitTail` | OCR['招募规则'] roi=[223, 181, 1057, 493] | Swipe [127, 683, 1, 1]→[127, 163, 1, 1] d=500 |
| `_ReinforcementSuppliesFromSupplies` | OCR['支援货柜'] roi=[76, 141, 129, 528] | Click(匹配框中心) |
| `_RewardFromProtocol` | OCR['奖', '励'] roi=[65, 203, 148, 134] | Click(匹配框中心) |
| `_RitualFromTheRoom` | 模板[TheRoom/Ritual.png] roi=[1115, 566, 159, 154] thr=None | Click(匹配框中心) |
| `_S001FromOngoingMission` | OCR['S001'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S002FromOngoingMission` | OCR['S002'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S003FromOngoingMission` | OCR['S003'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S101FromOngoingMission` | OCR['S101'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S102FromOngoingMission` | OCR['S102'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S103FromOngoingMission` | OCR['S103'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S201FromOngoingMission` | OCR['S201'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S202FromOngoingMission` | OCR['S202'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S203FromOngoingMission` | OCR['S203'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S301FromOngoingMission` | OCR['S301'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S302FromOngoingMission` | OCR['S302'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S303FromOngoingMission` | OCR['S303'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S401FromEliteMission` | OCR['S401'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S402FromEliteMission` | OCR['S402'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S501FromEliteMission` | OCR['S501'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S502FromEliteMission` | OCR['S502'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_S701FromEliteMission` | OCR['S701'] roi=[78, 89, 91, 587] | Click(匹配框中心) |
| `_SeaOfCognitionReward` | OCR['获取物资'] roi=[380, 30, 520, 190] | Click@[640, 650, 1, 1] |
| `_ServerMaintenance` | OCR['维护'] roi=[485, 227, 311, 133] | —(仅路由) |
| `_ShortTermCheckInFromEvent` | OCR['短期签到'] roi=[88, 112, 182, 542] | Click(匹配框中心) |
| `_ShortTermCheckInNA` | OCR['每日签到'] roi=[94, 87, 198, 131] | —(仅路由) |
| `_ShortTermCheckInNAFromEvent` | OCR['短期签到'] roi=[88, 112, 182, 542] | StopTask |
| `_SideQuestFromBCR` | 模板[BCR/SideQuest.png] roi=[591, 602, 211, 118] thr=None | Click(匹配框中心) |
| `_SilverMedalFromMeritRedeem` | 模板[Supplies/SilverMedal.png] roi=[180, 29, 268, 145] thr=None | Click(匹配框中心) |
| `_SilverMedalHead` | 模板[Supplies/AtSilverMedal.png] roi=[180, 29, 268, 145] thr=None | Swipe [240, 360, 1, 1]→[1270, 360, 1, 1] d=500 |
| `_SilverMedalTail` | 模板[Supplies/AtSilverMedal.png] roi=[180, 29, 268, 145] thr=None | Swipe [1270, 360, 1, 1]→[240, 360, 1, 1] d=500 |
| `_SkipButton` | 模板[Utils/SkipButton.png] roi=[1026, 21, 185, 130] thr=None | Click(匹配框中心) |
| `_SoCGBAbandonConfirm` | OCR['未选择灵感', '放弃激发'] roi=[200, 200, 880, 320] | Click@[760, 520, 1, 1] |
| `_SoCNoTicket` | OCR['入场券不足', '入场券数量不足'] roi=[0, 0, 1280, 720] | —(仅路由) |
| `_SpecialFromProtocolMission` | 模板[Protocol/ProtocolSpecial.png] roi=[927, 135, 184, 133] thr=None | Click(匹配框中心) |
| `_StaminaBonusFromEvent` | OCR['领取体力'] roi=[88, 112, 182, 542] | Click(匹配框中心) |
| `_StartUpLoading` | OCR['加', '载'] roi=[521, 429, 235, 141] | —(仅路由) |
| `_StopTask` | — | StopTask |
| `_StorageFromTheRoom` | 模板[TheRoom/Storage.png] roi=[718, 581, 153, 139] thr=None | Click(匹配框中心) |
| `_SuppliesFromHome` | 模板[['Homepage/Supplies_default.png', 'Homepage/Supplies_compact.png']] roi=[750, 58, 530, 578] thr=None | Click(匹配框中心) |
| `_SweepConfirm` | OCR['出发'] roi=[814, 500, 154, 127] | Click(匹配框中心) |
| `_SweepFromLevel` | OCR['扫荡', '扫汤', '快速完成'] roi=[804, 591, 273, 129] | Click(匹配框中心) |
| `_SweepMax` | 模板[BCR/AtSweep.png] roi=[148, 176, 308, 292] thr=None | Click@[955, 457, 1, 1] |
| `_SweepMin` | 模板[BCR/AtSweep.png] roi=[148, 176, 308, 292] thr=None | Click@[569, 457, 1, 1] |
| `_SystemFromHome` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=None | Click(匹配框中心) |
| `_TapeFromPrepared` | 模板[BCR/PreparedTape.png] roi=[43, 60, 1159, 534] thr=0.8 | Click(匹配框中心) |
| `_TheRoomFromHome` | 模板[['Homepage/TheRoom_default.png', 'Homepage/TheRoom_compact.png']] roi=[750, 58, 530, 578] thr=None | Click(匹配框中心) |
| `_UnfinishedGame` | OCR['未', '完', '成'] roi=[440, 224, 399, 139] | —(仅路由) |
| `_UpdateGame` | OCR['下载'] roi=[323, 161, 628, 344] | —(仅路由) |
| `_UrbanPatrolFromMission` | 模板[Mission/UrbanPatrol.png] roi=[1053, 0, 214, 133] thr=None | Click(匹配框中心) |
| `_UseKeysFromRitual` | OCR['追加档案残片'] roi=[879, 584, 247, 135] | Click(匹配框中心) |
| `_VioletMedalFromMeritRedeem` | 模板[Supplies/VioletMedal.png] roi=[697, 28, 269, 148] thr=None | Click(匹配框中心) |
| `_VioletMedalHead` | 模板[Supplies/AtVioletMedal.png] roi=[697, 28, 269, 148] thr=None | Swipe [240, 360, 1, 1]→[1270, 360, 1, 1] d=500 |
| `_VioletMedalTail` | 模板[Supplies/AtVioletMedal.png] roi=[697, 28, 269, 148] thr=None | Swipe [1270, 360, 1, 1]→[240, 360, 1, 1] d=500 |
| `_Wait2` | — | —(仅路由) |
| `_Wait5` | — | —(仅路由) |
| `_WeeklyFromMission` | 模板[Mission/WeeklyMission.png] roi=[867, 0, 208, 132] thr=None | Click(匹配框中心) |
| `_WeeklyFromProtocolMission` | 模板[Protocol/ProtocolWeekly.png] roi=[556, 135, 186, 134] thr=None | Click(匹配框中心) |
| `_WolfFromAppraisal` | OCR['巅峰时刻'] roi=[0, 401, 1280, 155] | Click(匹配框中心) |
| `~Appraisal` | OCR['火线特攻', '虎胆龙威', '巅峰时刻', '铜墙铁壁'] roi=[0, 407, 1280, 142] | —(仅路由) |
| `~AppraisalDisc` | OCR['火线特攻'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~AppraisalEagle` | OCR['铜墙铁壁'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~AppraisalLion` | OCR['虎胆龙威'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~AppraisalWolf` | OCR['巅峰时刻'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~BCR` | OCR['主线故事'] roi=[1080, 607, 200, 113] | —(仅路由) |
| `~BackButton` | 模板[Utils/BackButton.png] roi=[48, 0, 151, 143] thr=0.8 | —(仅路由) |
| `~Cancel1` | OCR['取消'] roi=[469, 412, 174, 142] | —(仅路由) |
| `~Cancel2` | OCR['取消'] roi=[716, 586, 175, 134] | —(仅路由) |
| `~Cancel3` | OCR['取消'] roi=[465, 590, 150, 130] | —(仅路由) |
| `~CancelGeneral` | 模板[Utils/CancelGeneral.png] roi=[481, 318, 155, 153] thr=None | —(仅路由) |
| `~CloseWindow1` | 模板[Utils/CloseWindow1.png] roi=[1102, 143, 130, 135] thr=None | —(仅路由) |
| `~CloseWindow2` | 模板[Utils/CloseWindow2.png] roi=[1163, 25, 117, 148] thr=None | —(仅路由) |
| `~CloseWindowsGeneral` | 模板[Utils/CloseWindows.png] roi=[1081, 29, 142, 143] thr=None | —(仅路由) |
| `~ConfirmGeneral` | 模板[Utils/ConfirmGeneral.png] roi=[644, 320, 158, 152] thr=None | —(仅路由) |
| `~ConfirmMiddle` | 模板[Utils/ConfirmMiddle.png] roi=[558, 1, 164, 719] thr=None | —(仅路由) |
| `~ConfirmSweepResult` | OCR['确定'] roi=[1014, 611, 162, 109] | —(仅路由) |
| `~Corridor` | OCR['回廊\\d+区'] roi=[47, 42, 173, 131] | —(仅路由) |
| `~CrisisMission` | 模板[BCR/AtCrisisMission.png] roi=[1122, 0, 142, 130] thr=0.8 | —(仅路由) |
| `~DailyMission` | 模板[Mission/AtDailyMission.png] roi=[677, 0, 214, 135] thr=0.8 | —(仅路由) |
| `~DailyStaminaBonus` | OCR['每日行动'] roi=[419, 24, 446, 170] | —(仅路由) |
| `~EliteMission` | 模板[BCR/AtEliteMission.png] roi=[0, 66, 467, 114] thr=0.8 | —(仅路由) |
| `~EnterGame` | OCR['点', '击', '开', '始', '游', '戏'] roi=[522, 489, 239, 79] | —(仅路由) |
| `~Event` | OCR['每日签到'] roi=[94, 87, 198, 131] | —(仅路由) |
| `~EventLevel` | OCR['活动'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~EventSupplies` | OCR['当期热卖', '活动货品'] roi=[220, 40, 188, 125] | —(仅路由) |
| `~ExternalRecruit` | OCR['外部招募'] roi=[325, 322, 290, 153] | —(仅路由) |
| `~ExternalRecruitAcc` | OCR['加速完成'] roi=[524, 177, 231, 137] | —(仅路由) |
| `~ExternalRecruitStart` | OCR['启动招募'] roi=[524, 177, 231, 137] | —(仅路由) |
| `~FilmRedeem` | OCR['胶卷兑换', '胶卷兌换'] roi=[563, 68, 245, 140] | —(仅路由) |
| `~G301` | 模板[BCR/AtG301.png] roi=[1013, 23, 267, 208] thr=0.8 | —(仅路由) |
| `~G302` | 模板[BCR/AtG302.png] roi=[1013, 23, 267, 208] thr=0.8 | —(仅路由) |
| `~G401` | 模板[BCR/AtG401.png] roi=[1013, 23, 267, 208] thr=0.8 | —(仅路由) |
| `~G402` | 模板[BCR/AtG402.png] roi=[1013, 23, 267, 208] thr=0.8 | —(仅路由) |
| `~G501` | 模板[BCR/AtG501.png] roi=[1013, 23, 267, 208] thr=0.8 | —(仅路由) |
| `~G502` | 模板[BCR/AtG502.png] roi=[1013, 23, 267, 208] thr=0.8 | —(仅路由) |
| `~G601` | 模板[BCR/AtG601.png] roi=[0, 51, 471, 444] thr=None | —(仅路由) |
| `~G602` | 模板[BCR/AtG602.png] roi=[0, 51, 471, 444] thr=None | —(仅路由) |
| `~G603` | 模板[BCR/AtG603.png] roi=[0, 51, 471, 444] thr=None | —(仅路由) |
| `~G604` | 模板[BCR/AtG604.png] roi=[0, 51, 471, 444] thr=None | —(仅路由) |
| `~HomeButton` | 模板[Utils/HomeButton.png] roi=[245, 0, 148, 143] thr=0.8 | —(仅路由) |
| `~Homepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) |
| `~JointBlockade` | 模板[BCR/AtJointBlockade.png] roi=[1120, 0, 146, 132] thr=None | —(仅路由) |
| `~JointBlockadeNA` | 模板[BCR/JointBlockadeNA.png] roi=[792, 576, 133, 136] thr=None | —(仅路由) |
| `~LevelNA` | OCR['重复行动'] roi=[804, 591, 273, 129] | —(仅路由) |
| `~LevelUp` | OCR['行动力恢复'] roi=[827, 207, 207, 133] | —(仅路由) |
| `~LiminalZone` | 模板[BCR/AtLiminalZone.png] roi=[45, 81, 147, 144] thr=0.8 | —(仅路由) |
| `~LiminalZoneNA` | 模板[BCR/LiminalZoneNA.png] roi=[859, 585, 140, 135] thr=None | —(仅路由) |
| `~Loading` | 模板[Utils/Loading.png] roi=[0, 0, 425, 123] thr=None | —(仅路由) |
| `~Login` | 模板[StartUp/Login.png] roi=[495, 431, 291, 129] thr=None | —(仅路由) |
| `~Mailbox` | 模板[Mailbox/CollectMail.png] roi=[55, 586, 229, 132] thr=None | —(仅路由) |
| `~MeritRedeem` | OCR['银心奖章'] roi=[228, 36, 189, 132] | —(仅路由) |
| `~Mission` | OCR['任务'] roi=[454, 0, 286, 137] | —(仅路由) |
| `~MutualAid` | 模板[Mission/AtMutualAid.png] roi=[59, 47, 248, 134] thr=0.8 | —(仅路由) |
| `~ObsoleteNexus` | OCR['废弃枢纽'] roi=[47, 42, 173, 131] | —(仅路由) |
| `~OngoingMission` | 模板[BCR/AtOngoingMission.png] roi=[0, 66, 467, 114] thr=0.8 | —(仅路由) |
| `~Prepared` | OCR['公平交易'] roi=[118, 407, 255, 142] | —(仅路由) |
| `~PreparedDust` | OCR['诡形物语'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~PreparedFund` | OCR['公平交易'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~PreparedTape` | OCR['共时性'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~Protocol` | OCR['协议'] roi=[382, 0, 180, 130] | —(仅路由) |
| `~ProtocolMission` | OCR['任务'] roi=[559, 139, 181, 126] | —(仅路由) |
| `~ProtocolReward` | 模板[Protocol/AtProtocolReward.png] roi=[414, 172, 172, 195] thr=0.8 | —(仅路由) |
| `~ProtocolSpecial` | 模板[Protocol/AtProtocolSpecial.png] roi=[927, 135, 184, 133] thr=0.8 | —(仅路由) |
| `~ProtocolWeekly` | 模板[Protocol/AtProtocolWeekly.png] roi=[556, 135, 186, 134] thr=0.8 | —(仅路由) |
| `~ReceptionRoom` | OCR['会客间'] roi=[47, 42, 173, 131] | —(仅路由) |
| `~Recruit` | OCR['招募规则'] roi=[223, 181, 1057, 493] | —(仅路由) |
| `~ReinforcementSupplies` | OCR['资源礼包'] roi=[220, 40, 188, 125] | —(仅路由) |
| `~Ritual` | 模板[TheRoom/AtRitual.png] roi=[0, 29, 308, 288] thr=0.8 | —(仅路由) |
| `~RitualAgentSelect` | OCR['探员需求'] roi=[187, 0, 197, 129] | —(仅路由) |
| `~RitualUseKeys` | 模板[TheRoom/AtUseKeys.png] roi=[432, 195, 136, 135] thr=0.8 | —(仅路由) |
| `~S001` | OCR['混合体Ⅰ', '混合体I$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S002` | OCR['混合体Ⅱ', '混合体II$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S003` | OCR['混合体Ⅲ', '混合体III$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S101` | OCR['奇点列车Ⅰ', '奇点列车I$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S102` | OCR['奇点列车Ⅱ', '奇点列车II$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S103` | OCR['奇点列车Ⅲ', '奇点列车III$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S201` | OCR['洛伦佐Ⅰ', '洛伦佐I$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S202` | OCR['洛伦佐Ⅱ', '洛伦佐II$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S203` | OCR['洛伦佐Ⅲ', '洛伦佐III$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S301` | OCR['乐园梦魇Ⅰ', '乐园梦魇I$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S302` | OCR['乐园梦魇Ⅱ', '乐园梦魇II$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S303` | OCR['乐园梦魇Ⅲ', '乐园梦魇III$', '乐园梦魔IⅢ'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S401` | OCR['总控一号Ⅰ', '总控一号I$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S402` | OCR['总控一号Ⅱ', '总控一号II$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S501` | OCR['幻影人偶Ⅰ', '幻影人偶I$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S502` | OCR['幻影人偶Ⅱ', '幻影人偶II$'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~S701` | OCR['罪与罚'] roi=[821, 70, 240, 115] | —(仅路由) |
| `~ShortTermCheckIn` | OCR['短期支援'] roi=[254, 377, 396, 190] | —(仅路由) |
| `~SideQuest` | 模板[BCR/CrisisMission.png] roi=[46, 79, 404, 535] thr=None | —(仅路由) |
| `~SilverMedal` | 模板[Supplies/AtSilverMedal.png] roi=[180, 29, 268, 145] thr=0.8 | —(仅路由) |
| `~SkipButton` | 模板[Utils/SkipButton.png] roi=[1026, 21, 185, 130] thr=None | —(仅路由) |
| `~StartUpLoading` | OCR['加', '载'] roi=[521, 429, 235, 141] | —(仅路由) |
| `~Supplies` | 模板[Supplies/AtSupplies.png] roi=[0, 65, 331, 655] thr=0.8 | —(仅路由) |
| `~Sweep` | 模板[BCR/AtSweep.png] roi=[148, 176, 308, 292] thr=None | —(仅路由) |
| `~System` | 模板[SystemPage/Settings.png] roi=[0, 559, 149, 149] thr=0.8 | —(仅路由) |
| `~TheRoom` | 模板[TheRoom/Ritual.png] roi=[1115, 566, 159, 154] thr=0.8 | —(仅路由) |
| `~TheRoomStorage` | 模板[TheRoom/AtStorage.png] roi=[603, 0, 144, 145] thr=0.8 | —(仅路由) |
| `~UrbanPatrol` | 模板[Mission/AtUrbanPatrol.png] roi=[1053, 0, 219, 136] thr=0.8 | —(仅路由) |
| `~VioletMedal` | 模板[Supplies/AtVioletMedal.png] roi=[697, 28, 269, 148] thr=0.8 | —(仅路由) |
| `~WeeklyMission` | 模板[Mission/AtWeeklyMission.png] roi=[867, 0, 209, 131] thr=0.8 | —(仅路由) |
| `~已切换到往期活动` | 模板[往期活动/往期活动标志.png] roi=[47, 65, 484, 89] thr=0.85 | —(仅路由) |
| `~已切换到往期活动_重试2` | 模板[往期活动/往期活动标志.png] roi=[47, 65, 484, 89] thr=0.85 | —(仅路由) |
| `~已切换到往期活动_重试3` | 模板[往期活动/往期活动标志.png] roi=[47, 65, 484, 89] thr=0.85 | —(仅路由) |
| `~战斗失败_条件` | 模板[自动推图/战斗失败条件.png] roi=[1088, 203, 122, 153] thr=0.8 | —(仅路由) |
| `~战斗失败_标题` | OCR['战斗失败'] roi=[855, 110, 430, 160] | —(仅路由) |
| `~战斗失败_退出` | 模板[自动推图/战斗失败退出.png] roi=[957, 598, 257, 64] thr=0.8 | —(仅路由) |
| `~战斗界面已加载` | 模板[自动推图/auto.png] roi=[790, 10, 140, 80] thr=0.7 | —(仅路由) |
| `~战斗胜利_战利品` | 模板[自动推图/战斗胜利战利品.png] roi=[1086, 409, 166, 71] thr=0.8 | —(仅路由) |
| `~战斗胜利_标题` | OCR['战斗胜利'] roi=[873, 114, 401, 280] | —(仅路由) |
| `~等待快速完成结果` | OCR['快速完成结果'] roi=[0, 0, 1280, 720] | —(仅路由) |
| `~识别往日行动调令` | OCR['[0-6]'] roi=[351, 92, 173, 48] | —(仅路由) |
| `~调令为零` | Custom | —(仅路由) |
| `~进入编队选择` | 模板[自动推图/编队选择关闭.png] roi=[1085, 39, 95, 98] thr=0.85 | —(仅路由) |
| `处理战斗失败` | DirectHit(必中) | Custom[播报进度] |
| `巡检关卡` | DirectHit(必中) | —(仅路由) |
| `巡检出发` | DirectHit(必中) | —(仅路由) |
| `巡检出发2` | DirectHit(必中) | —(仅路由) |
| `巡检出发3` | DirectHit(必中) | —(仅路由) |
| `巡检出发4` | DirectHit(必中) | —(仅路由) |
| `巡检编队` | DirectHit(必中) | —(仅路由) |
| `当期活动` | — | —(仅路由) |
| `往左滑动` | — | Swipe [1270, 368, 1, 1]→[10, 368, 1, 1] d=500 |
| `往左滑动2` | — | Swipe [1270, 368, 1, 1]→[10, 368, 1, 1] d=500 |
| `往左滑动3` | — | Swipe [1270, 368, 1, 1]→[10, 368, 1, 1] d=500 |
| `往期活动` | — | —(仅路由) |
| `推图完成` | DirectHit(必中) | Custom[播报进度] |
| `播报前提` | DirectHit(必中) | Custom[播报进度] |
| `播报开始` | DirectHit(必中) | Custom[播报进度] |
| `播报未满星` | DirectHit(必中) | Custom[播报进度] |
| `播报胜利` | DirectHit(必中) | Custom[播报进度] |
| `无往日行动调令结束` | DirectHit(必中) | —(仅路由) |
| `点击关闭编队` | 模板[自动推图/编队选择关闭.png] roi=[1085, 39, 95, 98] thr=0.85 | Click(匹配框中心) |
| `点击关闭编队_重试` | 模板[自动推图/编队选择关闭.png] roi=[1085, 39, 95, 98] thr=0.85 | Click(匹配框中心) |
| `点击出发` | OCR['出发'] roi=[740, 480, 400, 165] | Click(匹配框中心) |
| `点击开始作战` | 模板[自动推图/开始作战.png] roi=[1036, 593, 197, 111] thr=0.85 | Click(匹配框中心) |
| `点击往期活动` | 模板[往期活动/往期活动.png] roi=[421, 0, 859, 154] thr=0.85 | Click(匹配框中心) |
| `点击往期活动_重试2` | 模板[往期活动/往期活动.png] roi=[421, 0, 859, 154] thr=0.85 | Click(匹配框中心) |
| `点击往期活动_重试3` | 模板[往期活动/往期活动.png] roi=[421, 0, 859, 154] thr=0.85 | Click(匹配框中心) |
| `点击快速完成` | OCR['快速完成'] roi=[700, 600, 400, 120] | Click(匹配框中心) |
| `点击未满星结算` | 模板[自动推图/战斗未满星结算.png] roi=[804, 406, 451, 234] thr=0.8 | Click(匹配框中心) |
| `点击确定` | OCR['确定', '确认退出'] roi=[940, 600, 340, 120] | Click(匹配框中心) |
| `点击自动战斗` | 模板[自动推图/auto.png] roi=[790, 10, 140, 80] thr=0.7 | Click(匹配框中心) |
| `点击自动确认` | 模板[自动推图/自动战斗确认.png] roi=[425, 220, 410, 231] thr=0.8 | Click(匹配框中心) |
| `点击自动确认_重试` | 模板[自动推图/自动战斗确认.png] roi=[425, 220, 410, 231] thr=0.8 | Click(匹配框中心) |
| `点击跳过介绍` | DirectHit(必中) | Click@[1218, 273, 1, 1] |
| `等待战斗结束` | DirectHit(必中) | —(仅路由) |
| `等待战斗结束_间隔` | DirectHit(必中) | —(仅路由) |
| `等待编队出现` | DirectHit(必中) | —(仅路由) |
| `编队调整检测` | 模板[自动推图/编队调整_文字.png] roi=[1000, 439, 304, 132] thr=0.7 | Click(匹配框中心) |
| `自动战斗已开启` | DirectHit(必中) | —(仅路由) |
| `行动力判定` | OCR['时'] roi=[454, 189, 608, 165] | Click+offset[0, 70, 0, 0] |
| `行动次数确定` | OCR['快速完成次数'] roi=[640, 365, 240, 40] | Click@[955, 457, 1, 1] |
| `记录往日行动调令数` | OCR[] roi=[351, 92, 173, 48] | Custom[记录往日行动调令数] |
| `设置往期活动战斗次数` | DirectHit(必中) | Custom[设置往期活动战斗次数] |
| `识别出发` | OCR['出发'] roi=[784, 588, 496, 149] | Click(匹配框中心) |
| `识别出发失败处理` | DirectHit(必中) | Custom[存失败截图] |
| `识别未完成关卡` | 模板[自动推图/未完成关卡.png] roi=[0, 0, 1280, 720] thr=0.8 | Click(匹配框中心) |
| `返回主界面` | 模板[当期活动/主界面图标.png] roi=[11, 2, 413, 84] thr=0.85 | Click(匹配框中心) |
| `返回主界面_往期活动失败` | 模板[当期活动/主界面图标.png] roi=[11, 2, 413, 84] thr=0.85 | Click(匹配框中心) |
| `进入作战` | OCR['作战'] roi=[850, 300, 360, 200] | Click(匹配框中心) |
| `进入往期活动内部流程` | DirectHit(必中) | —(仅路由) |
| `进入活动页` | OCR['剩余'] roi=[1045, 212, 240, 194] | Click(匹配框中心) |
| `进入该往期活动事件` | DirectHit(必中) | —(仅路由) |
| `进入该往期活动事件_未适配` | DirectHit(必中) | —(仅路由) |
| `连点退出并重扫` | DirectHit(必中) | Custom[连点退出] |
| `退出关卡详情页` | 模板[当期活动/主界面图标.png] roi=[11, 2, 413, 84] thr=0.85 | Click(匹配框中心) |
| `退出往期活动失败` | 模板[当期活动/主界面图标.png] roi=[11, 2, 413, 84] thr=0.85 | Click(匹配框中心) |
| `选择公馆之夜` | 模板[往期活动/处理时间奇物的三项建议公馆之夜.png] roi=[930, 330, 320, 165] thr=0.8 | Click(匹配框中心) |
| `选择关卡` | OCR['被诅咒的信仰'] roi=[870, 350, 380, 230] | Click(匹配框中心) |
| `选择出战队伍` | 模板[自动推图/战斗编队1.png] roi=[166, 350, 146, 80] thr=0.85 | Click+offset[799, 0, 0, 0] |
| `选择出战队伍_失败停止` | DirectHit(必中) | —(仅路由) |
| `选择出战队伍_重试` | 模板[自动推图/战斗编队1.png] roi=[166, 350, 146, 80] thr=0.85 | Click+offset[799, 0, 0, 0] |
| `选择囚徒关卡` | 模板[往期活动/囚徒困境PD110.png] roi=[0, 0, 1280, 720] thr=0.8 | Click(匹配框中心) |
| `选择回忆录关卡` | 模板[往期活动/写给昨日的回忆录MY205.png] roi=[0, 0, 1280, 720] thr=0.8 | Click(匹配框中心) |
| `选择回忆重现` | 模板[往期活动/写给昨日的回忆录回忆重现.png] roi=[857, 423, 356, 162] thr=0.8 | Click(匹配框中心) |
| `选择困境迷途` | 模板[往期活动/囚徒困境困境迷途.png] roi=[831, 428, 213, 260] thr=0.8 | Click(匹配框中心) |
| `选择大玩家关卡` | 模板[往期活动/校园大玩家SR12.png] roi=[0, 0, 1280, 720] thr=0.8 | Click(匹配框中心) |
| `选择奇物关卡` | 模板[往期活动/处理时间奇物的三项建议TB112.png] roi=[0, 0, 1280, 720] thr=0.8 | Click(匹配框中心) |
| `选择小关卡` | OCR['SL11[0O]'] roi=[0, 0, 1280, 720] | Click(匹配框中心) |
| `选择往期活动` | 模板[往期活动/在月光之下.png] roi=[0, 147, 1280, 442] thr=0.8 | Click(匹配框中心) |
| `选择往期活动_重试2` | 模板[往期活动/在月光之下.png] roi=[0, 147, 1280, 442] thr=0.8 | Click(匹配框中心) |
| `选择往期活动_重试3` | 模板[往期活动/在月光之下.png] roi=[0, 147, 1280, 442] thr=0.8 | Click(匹配框中心) |
| `选择往期活动_重试4` | 模板[往期活动/在月光之下.png] roi=[0, 147, 1280, 442] thr=0.8 | Click(匹配框中心) |
| `选择新手` | 模板[往期活动/校园大玩家新手.png] roi=[945, 366, 210, 211] thr=0.8 | Click(匹配框中心) |
| `选择月光关卡` | 模板[往期活动/在月光之下IM112.png] roi=[0, 0, 1280, 720] thr=0.8 | Click(匹配框中心) |
| `选择笑笑关卡` | 模板[往期活动/笑笑小剧场FV104.png] roi=[469, 390, 147, 191] thr=0.8 | Click(匹配框中心) |
| `选择谜案回首关卡` | 模板[往期活动/谜案回首GB112.png] roi=[0, 0, 1280, 720] thr=0.8 | Click(匹配框中心) |
| `选择迷城之下` | 模板[往期活动/在月光之下迷城之下.png] roi=[1061, 345, 199, 309] thr=0.8 | Click(匹配框中心) |
| `选择首演` | 模板[往期活动/谜案回首首演.png] roi=[1080, 470, 200, 230] thr=0.8 | Click(匹配框中心) |