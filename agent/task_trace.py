# -*- coding: utf-8 -*-
"""任务级追踪：给每条 agent 日志补上「属于哪个任务」，并输出任务摘要。

背景：MFA 宿主只向 agent 转发 `Tasker.Task.*` 事件（节点级通知不转发），
所以拿不到逐节点的推送。这里做两件事：

1. `Tasker.Task.Starting`  → 设置日志上下文（task_id / entry），输出「任务开始」
2. `Tasker.Task.Succeeded/Failed` → 输出「任务摘要」（entry / 耗时 / 结果 / 节点数），清上下文

配合 `mfalog` 的 seq + ctx，`debug/mfa_agent.log` 里每条记录都自带 task_id 与 entry，
排查时可直接按 task_id 过滤出某一次任务的完整轨迹。

节点级上下文不在这里维护：`Context`/`TaskDetail` 在 custom_action 里更可靠
（见 `record_abort` 用 `argv.node_name` + `argv.task_detail`）。
"""
import time

from maa.agent.agent_server import AgentServer
from maa.tasker import TaskerEventSink

from mfalog import clear_context, context, mfa_log, set_context

_START_TS: dict = {}


@AgentServer.tasker_sink()
class TaskTrace(TaskerEventSink):
    """监听 Tasker.Task.*，输出任务级开始/摘要并维护日志上下文。"""

    def on_raw_notification(self, tasker, msg: str, details: dict) -> None:
        if not msg.startswith("Tasker.Task"):
            return
        d = details or {}
        tid = d.get("task_id")
        entry = d.get("entry") or d.get("name") or ""

        if msg.endswith(".Starting"):
            _START_TS[tid] = time.time()
            set_context(task_id=tid, entry=entry)
            mfa_log("trace", "task_start", "info",
                    f"任务开始 entry={entry}", entry=entry, task_id=tid)

        elif msg.endswith(".Succeeded") or msg.endswith(".Failed"):
            ok = msg.endswith(".Succeeded")
            cost = round(time.time() - _START_TS.pop(tid, time.time()), 1)
            # aborted：本次任务是否经 `_StopTask` 中止收尾（由 diagnostics 打的标记）。
            # StopTask 让任务判成功，光看 result 分不出「真的做完了」和「中途被迫中止」。
            aborted = bool(context().get("aborted"))
            mfa_log("trace", "task_end", "ok" if ok else "fail",
                    f"任务{'完成' if ok else '失败'}{'（中途中止）' if aborted else ''} "
                    f"entry={entry} 耗时={cost}s",
                    entry=entry, task_id=tid, cost_s=cost, aborted=aborted)
            clear_context()
