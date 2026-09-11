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


def main():
    Toolkit.init_option("./")

    socket_id = sys.argv[-1]

    AgentServer.start_up(socket_id)
    AgentServer.join()
    AgentServer.shut_down()


if __name__ == "__main__":
    main()
