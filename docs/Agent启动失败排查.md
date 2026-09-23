# Agent 启动失败排查指南

适用症状：GUI 依次提示「正在启动 Agent → 连接重试 (2/3) → (3/3) → Agent启动失败 → 任务失败: 连接」。

>[!NOTE]
>
>本项目当前**仅发布完整包**（GitHub Release 的完整包 zip）更新，**暂不提供增量（resource）更新**。下文关于「OTA 增量更新导致版本不一致」的内容，仅用于解释本次故障的历史根因，不代表当前更新方式。

---

## 1. 机制（官方文档依据）

- Agent 是 **MaaFramework 依据 `interface.json` 的 `agent` 块**（`child_exec` / `child_args`）拉起的独立 Python 子进程，框架自动生成 `socket_id` 并作为参数传给 `agent/main.py`；`agent/main.py` 调用 `AgentServer.start_up(socket_id)` 回连主机（[MaaFramework 官方 QuickStart](https://maafw.com/en/docs/1.1-QuickStarted)、[docs.rs `AgentServer`](https://docs.rs/maa-framework/latest/maa_framework/agent_server/struct.AgentServer.html)）。
- 启动链：`spawn(child, socket_id)` → 导入依赖 → `AgentServer.start_up(socket_id)` → `join()`（[DeepWiki M9A `3.4-agent-system`](https://deepwiki.com/MAA1999/M9A/3.4-agent-system)）。任一步在 `start_up` 之前异常退出，主机侧就会 `failed to send_and_recv`。
- 子进程（Python）的 stdout/stderr 进的是 **MFA 主机日志**，**不在 `maafw.log`**。

## 2. 根因判断（结合 MaaEOV 实测日志）

日志证据（测试机 `maafw.log`，框架全程 `MaaFramework v5.12.3`）：

| 证据 | 含义 |
|---|---|
| 05:10 会话成功：`AgentClient` 连上 `maafw-agent-7wRruXrv.sock`，跑完整任务链 | agent 层当时健康 |
| 14:49 / 14:56 / 15:24 三次均 `AgentClient::connect → failed to send_and_recv`，且**无 `Tasker.Task.Starting`** | 子进程没连上 socket，任务根本没开始 |
| 框架版本全程 `v5.12.3` 未变 | 不是 MaaFramework 升级引入的回归 |
| `maafw.log` 无任何 `python.exe` / `main.py` 生成记录 | 崩溃信息在 MFA 主机日志，不在 `maafw.log` |

**结论**：测试机的 **`agent/` + `python/` + `maa` 包这一层损坏或版本错配**（最可能是 05:10 之后做了一次不完整更新、或「旧完整包 + OTA 资源」混装、或 OTA 因 PAT 失效只拉了一半资源）。

> OTA（增量更新）只动 `interface.json` + `resource/`，碰不到 `agent/`/`python/`/`maa`。所以 OTA 不是直接元凶，但「资源版本与完整包版本不一致」会让 agent 在启动期就失败。

## 3. 同栈项目官方 FAQ 的精确对应

[M9A 官方 FAQ](https://1999.fan/zh_cn/manual/faq.html)（同为 MaaFramework + MFAAvalonia 栈）：

> 「Agent 长时间启动无反应（Windows）：使用通用 UI（如 MFAAvalonia）时，长时间无反应，或提示 `...No such file or directory`，需要**重新下载完整包**。」

一线解法即为「重新下载/重解压完整包」，与上面的根因判断一致。

## 4. 排查步骤

在测试机软件目录下：

```bat
rem 手动跑 agent，观察是 hang 还是立刻报错
python\python.exe agent\main.py
```

- **卡住不动（hang）** = 健康，只是在等 MFA 连它 → 问题在 MFA 主机侧或残留进程。
- **立刻 traceback** = 缺模块 / `maa` 损坏 / `python.exe` 不对 → 按报错修（通常需回到「重解压完整包」）。
- 同时查看 **MFA 自身日志** 拿 Python 真实报错（agent 的 stderr 不进 `maafw.log`）。

## 5. 解决方法（按优先级）

1. **重解压完整包覆盖**：重新解压 `MaaEOV-v<版本>-full-package.zip`，使 `agent/` + `python/` + `maa` 包 + MFA 同源同版本。
2. **手动验证 agent**（见第 4 节）确认 python/`maa` 层 OK。
3. **更新走完整包**：本项目目前仅发布完整包（GitHub Release），版本由完整包统一保证；不要手动把不同版本的 `resource/` 与 `agent/` 混装。私有库在 `设置 → 更新 → GitHub Token` 填有效的只读 PAT（权限仅 `Contents: Read-only`）才能拉取 Release。
4. 任务管理器结束残留 `python.exe` 再重试，避免旧 socket 占用。
5. 仍不行则查看 MFA 主机日志中的 traceback 定位具体缺失模块。

## 6. 自诊断增强

`agent/main.py` 已对自定义模块导入加 `try/except`：导入失败时会在 stderr 打印一行显式错误

```
[MaaEOV] Agent 启动失败：自定义模块导入错误 -> <异常>
```

该信息出现在 MFA 主机日志中，便于直接定位根因。

## 7. 来源

- MaaFramework 官方 QuickStart：<https://maafw.com/en/docs/1.1-QuickStarted>
- `AgentServer` API（docs.rs）：<https://docs.rs/maa-framework/latest/maa_framework/agent_server/struct.AgentServer.html>
- M9A Agent System（DeepWiki）：<https://deepwiki.com/MAA1999/M9A/3.4-agent-system>
- M9A 官方 FAQ（症状精确对应）：<https://1999.fan/zh_cn/manual/faq.html>
- MFAAvalonia README：<https://github.com/MaaXYZ/MFAAvalonia>
