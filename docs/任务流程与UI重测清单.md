# MaaEOV 任务流程梳理与 UI 变更重测清单

> 自动生成自 `resource/base/pipeline/` 下 21 个流水线文件（`scripts/gen_flow_doc.py`，**请勿手改本文档**；改 pipeline 后重跑生成器，CI 会校验同步）。

> 基准分辨率：1280×720。所有坐标、ROI 均为该基准下的像素值，UI 改版后需逐项复核。

> 共解析到 **15** 个任务入口、**609** 个节点。

## 公共约定（所有任务共用）

- 每个节点的 `next` 列表中，以 `[JumpBack]_XXX` 开头的是**中断/弹窗保底处理**（服务器维护、断线重连、升级弹窗、领奖等），不属正常流程，故下方流程表默认只列**主链路**（`next` 首项）。
- `DirectHit` 节点**必定命中**，多用于「路由/播报/兜底」；`TemplateMatch`/`OCR` 节点按识别结果决定是否执行、再到 `next`。
- **UI 重测重点**：流程表里「识别」列即该步的 UI 依赖——模板图片需重新截图、OCR 文案需逐字核对、坐标需重新定位。任一变更都会导致该节点识别失败、任务卡死或错点。
- 同一节点跨任务复用时只在首次出现处展开，其余位置标 ↺；被多个任务复用的节点单独汇总在文末（改一处影响多处，需一并回归）。

---

## `#StartUp`（启动游戏）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `StartUp` | — | —(仅路由) | `~Homepage` / `_LaunchGame` |
| &nbsp;&nbsp;1 | `~Homepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | （结束） |
| &nbsp;&nbsp;1 | `_LaunchGame` | — | StartApp | `_NavigateHomepage` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `_NavigateHomepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | `_EnsureHomepage` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `_EnsureHomepage` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | `~Homepage` / `_NavigateHomepage` |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_NavigateHomepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_UpdateGame`, `[JumpBack]_UnfinishedGame`, `[JumpBack]_ConfirmExitTheRoom`, `[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfirmReconnect`, `[JumpBack]_CancelGeneral`, `[JumpBack]_Cancel1`, `[JumpBack]_Cancel2`, `[JumpBack]_Cancel3`, `[JumpBack]_Cancel4`, `[JumpBack]_ConfirmGeneral`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]_ConfirmSweepResult`, `[JumpBack]_CloseWindowsGeneral`, `[JumpBack]_CloseWindow1`, `[JumpBack]_CloseWindow2`, `[JumpBack]_SkipButton`, `[JumpBack]_LevelUp`, `[JumpBack]_HomeButton`, `[JumpBack]_BackButton`, `[JumpBack]_Login`, `[JumpBack]_EnterGame`, `[JumpBack]_ExitTheRoom`, `[JumpBack]_Loading`, `[JumpBack]_StartUpLoading`, `[JumpBack]_Escape`


## `#活动领取`（活动领取）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `活动领取` | — | —(仅路由) | `Mailbox` |
| &nbsp;&nbsp;1 | `Mailbox` | — | —(仅路由) | `_EventGateMail` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `_EventGateMail` | — | —(仅路由) | `CollectMail` / `_EventGateStamina` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `CollectMail` | 模板[Mailbox/CollectMail.png] roi=[55, 586, 229, 132] | Click | `_EventGateStamina` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `_EventGateStamina` | — | —(仅路由) | `DailyStaminaBonus` / `_EventGateShortTerm` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `DailyStaminaBonus` | — | —(仅路由) | `CollectStaminaBonusNoon` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `CollectStaminaBonusNoon` | OCR['每日行动'] roi=[419, 24, 446, 170] | Click@[431, 584, 1, 1] | `CollectStaminaBonusEvening` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `CollectStaminaBonusEvening` | OCR['每日行动'] roi=[419, 24, 446, 170] | Click@[708, 582, 1, 1] | `_EventGateShortTerm` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `_EventGateShortTerm` | — | —(仅路由) | `ShortTermCheckIn` / `_EventDone` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `ShortTermCheckIn` | — | —(仅路由) | `CollectShortTermCheckIn` / `_ShortTermCheckInDone` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `CollectShortTermCheckIn` | OCR['点击领取'] roi=[1035, 117, 179, 547] | Click | `~TaskExit` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;11 | `~TaskExit` | DirectHit | —(仅路由) | `~Homepage` |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `_ShortTermCheckInDone` | OCR['短期支援'] roi=[254, 377, 396, 190] | —(仅路由) | `~TaskExit` |
| · | `~TaskExit` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `_EventDone` | — | —(仅路由) | `~TaskExit` |
| · | `~TaskExit` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_EventGateShortTerm` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_EventGateStamina` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_NavigateHomepage`, `[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfirmReconnect`, `[JumpBack]_NavigateShortTermCheckIn`, `[JumpBack]_NavigateStaminaBonus`, `[JumpBack]_NavigateMailbox`


## `#JointBlockade`（联线封锁）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `JointBlockade` | — | —(仅路由) | `JointBlockadeCompleteFromSystem` / `JointBlockadeFromSystem` |
| &nbsp;&nbsp;1 | `JointBlockadeCompleteFromSystem` | OCR['108/108'] roi=[0, 483, 168, 128] | —(仅路由) | `~TaskExit` |
| · | `~TaskExit` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;1 | `JointBlockadeFromSystem` | OCR['联线封锁'] roi=[0, 458, 189, 128] | Click | `~JointBlockadeNA` / `JointBlockadeCompleteFromLevel` / `JointBlockadeTicketsCompleteFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `~JointBlockadeNA` | 模板[BCR/JointBlockadeNA.png] roi=[792, 576, 133, 136] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `JointBlockadeCompleteFromLevel` | OCR['108/108'] roi=[106, 554, 218, 135] | —(仅路由) | `~TaskExit` |
| · | `~TaskExit` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `JointBlockadeTicketsCompleteFromLevel` | OCR['^0'] roi=[1161, 0, 119, 92] | —(仅路由) | `~TaskExit` |
| · | `~TaskExit` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfirmReconnect`, `[JumpBack]ConfirmDiscardJointBlockadeUnfinishedGame`, `[JumpBack]_ConfirmJointBlockadeResult`, `[JumpBack]_SweepConfirm`, `[JumpBack]_SweepFromLevel`, `[JumpBack]JointBlockadeUnfinishedGame`, `[JumpBack]_NavigateJointBlockade`, `[JumpBack]_NavigateSystem`


## `#SeaOfCognition`（认知海域）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `SeaOfCognition` | — | —(仅路由) | `SoCResume` |
| &nbsp;&nbsp;1 | `SoCResume` | DirectHit | —(仅路由) | `_SoCAbandonDive` / `_SoCScoreFull` / `SoCClaim` / `SoCContinue` / `SoCStartBattle` / `SoCInBattleBuff` / `SoCInBattleBuffOCR` / `SoCInspirationNode` / `SoCInspirationNodeOCR` / `SoCState_GB1` / `SoCState_GB0` / `_SoCTicketLowNoFree` / `_SoCTicketLow` / `SoCStartDive` / `SoCContinueDive` / `SoCTicketGateFree` / `SoCDeepDive` / `SoCDeepDiveFree` / `SoCFallbackStart` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `_SoCAbandonDive` | OCR['[终終][止比]下[潜潛]'] roi=[790, 595, 440, 80] | Click | `_SoCAbandonConfirm` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `_SoCAbandonConfirm` | OCR['放弃本次探索', '是否放弃'] roi=[200, 250, 880, 120] | Click@[732, 407, 1, 1] | `_SoCAbandonResult` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `_SoCAbandonResult` | OCR['探索[终終]止', '完成节点', '完成節點'] roi=[0, 0, 1280, 720] | Click@[640, 360, 1, 1] | `_SoCScoreFull` / `_SoCBattleFailStop` / `SoCSelectLayer` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `_SoCScoreFull` | OCR['1000\\s*/\\s*1000', '1000/1000', '1000／1000'] roi=[20, 630, 250, 82] | —(仅路由) | `_SoCReturnHome` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `_SoCReturnHome` | — | —(仅路由) | `~SoCHome` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `~SoCHome` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | `SoCDone` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `SoCDone` | DirectHit | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `_SoCBattleFailStop` | Custom['SoCBattleFailGiveUp'] | DoNothing | `_SoCReturnHome` |
| · | `_SoCReturnHome` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `SoCSelectLayer` | OCR['[梦夢][渊淵][层層]'] roi=[0, 0, 1280, 720] | Click | `_SoCAbandonDive` / `_SoCTicketLowNoFree` / `_SoCTicketLow` / `_SoCScoreFull` / `SoCStartDive` / `SoCContinueDive` |
| · | `_SoCAbandonDive` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `_SoCTicketLowNoFree` | Custom['SoCTicketLowNoFree'] | —(仅路由) | `_SoCReturnHome` |
| · | `_SoCReturnHome` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `_SoCTicketLow` | Custom['SoCTicketLow'] | —(仅路由) | `_SoCReturnHome` |
| · | `_SoCReturnHome` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_SoCScoreFull` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `SoCStartDive` | OCR['开始下[潜潛]'] roi=[820, 545, 460, 175] | Click | `SoCResume` / `SoCDeepDive` / `SoCDeepDiveFree` / `SoCDeepDiveFallback` |
| · | `SoCResume` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `SoCDeepDive` | OCR['深[潜潛]指引'] roi=[0, 0, 1280, 720] | Click | `SoCTeamEnter` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `SoCTeamEnter` | 模板[SeaOfCognition/进入海域.png] roi=[0, 0, 1280, 720] thr=0.8 | Click | `SoCInspirationNode` / `SoCInspirationNodeOCR` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `SoCInspirationNode` | 模板[SeaOfCognition/认知海域灵感节点.png] roi=[192, 159, 358, 556] thr=0.8 | —(仅路由) | `SoCInspirationClick` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `SoCInspirationClick` | OCR['[灵靈]感[节節][点點]'] roi=[0, 0, 1280, 720] | Click | `SoCGBLoop` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;11 | `SoCGBLoop` | — | —(仅路由) | `SoCGBPickAvailable` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;12 | `SoCGBPickAvailable` | DirectHit | Custom['SoCGBPickAvailable'] | `SoCGBContinue` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `SoCGBContinue` | 模板[SeaOfCognition/BuffContinue.png] roi=[450, 600, 380, 100] thr=0.8 | Click | `SoCInBattleBuff` / `SoCInBattleBuffOCR` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;14 | `SoCInBattleBuff` | 模板[SeaOfCognition/局内buff选择.png] roi=None thr=0.8 | Custom['SoCPickInBattleBuff'] | `SoCInBattleBuffConfirm` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;15 | `SoCInBattleBuffConfirm` | 模板[SeaOfCognition/QiFa.png] roi=None thr=0.8 | Click | `SoCStartBattle` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;16 | `SoCStartBattle` | 模板[SeaOfCognition/认知海域开始作战.png] roi=None thr=0.8 | Click | `SoCAutoBattle` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;17 | `SoCAutoBattle` | DirectHit | Custom['SoCAwaitBattle'] | `_SoCBackToLayer` / `SoCContinue` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;18 | `_SoCBackToLayer` | OCR['开始下[潜潛]', '继续下[潜潛]', '繼續下[潜潛]', '開始下[潜潛]'] roi=[820, 545, 460, 175] | —(仅路由) | `_SoCScoreFull` / `_SoCTicketLowNoFree` / `_SoCTicketLow` / `SoCStartDive` |
| · | `_SoCScoreFull` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_SoCTicketLowNoFree` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_SoCTicketLow` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCStartDive` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;18 | `SoCContinue` | 模板[SeaOfCognition/战斗完成继续.png] roi=[950, 600, 330, 120] thr=0.8 | Click | `SoCAfterContinue` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;19 | `SoCAfterContinue` | DirectHit | —(仅路由) | `SoCState_GB1` / `SoCState_GB0` / `SoCNodeLoop` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;20 | `SoCState_GB1` | OCR['剩余可选灵感'] roi=[400, 560, 500, 110] | —(仅路由) | `SoCGBSwipe` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;21 | `SoCGBSwipe` | DirectHit | Swipe | `SoCGBLoop` |
| · | `SoCGBLoop` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;20 | `SoCState_GB0` | 模板[SeaOfCognition/剩余可选灵感0.png] roi=None thr=0.8 | —(仅路由) | `SoCGBLoop` |
| · | `SoCGBLoop` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;20 | `SoCNodeLoop` | — | —(仅路由) | `SoCInBattleBuff` / `SoCInBattleBuffOCR` / `SoCContinue` / `SoCClaim` / `_SoCBackToLayer` |
| · | `SoCInBattleBuff` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;21 | `SoCInBattleBuffOCR` | OCR['请选择一个短暂灵感'] roi=[490, 125, 320, 55] | Custom['SoCPickInBattleBuff'] | `SoCInBattleBuffConfirm` |
| · | `SoCInBattleBuffConfirm` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCContinue` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;21 | `SoCClaim` | OCR['[领領]取', '[确確][认認]'] roi=[0, 0, 1280, 720] | Click | `SoCAtBCR` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;22 | `SoCAtBCR` | OCR['[终終]局行动', '[终終]局行動'] roi=[420, 630, 300, 90] | Click | `SoCEntryCognition` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;23 | `SoCEntryCognition` | OCR['进入', '進入'] roi=[430, 555, 270, 120] | Click | `_SoCNoticeClose` / `_SoCRewardPanelClose` / `_SoCTicketLowNoFree` / `_SoCTicketLow` / `_SoCScoreFull` / `SoCSelectLayer` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;24 | `_SoCNoticeClose` | OCR['奖励已更新', '認知海域奖励', '认知海域奖励'] roi=[300, 180, 700, 150] | Click@[646, 391, 1, 1] | `_SoCRewardPanelClose` / `SoCSelectLayer` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;25 | `_SoCRewardPanelClose` | OCR['奖励倒计时', '奖励倒計時'] roi=[300, 190, 500, 70] | Click@[1177, 214, 1, 1] | `SoCSelectLayer` |
| · | `SoCSelectLayer` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCSelectLayer` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_SoCRewardPanelClose` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_SoCTicketLowNoFree` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_SoCTicketLow` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_SoCScoreFull` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCSelectLayer` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_SoCBackToLayer` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInBattleBuffOCR` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `SoCInspirationNodeOCR` | OCR['[灵靈]感[节節][点點]'] roi=[192, 159, 358, 556] | —(仅路由) | `SoCInspirationClick` |
| · | `SoCInspirationClick` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `SoCDeepDiveFree` | OCR['自由探索', '自由', '探索'] roi=[0, 0, 1280, 720] | Click | `SoCTeamEnter` |
| · | `SoCTeamEnter` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `SoCDeepDiveFallback` | DirectHit | Click@[351, 581, 1, 1] | `SoCTeamEnter` |
| · | `SoCTeamEnter` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `SoCContinueDive` | 模板[SeaOfCognition/认知海域继续下潜.png] roi=[820, 545, 460, 175] thr=0.8 | Click | `SoCInspirationNode` / `SoCInspirationNodeOCR` / `SoCState_GB1` / `SoCState_GB0` / `SoCInBattleBuff` / `SoCInBattleBuffOCR` / `SoCStartBattle` / `SoCClaim` / `SoCContinue` / `SoCInspirationFallback` |
| · | `SoCInspirationNode` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInspirationNodeOCR` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCState_GB1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCState_GB0` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInBattleBuff` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInBattleBuffOCR` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCStartBattle` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCClaim` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCContinue` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `SoCInspirationFallback` | DirectHit | Click@[351, 581, 1, 1] | `SoCInBattleBuff` / `SoCInBattleBuffOCR` |
| · | `SoCInBattleBuff` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInBattleBuffOCR` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_SoCScoreFull` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCClaim` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCContinue` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCStartBattle` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInBattleBuff` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInBattleBuffOCR` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInspirationNode` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCInspirationNodeOCR` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCState_GB1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCState_GB0` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_SoCTicketLowNoFree` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_SoCTicketLow` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCStartDive` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCContinueDive` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `SoCTicketGateFree` | Custom['SoCTicketFreeGate'] | DoNothing | `SoCDeepDiveFree` |
| · | `SoCDeepDiveFree` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCDeepDive` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `SoCDeepDiveFree` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `SoCFallbackStart` | DirectHit | —(仅路由) | `SoCAtBCR` |
| · | `SoCAtBCR` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_NavigateHomepage`, `[JumpBack]_CancelGeneral`, `[JumpBack]_CloseWindowsGeneral`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfirmReconnect`, `[JumpBack]_LevelUp`, `[JumpBack]_SeaOfCognitionReward`, `[JumpBack]_NavigateBCR`, `[JumpBack]_CloseWindows`, `[JumpBack]_SoCGBAbandonConfirm`, `[JumpBack]_SoCNoTicket`


## `#LiminalZone`（阈限禁区）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `LiminalZone` | — | —(仅路由) | `LiminalZoneCompletedFromSystem` / `LiminalZoneFromSystem` |
| &nbsp;&nbsp;1 | `LiminalZoneCompletedFromSystem` | OCR['480/480'] roi=[199, 312, 223, 128] | —(仅路由) | `~TaskExit` |
| · | `~TaskExit` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;1 | `LiminalZoneFromSystem` | 模板[SystemPage/Settings.png] roi=[0, 559, 149, 149] | Click@[337, 362, 1, 1] | `SelectLevelFromLiminalZone` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `SelectLevelFromLiminalZone` | 模板[BCR/阈限禁区_界面标志.png] roi=[45, 81, 147, 144] | —(仅路由) | `~LiminalZoneNA` / `LiminalZoneSelectLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `~LiminalZoneNA` | 模板[BCR/LiminalZoneNA.png] roi=[859, 585, 140, 135] | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `LiminalZoneSelectLevel` | — | —(仅路由) | `_NavigateObsoleteNexus` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `_NavigateObsoleteNexus` | — | —(仅路由) | `~ObsoleteNexus` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `~ObsoleteNexus` | OCR['废弃枢纽'] roi=[40, 75, 320, 70] | —(仅路由) | `LiminalZoneFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `LiminalZoneFromLevel` | OCR['扫荡', '扫汤'] roi=[804, 591, 273, 129] | —(仅路由) | `_CancelLiminalZoneOverflow` / `LiminalZoneCompletedFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `_CancelLiminalZoneOverflow` | OCR['进行探索', '回收物'] roi=[222, 225, 834, 136] | —(仅路由) | `_Cancel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `_Cancel` | — | —(仅路由) | `_CancelGeneral` / `_Cancel1` / `_Cancel2` / `_Cancel3` / `_Cancel4` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `_CancelGeneral` | 模板[Utils/CancelGeneral.png] roi=[481, 318, 155, 153] | Click | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `_Cancel1` | OCR['取消'] roi=[469, 412, 174, 142] | Click | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `_Cancel2` | OCR['取消'] roi=[716, 586, 175, 134] | Click | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `_Cancel3` | OCR['取消'] roi=[465, 590, 150, 130] | Click | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `_Cancel4` | OCR['取消'] roi=[574, 448, 162, 125] | Click | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `LiminalZoneCompletedFromLevel` | OCR['480/480'] roi=[92, 620, 225, 100] | —(仅路由) | `~TaskExit` |
| · | `~TaskExit` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfirmReconnect`, `[JumpBack]_ConfirmLiminalZoneResult`, `[JumpBack]LiminalZoneOutOfStamina`, `[JumpBack]_LevelUp`, `[JumpBack]_SweepMax`, `[JumpBack]_SweepFromLevel`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]_LiminalZoneBackToSelect`, `[JumpBack]_ObsoleteNexusFromLiminalZone`, `[JumpBack]_LiminalZoneHead`, `[JumpBack]_NavigateLiminalZone`, `[JumpBack]_NavigateSystem`


## `#TheRoom`（事务所（解读仪式））

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `TheRoom` | — | —(仅路由) | `Ritual` |
| &nbsp;&nbsp;1 | `Ritual` | — | —(仅路由) | `RitualCompleted` / `RitualNoAmulet` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `RitualCompleted` | OCR['暂无档案残片'] roi=[420, 290, 440, 110] | —(仅路由) | `SellAmulet` / `RitualDone` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `SellAmulet` | — | —(仅路由) | `AmuletSoldOut` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `AmuletSoldOut` | OCR['^0/'] roi=[721, 0, 180, 136] | —(仅路由) | `_NavigateTheRoom` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `_NavigateTheRoom` | 模板[TheRoom/Ritual.png] roi=[1115, 566, 159, 154] thr=0.8 | —(仅路由) | `_EnsureTheRoom` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `_EnsureTheRoom` | 模板[TheRoom/Ritual.png] roi=[1115, 566, 159, 154] | —(仅路由) | `_ServerMaintenance` / `_ConfirmReconnect` / `_CancelExitTheRoom` / `_CloseMeditationLog` / `~TheRoom` / `_NavigateTheRoom` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `_ServerMaintenance` | OCR['维护'] roi=[485, 227, 311, 133] | —(仅路由) | `_ConfirmServerMaintenance` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `_ConfirmServerMaintenance` | 模板[Utils/ConfirmMiddle.png] roi=[558, 1, 164, 719] | Click | `_LaunchGame` |
| · | `_LaunchGame` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `_ConfirmReconnect` | OCR['回来', '继续游玩'] roi=[437, 234, 404, 135] | —(仅路由) | `_ConfirmMiddle` |
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
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `RitualDone` | DirectHit | —(仅路由) | `~TaskExit` |
| · | `~TaskExit` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `RitualNoAmulet` | OCR['不足'] roi=[123, 500, 185, 127] | —(仅路由) | `SellAmulet` / `RitualDone` |
| · | `SellAmulet` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `RitualDone` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]Key2ArchivePieces`, `[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfirmReconnect`, `[JumpBack]_CancelExitTheRoom`, `[JumpBack]_CancelKey2ArchivePieces`, `[JumpBack]_CancelKey2Agent`, `[JumpBack]_CloseSellAmulet`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]_CloseMeditationLog`, `[JumpBack]_CloseRitualResult`, `[JumpBack]_ExitTheRoomStorage`, `[JumpBack]_ExitRitual`, `[JumpBack]_ExitRitualAgentSelect`, `[JumpBack]_Loading`, `[JumpBack]_TheRoomFromHome`, `[JumpBack]_NavigateHomepage`, `[JumpBack]NextAmulet`, `[JumpBack]_NavigateTheRoomStorage`, `[JumpBack]Key2Agent`, `[JumpBack]RitualUseAllKeys`, `[JumpBack]RitualRewardSelect`, `[JumpBack]NextRitual`, `[JumpBack]_NavigateRitual`


## `#CrisisMissionTickets`（危机行动调令）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `CrisisMissionTickets` | — | —(仅路由) | `CrisisMissionTicketsFromBCR` |
| &nbsp;&nbsp;1 | `CrisisMissionTicketsFromBCR` | OCR['主线故事'] roi=[1080, 607, 200, 113] | —(仅路由) | `CrisisMissionTicketsEnterCM` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `CrisisMissionTicketsEnterCM` | — | —(仅路由) | `确认在危机行动界面` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `确认在危机行动界面` | 模板[BCR/危机行动_界面标志.png] roi=[1122, 0, 142, 130] thr=0.8 | —(仅路由) | `检测危机行动调令HUD` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `检测危机行动调令HUD` | OCR['[0-9]'] roi=[1210, 22, 30, 33] | Custom['记录危机行动调令数'] | `~危机行动调令为零` / `CrisisMissionTicketsSelectLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `~危机行动调令为零` | Custom['危机行动调令为零'] | —(仅路由) | `CrisisMissionTicketsSkipped` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `CrisisMissionTicketsSkipped` | DirectHit | —(仅路由) | `_HomeButton` / `~Homepage` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `_HomeButton` | 模板[Utils/HomeButton.png] roi=[245, 0, 148, 143] | Click | （结束） |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `CrisisMissionTicketsSelectLevel` | 模板[BCR/危机行动_界面标志.png] roi=[1122, 0, 142, 130] thr=0.8 | —(仅路由) | `_NavigateS502` / `CrisisMissionTicketsFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `_NavigateS502` | OCR['幻影人偶Ⅱ', '幻影人偶II$'] roi=[821, 70, 240, 115] | —(仅路由) | `~S502_GoLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `~S502_GoLevel` | OCR['幻影人偶Ⅱ', '幻影人偶II$'] roi=[821, 70, 240, 115] | —(仅路由) | `CrisisMissionTicketsFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `CrisisMissionTicketsFromLevel` | OCR['快速完成'] roi=[804, 591, 273, 129] | Click | `CrisisMissionTicketsSweepStrategy` / `CrisisMissionTicketsSkipped` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `CrisisMissionTicketsSweepStrategy` | 模板[BCR/扫荡弹窗_界面标志.png] roi=[148, 176, 308, 292] | —(仅路由) | `设置危机行动战斗次数` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `设置危机行动战斗次数` | DirectHit | Custom['设置危机行动战斗次数'] | `点击出发` / `CrisisMissionTicketsSkipped` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;11 | `点击出发` | OCR['出发'] roi=[740, 480, 400, 165] | Click | `~等待快速完成结果` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;12 | `~等待快速完成结果` | OCR['快速完成结果', '完成次数', '认知度'] roi=[0, 0, 1280, 720] | —(仅路由) | `点击确定` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `点击确定` | OCR['确定', '确认退出'] roi=[940, 600, 340, 120] | Click | `退出关卡详情页` / `~Homepage` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;14 | `退出关卡详情页` | 模板[当期活动/主界面图标.png] roi=[11, 2, 413, 84] thr=0.85 | Click | `返回主界面` / `~Homepage` / `个人信息页返回` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;15 | `返回主界面` | 模板[当期活动/主界面图标.png] roi=[11, 2, 413, 84] thr=0.85 | Click | （结束） |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;15 | `个人信息页返回` | OCR['登录统计', '我的名片', '好友名册'] roi=[0, 0, 1280, 720] | Click@[127, 38, 1, 1] | （结束） |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `CrisisMissionTicketsSkipped` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `CrisisMissionTicketsSkipped` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `CrisisMissionTicketsFromLevel` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfirmReconnect`, `[JumpBack]_ConfirmSweepResult`, `[JumpBack]_LevelUp`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]_S502FromEliteMission`, `[JumpBack]_CrisisMissionHead`, `[JumpBack]_NavigateEliteMission`, `[JumpBack]_ReenterCrisisMission`, `[JumpBack]_NavigateCrisisMission`, `[JumpBack]_NavigateBCR`


## `#当期活动`（当期活动）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `当期活动` | — | —(仅路由) | `当前无活动` / `进入活动页` |
| &nbsp;&nbsp;1 | `当前无活动` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | `当前无活动确认` / `进入活动页` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `当前无活动确认` | OCR['剩余'] roi=[1150, 355, 130, 50] | —(仅路由) | `_StopTask` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `_StopTask` | — | Custom['记录任务中止'] | `_HaltTask` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `_HaltTask` | — | StopTask | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `进入活动页` | OCR['剩余'] roi=[1150, 355, 130, 50] | Click | `关闭活动提示` / `进入关卡章节` / `进入探索之旅` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `关闭活动提示` | OCR['今日获得', '硬币', '注意'] roi=[400, 180, 520, 180] | Click@[640, 380, 1, 1] | `进入关卡章节` / `进入探索之旅` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `进入关卡章节` | OCR['在光消失的地方', '消失的地方'] roi=[950, 460, 330, 90] | Click | `选择关卡` / `_关卡地图平移1` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `选择关卡` | 模板[当期活动/升腾AE111.png] roi=[0, 150, 1280, 480] thr=0.8 | Click@offset[0, 0, 0, 0] | `点击快速完成` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `点击快速完成` | OCR['快速完成'] roi=[700, 600, 400, 120] | Click | `行动力判定` / `行动次数确定` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `行动力判定` | OCR['下次恢复时间', '恢复时间'] roi=[400, 60, 720, 300] | Click@[640, 580, 1, 1] | `_Done` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `_Done` | DirectHit | —(仅路由) | `~TaskExit` |
| · | `~TaskExit` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `行动次数确定` | OCR['快速完成次数'] roi=[640, 365, 240, 40] | Click@[955, 457, 1, 1] | `点击出发` |
| · | `点击出发` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `_关卡地图平移1` | OCR['在光消失的地方', '消失的地方', '探索之旅'] roi=[0, 55, 420, 90] | Swipe | `选择关卡` / `_关卡地图平移2` |
| · | `选择关卡` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `_关卡地图平移2` | OCR['在光消失的地方', '消失的地方', '探索之旅'] roi=[0, 55, 420, 90] | Swipe | `选择关卡` |
| · | `选择关卡` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `进入探索之旅` | OCR['探索之旅'] roi=[740, 620, 260, 80] | Click | `选择关卡` / `_关卡地图平移1` |
| · | `选择关卡` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_关卡地图平移1` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `进入关卡章节` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `进入探索之旅` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `进入活动页` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfirmReconnect`, `[JumpBack]_NavigateHomepage`


## `#往期活动`（往期活动）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `往期活动` | — | —(仅路由) | `进入作战` / `点击往期活动` |
| &nbsp;&nbsp;1 | `进入作战` | OCR['作战'] roi=[850, 300, 360, 200] | Click | `点击往期活动` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `点击往期活动` | 模板[往期活动/往期活动.png] roi=[421, 0, 859, 154] thr=0.8 | Click | `~已切换到往期活动` / `点击往期活动_重试2` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `~已切换到往期活动` | 模板[往期活动/往期活动标志.png] roi=[47, 65, 484, 89] thr=0.85 | —(仅路由) | `进入往期活动内部流程` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `进入往期活动内部流程` | DirectHit | —(仅路由) | `~识别往日行动调令` / `选择往期活动` / `往左滑动` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `~识别往日行动调令` | OCR['[0-6]'] roi=[351, 92, 173, 48] | —(仅路由) | `记录往日行动调令数` / `选择往期活动` / `往左滑动` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `记录往日行动调令数` | OCR['[0-9]'] roi=[351, 92, 173, 48] | Custom['记录往日行动调令数'] | `~调令为零` / `选择往期活动` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `~调令为零` | Custom['调令为零'] | —(仅路由) | `退出往期活动失败` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `退出往期活动失败` | 模板[当期活动/主界面图标.png] roi=[11, 2, 413, 84] thr=0.85 | Click | `_NavigateHomepage` / `~Homepage` |
| · | `_NavigateHomepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `~Homepage` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `选择往期活动` | OCR['在月光之下'] roi=[0, 147, 1280, 442] | Click | `进入该往期活动事件` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `进入该往期活动事件` | DirectHit | —(仅路由) | `进入该往期活动事件_未适配` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `进入该往期活动事件_未适配` | DirectHit | —(仅路由) | （结束） |
| · | `选择往期活动` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `往左滑动` | — | Swipe | `选择往期活动_重试2` / `往左滑动2` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `选择往期活动_重试2` | OCR['在月光之下'] roi=[0, 147, 1280, 442] | Click | `进入该往期活动事件` |
| · | `进入该往期活动事件` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `往左滑动2` | — | Swipe | `选择往期活动_重试3` / `往左滑动3` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `选择往期活动_重试3` | OCR['在月光之下'] roi=[0, 147, 1280, 442] | Click | `进入该往期活动事件` |
| · | `进入该往期活动事件` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `往左滑动3` | — | Swipe | `选择往期活动_重试4` / `退出往期活动失败` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `选择往期活动_重试4` | OCR['在月光之下'] roi=[0, 147, 1280, 442] | Click | `进入该往期活动事件` |
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

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfirmReconnect`, `[JumpBack]_NavigateHomepage`


## `#Farm`（清体力）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `Farm` | — | —(仅路由) | `SelectLevelFromBCR` |
| &nbsp;&nbsp;1 | `SelectLevelFromBCR` | OCR['主线故事'] roi=[1080, 607, 200, 113] | —(仅路由) | `~LevelNA` / `~LiminalZoneNA` / `FarmFromLevel` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `~LevelNA` | OCR['重复行动'] roi=[804, 591, 273, 129] | —(仅路由) | （结束） |
| · | `~LiminalZoneNA` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `FarmFromLevel` | OCR['扫荡', '扫汤', '快速完成'] roi=[804, 591, 273, 129] | —(仅路由) | `_False` / `FarmStaminaShort` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `_False` | — | —(仅路由) | （结束） |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `FarmStaminaShort` | Custom['FarmStaminaShort'] | —(仅路由) | `_FarmStop` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `_FarmStop` | — | Custom['记录任务中止'] | `~TaskExitStop` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `~TaskExitStop` | DirectHit | —(仅路由) | `~HomepageThenHalt` / `_HaltTask` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `~HomepageThenHalt` | 模板[Homepage/SystemButton.png] roi=[32, 562, 137, 145] thr=0.8 | —(仅路由) | `_HaltTask` |
| · | `_HaltTask` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_HaltTask` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfirmReconnect`, `[JumpBack]_ConfirmSweepResult`, `[JumpBack]_ConfirmLiminalZoneOverflow`, `[JumpBack]FarmOutOfStamina`, `[JumpBack]_NavigateHomepage`, `[JumpBack]_LevelUp`, `[JumpBack]_SweepMax`, `[JumpBack]_SweepFromLevel`, `[JumpBack]FarmSelectLevel`, `[JumpBack]_NavigateBCR`


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

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfirmReconnect`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]_RecruitResult`, `[JumpBack]ExternalRecruitMax`, `[JumpBack]ExternalRecruitProceed`, `[JumpBack]ExternalRecruitAcc`, `[JumpBack]_NavigateExternalRecruit`


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
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;12 | `VioletMedalRedeemRecordAtVioletMedal` | 模板[Supplies/补给站_紫心奖章页签.png] roi=[697, 28, 269, 148] | —(仅路由) | `VioletMedalRedeemRecordOutOfMedal` / `VioletMedalRedeemRecordComplete` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `VioletMedalRedeemRecordOutOfMedal` | 模板[Utils/Tips.png] roi=[868, 95, 142, 300] | Click@[652, 512, 1, 1] | `_Done` |
| · | `_Done` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;13 | `VioletMedalRedeemRecordComplete` | OCR['剩余购买次数0'] roi=[876, 151, 230, 125] | Click@[652, 512, 1, 1] | `_Done` |
| · | `_Done` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_Done` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
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

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfirmReconnect`, `[JumpBack]_ConfirmMiddle`, `[JumpBack]VioletMedalRedeemRecordMax`, `[JumpBack]VioletMedalRedeemRecordFound`, `[JumpBack]_Cancel4`, `[JumpBack]_VioletMedalTail`, `[JumpBack]_NavigateVioletMedal`, `[JumpBack]SilverMedalRedeemAccMax`, `[JumpBack]SilverMedalRedeemAccFound`, `[JumpBack]_SilverMedalTail`, `[JumpBack]_NavigateSilverMedal`, `[JumpBack]SilverMedalRedeemOfferMax`, `[JumpBack]SilverMedalRedeemOfferFound`, `[JumpBack]SilverMedalRedeemRecordMax`, `[JumpBack]SilverMedalRedeemRecordFound`, `[JumpBack]CollectEventGift`, `[JumpBack]_NavigateEventSupplies`, `[JumpBack]DailyGift`, `[JumpBack]_NavigateReinforcementSupplies`


## `#一键领取`（一键领取）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `一键领取` | — | —(仅路由) | `DailyReward` |
| &nbsp;&nbsp;1 | `DailyReward` | — | —(仅路由) | `_OneClickGateDaily` |
| &nbsp;&nbsp;&nbsp;&nbsp;2 | `_OneClickGateDaily` | — | —(仅路由) | `CollectDailyReward` / `_OneClickGateWeekly` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3 | `CollectDailyReward` | 模板[Mission/日常任务_页签.png] roi=[677, 0, 214, 135] | Click@[1151, 669, 1, 1] | `_OneClickGateWeekly` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4 | `_OneClickGateWeekly` | — | —(仅路由) | `CollectWeeklyReward` / `_OneClickGateProtocol` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5 | `CollectWeeklyReward` | 模板[Mission/周常任务_页签.png] roi=[867, 0, 209, 131] | Click@[1151, 669, 1, 1] | `_OneClickGateProtocol` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6 | `_OneClickGateProtocol` | — | —(仅路由) | `CountermeasureProtocol` / `_OneClickDone` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `CountermeasureProtocol` | — | —(仅路由) | `ProtocolFullLevel` / `CollectProtocolWeekly` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `ProtocolFullLevel` | OCR['已满级'] roi=[550, 65, 171, 133] | —(仅路由) | `~TaskExit` |
| · | `~TaskExit` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;8 | `CollectProtocolWeekly` | 模板[Protocol/应对协议_周常页签.png] roi=[556, 135, 186, 134] | Click@[1103, 640, 1, 1] | `CollectProtocolSpecial` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;9 | `CollectProtocolSpecial` | 模板[Protocol/应对协议_特制页签.png] roi=[927, 135, 184, 133] | Click@[1103, 640, 1, 1] | `CollectProtocolReward` |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;10 | `CollectProtocolReward` | 模板[Protocol/应对协议_奖励页签.png] roi=[414, 172, 172, 195] | Click@[1103, 640, 1, 1] | `~TaskExit` |
| · | `~TaskExit` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7 | `_OneClickDone` | — | —(仅路由) | （结束） |
| · | `_OneClickGateProtocol` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |
| · | `_OneClickGateWeekly` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfirmReconnect`, `[JumpBack]_NavigateProtocolReward`, `[JumpBack]_NavigateProtocolSpecial`, `[JumpBack]_NavigateProtocolWeekly`, `[JumpBack]_NavigateWeeklyMission`, `[JumpBack]_NavigateDailyMission`


## `#UrbanPatrol`（市区巡逻）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `UrbanPatrol` | — | —(仅路由) | `DailyCollabPtsCollected` |
| &nbsp;&nbsp;1 | `DailyCollabPtsCollected` | OCR已 roi=[1052, 516, 166, 124] | —(仅路由) | `_False` |
| · | `_False` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |

> 该任务挂载的中断保底：`[JumpBack]_ServerMaintenance`, `[JumpBack]_ConfirmReconnect`, `[JumpBack]SelectAllFriends`, `[JumpBack]_NavigateMutualAid`, `[JumpBack]CollectDailyCollabPts`, `[JumpBack]_NavigateUrbanPatrol`


## `#ShutDown`（退出游戏）

| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |
|----|------|------------------|------|--------------------------|
| 0 | `ShutDown` | — | —(仅路由) | `_ExitGame` |
| &nbsp;&nbsp;1 | `_ExitGame` | — | StopApp | （结束） |


---

## 跨任务复用节点（共 10 个，改版回归时需一并验证）

| 节点 | 定义文件 | 复用任务数 | 复用任务 |
|------|---------|-----------|---------|
| `~Homepage` | Shared.json | 6 | 事务所（解读仪式）、危机行动调令、启动游戏、外部招募、往期活动、活动领取 |
| `~TaskExit` | Shared.json | 6 | 一键领取、事务所（解读仪式）、当期活动、活动领取、联线封锁、阈限禁区 |
| `_NavigateHomepage` | Shared.json | 3 | 启动游戏、外部招募、往期活动 |
| `_Cancel` | Shared.json | 2 | 事务所（解读仪式）、阈限禁区 |
| `_Done` | Shared.json | 2 | 当期活动、补给站 |
| `_False` | Shared.json | 2 | 市区巡逻、清体力 |
| `_HaltTask` | Shared.json | 2 | 当期活动、清体力 |
| `_LaunchGame` | Shared.json | 2 | 事务所（解读仪式）、启动游戏 |
| `~LiminalZoneNA` | Shared.json | 2 | 清体力、阈限禁区 |
| `点击出发` | Shared.json | 2 | 危机行动调令、当期活动 |
