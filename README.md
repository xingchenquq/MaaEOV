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
  <img alt="platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blueviolet">
  <img alt="license" src="https://img.shields.io/github/license/xingchenquq/MaaEOV">
  <br>
  <img alt="commit" src="https://img.shields.io/github/commit-activity/m/xingchenquq/MaaEOV">
  <img alt="stars" src="https://img.shields.io/github/stars/xingchenquq/MaaEOV">
  <img alt="downloads" src="https://img.shields.io/github/downloads/xingchenquq/MaaEOV/total">
  <!-- <a href="https://mirrorchyan.com/zh/projects?rid=M9A&source=m9agh-badge" target="_blank"><img alt="mirrorc" src="https://img.shields.io/badge/Mirror%E9%85%B1-%239af3f6?logo=countingworkspro&logoColor=4f46e5"></a> -->
</p>

<div align="center">

<!-- [English](./README_en.md) | [简体中文](./README.md) -->

</div>

## 公告

>[!IMPORTANT]
>
>请注意：
>
>- 当前版本似乎已经可以稳定运行。建议使用时在监督下运行一次，以确认功能运行正常。如在使用过程中遇到问题，欢迎通过 Issues 反馈。
>- 由于《异象回声》桌面互通版需要跳转浏览器登录，**MaaEOV暂无对桌面互通版的支持计划**，请搭配模拟器使用。
<!-- 
---

>[!TIP]
>
>新版本 **[MFAAvalonia](https://github.com/SweetSmellFox/MFAAvalonia)** 近期已趋于稳定，项目后续可能会升级至较新版本。若升级 GUI，用户可能需要安装 .NET 10，并对 配置文件 进行调整，具体说明将另行发布。
>
>**建议对保存的配置文件（`MaaEOV/config/<配置名称>.json`）进行备份以免丢失。** -->

## 使用说明

>[!WARNING]
>
>在游戏的 **设置 → 画面** 中，请确保 **「低分辨率」选项处于关闭状态**。开启该选项会导致功能异常。

>[!TIP]
>
>**首次使用 · 模拟器与退出设置**
>
>- **模拟器**：发布包**不含任何模拟器配置**（模拟器路径 / 端口因机器而异，硬编码会连错设备）。首次启动后在 GUI 的「连接设置」中选择你的模拟器；模拟器未运行时请先手动打开，GUI 会自动检测到设备。
>- **多开端口**：MuMu 端口随实例号递增（0 号实例为 `127.0.0.1:16384`），请按实际实例填写。
>- **跑完自动退出**：若希望任务全部结束后自动关闭 MaaEOV，请在 GUI 中把「任务完成后」设为 **关闭 MFA**。请勿用队列末尾的「退出应用」任务充当退出——**任一任务失败会中止整条队列**，末尾任务不会执行，程序也就不会退出。

>[!TIP]
>
>**更新方式（当前仅完整包）**
>
>- 目前**只发布完整包**：在 GitHub Release 下载 `MaaEOV-v<版本>-full-package.zip`，解压覆盖到原安装目录即可完成更新（会一并更新 `agent/` + `python/` + `maa` 包 + MFA + `resource/`）。
>- 本仓库为**私有库**，因此使用 GUI 的 GitHub 更新前，需在 **设置 → 更新 → GitHub Token** 填入一个对该仓库**只读**的 PAT（建议细粒度令牌，权限仅 `Contents: Read-only`，仅授权本仓库），这样才能拉取 Release。
>- 该 Token 只保存在你本机的全局配置里；**发布包不包含它**，请勿把带 Token 的配置外传。
>- 暂不提供增量（resource）更新；如需更新，请使用上面的完整包。

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
>3. **更新走完整包**：目前仅发布完整包（GitHub Release），版本由完整包统一保证；不要手动把不同版本的 `resource/` 与 `agent/` 混装。私有库需在 `设置 → 更新 → GitHub Token` 填有效的只读 PAT 才能拉取 Release。
>4. 任务管理器里结束残留的 `python.exe` 再重试，避免旧 socket 占用。
>5. 查看 **MFA 自身日志** 拿 Python 真实报错（agent 的 stderr 不进 `maafw.log`）。

## 功能列表

- 启动游戏
- 每周-阈限禁区
- 清体力
- 危机行动调令
- 事务所（解读仪式）
- 市区巡逻
- 领取任务奖励
- 领取应对协议
- 领取邮件
- 补给站
- 外部招募
- 退出游戏
- 退出应用
- 活动-每日行动补给
- 联线封锁
- 活动-短期支援补贴
- 当期活动
- 往期活动
- 自动推图
- 认知海域（开发中）

>[!NOTE]
>认知海域 自动扫荡已实现初版（独立 pipeline 文件 `resource/base/pipeline/认知海域.json`，GUI 任务「认知海域」）。
>范围为：导航 → 选层（默认梦渊层）→ 深潜指引 → 配队确认 → Buff(首个) → 启动自动战斗 → 等待结算 → 领奖 → 循环（入场券耗尽即停）。
>按钮识别以 OCR 为主；部分界面（Buff 选择 UI、入场券耗尽弹窗文字、配队确认按钮文字）仍需截图核对后微调。

## 开发相关

更多文档请前往 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 主仓库查看

## 鸣谢

- 本项目由 **[MaaFramework](https://github.com/MaaXYZ/MaaFramework)** 强力驱动！
- 项目模板：[MaaPracticeBoilerplate](https://github.com/MaaXYZ/MaaPracticeBoilerplate)
- GUI: [MFAAvalonia](https://github.com/SweetSmellFox/MFAAvalonia)
- Debugger: [MaaDebugger](https://github.com/MaaXYZ/MaaDebugger)
- Tool: [MFATools](https://github.com/SweetSmellFox/MFATools)
- 参考：[M9A](https://github.com/MAA1999/M9A)

<!-- 感谢以下开发者对本项目作出的贡献:

[![Contributors](https://contrib.rocks/image?repo=xingchenquq/MaaEOV&max=1000)](https://github.com/xingchenquq/MaaEOV/graphs/contributors) -->
