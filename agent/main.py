import os
import sys

# 让 AgentServer 启动时能直接 import 本目录里的自定义模块（my_action / my_reco）
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from maa.agent.agent_server import AgentServer
from maa.toolkit import Toolkit

from mfalog import configure_stdlib_logging

# 统一接管 stdlib logging，使 MaaFW / 各组件既有的 log.info/error 也转为结构化 [MFA]{json}
configure_stdlib_logging()

# 资源包完整性自检（P0-1）：OTA 后若 agent/ 或 pipeline 被清空，这里先报出来。
# 只报告不阻断——自检自身异常不得变成新的故障源。
try:
    from selfcheck import run as _run_selfcheck
    _run_selfcheck()
except Exception:  # noqa: BLE001
    pass

# import my_action
# import my_reco
try:
    import crisis_mission
    import farm  # noqa: F401  注册 custom_recognition「FarmStaminaShort」（清体力体力不足判据）
    import past_event
    import soc_actions
    # 2026-10-22：任务级日志上下文 + 中止留痕（诊断用，无业务逻辑）
    import task_trace  # noqa: F401  注册 TaskerEventSink，输出任务开始/摘要
    import diagnostics  # noqa: F401  注册 custom_action「记录任务中止」
except Exception as exc:  # noqa: BLE001
    # Agent 由 MaaFramework 按 interface.json 的 agent 块拉起，崩溃信息只进
    # MFA 主机日志（不写 maafw.log）。这里打印显式错误，方便在主机日志里
    # 直接定位「Agent启动失败 / 连接失败」的根因。
    sys.stderr.write(
        "\n[MaaEOV] Agent 启动失败：自定义模块导入错误 -> {!r}\n"
        "排查：在软件目录执行 'python\\python.exe agent\\main.py' 手动运行，\n"
        "确认 python/ 与 maa 包完整、且版本与资源一致。\n".format(exc)
    )
    raise


def _resolve_socket_id() -> str:
    """解析 Agent 的 socket_id。

    MFAAvalonia 2.x 的启动命令形如：
        python main.py <ClientId> socket_id=<ClientId> instance_id=<id> instance_name=<name>
    而 1.x（旧版）只有：
        python main.py <ClientId>

    所以不能再用 `sys.argv[-1]`（新版下会取到 instance_name=...，导致 socket 名不匹配、
    C# 端永远等不到连接，表现为卡在「正在启动 Agent」）。
    这里优先取显式的 `socket_id=` 参数，其次退回到第一个不含 '=' 的位置参数。
    """
    for arg in sys.argv[1:]:
        if arg.startswith("socket_id="):
            return arg.split("=", 1)[1]
    for arg in sys.argv[1:]:
        if "=" not in arg:
            return arg
    return sys.argv[-1]


def main():
    Toolkit.init_option("./")

    socket_id = _resolve_socket_id()

    AgentServer.start_up(socket_id)
    AgentServer.join()
    AgentServer.shut_down()


if __name__ == "__main__":
    main()
