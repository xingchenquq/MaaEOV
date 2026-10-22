# -*- coding: utf-8 -*-
"""任务中止留痕：在 `_StopTask` 之前记录「从哪个节点中止 + 页面截图 + 最近路径」。

背景：`_StopTask` 是全局唯一的"停任务"出口，它让任务状态判为**成功**。
于是"活动未开放跳过"和"卡住了被迫中止"在 MFA 面板上长得一模一样（都是绿色），
出问题时只能靠人回忆 + 翻 debug/maafw.log。

本动作在停止前留一条结构化记录：
  debug/mfa_agent.log  一行 `[MFA]{...}`，含 node / entry / task_id / 最近节点路径
  debug/evidence/      当前页面截图（+ 同名 json 元数据），可直接看"停在什么界面"

排查时：`grep '"event": "task_abort"' debug/mfa_agent.log`，再按 task_id 拉出该次任务的完整轨迹。
"""
import os

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction

import evidence
from mfalog import mfa_err, mfa_log


def _recent_nodes(argv, limit: int = 8):
    """取本任务最近执行过的节点名（TaskDetail.nodes 惰性加载，失败不影响主流程）。"""
    try:
        td = argv.task_detail
        if td is None:
            return []
        names = [getattr(n, "name", "") for n in (getattr(td, "nodes", None) or [])]
        return [x for x in names if x][-limit:]
    except Exception:
        return []


@AgentServer.custom_action("记录任务中止")
class RecordTaskAbort(CustomAction):
    """在停止任务前落盘证据。永不抛出，避免"记录失败"变成新的故障源。"""

    def run(self, context, argv) -> bool:
        node = getattr(argv, "node_name", "") or "?"
        try:
            path_tail = _recent_nodes(argv)
        except Exception:
            path_tail = []

        shot = None
        # 真实的中止原因节点 = 最近路径里最后一项（`_StopTask` 自身此时尚未完成，不在其中）；
        # 若拿不到路径才退回 argv.node_name（那会是 `_StopTask`，信息量较低）。
        caller = path_tail[-1] if path_tail else node
        try:
            img = context.tasker.controller.post_screencap().wait().get()
            if img is not None:
                shot = evidence.save_evidence(
                    img, f"abort_{caller}",
                    meta={"stop_node": node, "caller": caller,
                          "path_tail": path_tail, "reason": "task_abort"},
                )
        except Exception as e:  # noqa: BLE001
            mfa_err("diagnostics", "abort_shot", f"中止截图失败（不影响停止）：{e}")

        try:
            # 打上 aborted 标记：之后同任务的每条日志（含 task_trace 的 task_end 摘要）都会带
            # aborted=true，一眼看出"这次虽然绿了，但中途是中止收尾的"。
            from mfalog import set_context
            set_context(aborted=True)
            mfa_log("diagnostics", "task_abort", "skip",
                    f"任务在节点「{caller}」中止（详见 path_tail 与截图）",
                    node=caller, stop_node=node, path_tail=path_tail, shot=shot or "")
        except Exception:  # noqa: BLE001
            pass
        return True
