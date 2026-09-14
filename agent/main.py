import os
import sys

# 让 AgentServer 启动时能直接 import 本目录里的自定义模块（my_action / my_reco）
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from maa.agent.agent_server import AgentServer
from maa.toolkit import Toolkit

# import my_action
# import my_reco
import auto_battle
import past_event
import soc_actions


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
