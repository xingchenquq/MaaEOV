<!-- markdownlint-disable MD033 MD041 -->
<div align="center">

<img alt="LOGO" src="./Assets/logo.ico" width="256" height="256" />

# MaaEOV

基于 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 的 [异象回声](https://eov.astral-vector.com/) 小助手。  
旨在自动化完成日常任务，避免错过/忘记/懒得做日常。图像技术 + 模拟控制，解放双手！  
<a href="https://github.com/xingchenquq/MaaEOV" target="_blank" style="font-weight: bold;">🔗 本项目 GitHub 仓库</a><br>
🌟喜欢本项目就在仓库右上角点个星星吧🌟

</div>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white">
  <img alt="platform" src="https://img.shields.io/badge/platform-Windows-blueviolet">
  <img alt="license" src="https://img.shields.io/github/license/xingchenquq/MaaEOV">
  <br>
  <img alt="commit" src="https://img.shields.io/github/commit-activity/m/xingchenquq/MaaEOV">
  <img alt="stars" src="https://img.shields.io/github/stars/xingchenquq/MaaEOV">
  <img alt="downloads" src="https://img.shields.io/github/downloads/xingchenquq/MaaEOV/total">
</p>

## 项目说明与来源

>[!IMPORTANT]
>
>本项目基于 **[Tigerisu/MaaEOV](https://github.com/Tigerisu/MaaEOV)** 二次开发而来（衍生项目，非 Fork 关系），遵循其 MIT 许可证继续开源。
>原项目由 [Tigerisu](https://github.com/Tigerisu) 开发并维护，本项目在其架构与流程基础上持续迭代，新增/重写了大量任务（认知海域、往期活动、活动双任务、补给站、一键领取等），并随游戏版本持续适配。
>感谢原作者的出色工作，本项目的存在离不开它。

**与上游的主要差异（截至 v2.1.2）**

| 能力 | 上游 Tigerisu/MaaEOV | 本项目 |
|---|---|---|
| 认知海域自动扫荡 | 计划中 | ✅ 已实现（自走棋式自动战斗） |
| 往期活动扫荡 | 无 | ✅ 多期复刻活动可选 |
| 当期活动 | 无 | ✅ 主线 + 复刻双活动，关卡可选 |
| 补给站 / 一键领取 / 邮件 | 部分散落 | ✅ 整合为独立任务，逐项可开关 |

## 公告

>[!IMPORTANT]
>
>- 建议首次使用时**在监督下运行一次**，确认功能运行正常。遇到问题欢迎通过 [Issues](https://github.com/xingchenquq/MaaEOV/issues) 反馈，附上 `logs/` 与 `debug/` 目录更易定位。
>- 由于《异象回声》桌面互通版需要跳转浏览器登录，**MaaEOV 暂无对桌面互通版的支持计划**，请搭配模拟器使用。

## 快速开始

1. **下载**：在 [Releases](https://github.com/xingchenquq/MaaEOV/releases) 页面下载最新完整包 `MaaEOV-v<版本>-full-package.zip`。
2. **解压**：解压到任意**不含中文与空格**的目录（建议独立目录，不要与其他 Maa 系项目混放）。
3. **启动**：运行 `MaaEOV.exe`，在 GUI 的「连接设置」中选择你的模拟器。模拟器未运行时请先手动打开，GUI 会自动检测设备。
4. **开跑**：左侧勾选要跑的任务（默认已勾选「日常」组），点「开始任务」。任务从上到下依次执行，可拖拽调整顺序。

> [!TIP]
> 首次使用建议只勾「日常」组跑一遍，观察各任务是否正常，再按需添加「周期副本」「活动」组。

## 使用说明

>[!WARNING]
>
>在游戏的 **设置 → 画面** 中，请确保 **「低分辨率」选项处于关闭状态**。开启该选项会导致功能异常。

>[!TIP]
>
>**模拟器与连接**
>
>- 发布包**不含任何模拟器配置**（模拟器路径 / 端口因机器而异，硬编码会连错设备）。请按实际实例在「连接设置」中填写。
>- 多开端口：MuMu 端口随实例号递增（0 号实例为 `127.0.0.1:16384`），请按实际实例填写。
>- 需要游戏内**关闭「低分辨率」**、模拟器分辨率建议 **1280×720（DPI 240）**。

>[!TIP]
>
>**跑完自动退出**
>
>若希望任务全部结束后自动关闭 MaaEOV，请在 GUI 中把「任务完成后」设为 **关闭 MFA**。请勿用队列末尾的「退出应用」任务充当退出——**任一任务失败会中止整条队列**，末尾任务不会执行，程序也就不会退出。

>[!TIP]
>
>**更新方式（完整包）**
>
>- 在 GitHub Release 下载 `MaaEOV-v<版本>-full-package.zip`，解压覆盖到原安装目录即可完成更新（会一并更新 `agent/` + `python/` + `maa` 包 + MFA + `resource/`）。
>- 暂不提供增量（resource）更新；如需更新，请使用完整包。

## 功能列表

任务列表即执行顺序，可自由勾选、拖拽调整。默认已勾选「日常」组，点开始即可跑完一天。

**日常**（每天重置）

| 任务 | 说明 |
|---|---|
| 活动领取 | 邮件、每日行动补给、短期支援补贴 |
| 事务所（解读仪式） | 按偏好刷解读仪式，可选追加档案残片 / 加速休息 / 分解护符 |
| 危机行动调令 | 消耗全部调令，为 0 时跳过 |
| 清体力 | 在指定关卡清空体力（可选自动用即将过期的体力道具） |
| 外部招募 | 队列满时可选用急务招聘书 |
| 补给站 | 每日礼包 + 活动货柜 + 银心/紫心奖章商店 |
| 一键领取 | 日常任务奖励、周常任务奖励、应对协议奖励（可逐项开关） |
| 市区巡逻 | 赠送并领取解读点数，购买全部奖励 |

**周期副本**

| 任务 | 周期 | 说明 |
|---|---|---|
| 阈限禁区 | 每周 | 扫荡至黑胶上限（480/480） |
| 认知海域 | 双周 | 自走棋式自动战斗，满 1000 分或入场券耗尽即停 |
| 联线封锁 | 每月 | 扫荡至奖章上限（108/108） |

**活动**

| 任务 | 说明 |
|---|---|
| 当期活动 | 扫荡当前活动关卡，关卡可选（主线 / 复刻入口自动分派，换期后需确认关卡配置） |
| 往期活动 | 复刻活动扫荡（活动可选） |

**系统**

| 任务 | 说明 |
|---|---|
| 启动游戏 | 启动直到检测到游戏主界面（可选放弃未完成战斗） |
| 退出游戏 | 退出游戏 |

>[!NOTE]
>扫荡类任务（阈限禁区 / 联线封锁 / 活动）要求对应关卡**通关过一次**才会开放扫荡。
>认知海域支持目标层与 Buff 取舍策略两档配置，默认「配置一」不读卡名、行为最稳。
>「当期活动」的关卡选项跟随游戏当前活动更新（如 FL105 / AE201 / AE110-112），**换期后请先确认关卡配置是否仍匹配当前活动**，如需适配可在 Issues 反馈。

## 故障排查

>[!NOTE]
>
>**Agent 启动失败（连接重试 → 任务失败: 连接）**
>
>现象：GUI 依次提示「正在启动 Agent → 连接重试 (2/3) → (3/3) → Agent启动失败 → 任务失败: 连接」。
>
>本质：Agent 是 MaaFramework 依据 `interface.json` 的 `agent` 块拉起的独立 Python 子进程，通过框架自动生成的 `socket_id` 回连主机。日志里出现 `failed to send_and_recv`，代表**子进程虽被拉起、却没连上 socket 就已退出**——通常是自定义模块导入报错、`maa` 包损坏，或 `python/` 缺失/版本错配。注意：子进程崩溃信息只进 **MFA 主机日志**，**不会**写进 `maafw.log`，所以 `maafw.log` 里看不到 Python 报错是正常的。
>
>解决（按优先级）：
>1. **重解压完整包覆盖**：重新解压 `MaaEOV-v<版本>-full-package.zip`，让 `agent/` + `python/` + `maa` 包 + MFA 同源同版本。
>2. **手动验证 agent**：在软件目录下执行 `python\python.exe agent\main.py`。
>   - 卡住不动（hang）= 健康，只是在等 MFA 连它；
>   - 立刻 traceback = 缺模块 / `maa` 损坏 / `python.exe` 不对，按报错修。
>3. **更新走完整包**：目前仅发布完整包（GitHub Release），版本由完整包统一保证；不要手动把不同版本的 `resource/` 与 `agent/` 混装。
>4. 任务管理器里结束残留的 `python.exe` 再重试，避免旧 socket 占用。
>5. 查看 **MFA 自身日志** 拿 Python 真实报错（agent 的 stderr 不进 `maafw.log`）。

## 参与贡献

欢迎以任何形式参与：

- **反馈问题**：[Issues](https://github.com/xingchenquq/MaaEOV/issues) 提交 Bug / 建议。请附：
  - `logs/` 与 `debug/` 目录（GUI 右下角「导出日志」可一键打包）；
  - 出问题时模拟器分辨率、游戏版本、所用任务与选项。
- **提交代码**：Fork → 分支 → PR。改动请先在本地跑通：
  - 静态校验：`python scripts/verify_feature.py`（需 ALL_OK）与 `python scripts/check_graph.py`；
  - 关卡配置一致性：`python scripts/check_levels.py`；
  - 实机冒烟：`python scripts/run_tasks.py --only <任务名>`（需已连接模拟器）。
- **适配新活动**：换期后关卡入口 / 编号变化时，欢迎提 Issue 附上界面截图与关卡 ID，或直接提 PR 修改入口链与关卡配置。

## 许可证

本项目以 **[MIT License](./LICENSE)** 开源。

- 本项目衍生自 [Tigerisu/MaaEOV](https://github.com/Tigerisu/MaaEOV)（MIT），原项目的代码与设计归原作者所有；
- 基于本项目使用的 [MaaFramework](https://github.com/MaaXYZ/MaaFramework)（LGPL-3.0）与 [MFAAvalonia](https://github.com/SweetSmellFox/MFAAvalonia) 同样遵循其各自许可证；
- 使用本项目即表示你了解并同意：自动化脚本存在封号风险，**由此产生的一切后果由使用者自行承担**，项目仅供学习交流。

## 鸣谢

- 本项目由 **[MaaFramework](https://github.com/MaaXYZ/MaaFramework)** 强力驱动！
- **原项目：[Tigerisu/MaaEOV](https://github.com/Tigerisu/MaaEOV)** —— 本项目的起点，感谢 Tigerisu 的工作与 MIT 开源
- 项目模板：[MaaPracticeBoilerplate](https://github.com/MaaXYZ/MaaPracticeBoilerplate)
- GUI: [MFAAvalonia](https://github.com/SweetSmellFox/MFAAvalonia)
- Debugger: [MaaDebugger](https://github.com/MaaXYZ/MaaDebugger)
- Tool: [MFATools](https://github.com/SweetSmellFox/MFATools)
- 参考：[M9A](https://github.com/MAA1999/M9A)

<!-- 感谢以下开发者对本项目作出的贡献:

[![Contributors](https://contrib.rocks/image?repo=xingchenquq/MaaEOV&max=1000)](https://github.com/xingchenquq/MaaEOV/graphs/contributors) -->
