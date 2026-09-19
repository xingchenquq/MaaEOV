"""退出 MaaEOV 应用（MFA 进程）CustomAction（MaaEOV）

提供的 CustomAction：
- ExitApplication：终止 MaaEOV / MFA 主进程（及其进程树），用于「退出应用」任务。

设计要点：
  MaaEOV 的运行架构是 MFAAvalonia 宿主（MaaEOV.exe）通过 interface.json 的
  ``agent.child_exec`` 拉起内嵌 Python（python/python.exe）运行 agent/main.py。
  因此「退出应用」= 关闭 MaaEOV.exe 这个宿主进程；其下的 agent Python 作为子进程
  会随进程树一并被终止。

  为了避免「动作还在执行时自己就被杀掉导致返回失败」，本动作把真正的结束命令
  以**独立、脱离控制台的子进程（DETACHED_PROCESS）**方式拉起，然后立即返回 True。
  结束命令在后台异步执行，稍后把 MaaEOV.exe 进程树干掉，整个应用干净退出。

  结束策略（默认）：
    1. 按名称结束候选 exe（默认 ["MaaEOV.exe"]）：先发优雅关闭（taskkill 不带 /F，
       等价于向主窗口发 WM_CLOSE），等待短暂宽限后再强制结束（/F /T 连子树一起杀）。
    2. 可选地结束「当前 agent Python 的父进程树」：覆盖宿主被改名 / 由启动器拉起的场景。
       仅当父进程映像名看起来像宿主（含 MaaEOV / MFAAvalonia / dotnet）时才动手，
       避免误杀 explorer 等无关进程树。

  ⚠️ 不会波及模拟器（MuMu / 雷电）：它们属于独立进程树，不在 MaaEOV.exe 的子树内。
"""
import logging
import os
import subprocess
import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

log = logging.getLogger(__name__)

# 默认要结束的宿主 exe（与发布包根目录 MaaEOV.exe 对应）
_DEFAULT_EXE_NAMES = ["MaaEOV.exe"]
# 父进程映像名命中以下关键字才允许「结束父进程树」，避免误杀系统进程
_HOST_NAME_HINTS = ("MAAEOV", "MFAAVALONIA", "DOTNET")


def _parse_param(raw):
    """把 custom_action_param 解析成 dict，兼容已解析 dict / 字符串 / 双重 JSON 编码。"""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            import json
            return json.loads(raw or "{}")
        except Exception:
            return {}
    return {}


def _run_detached(cmd):
    """以脱离控制台的方式异步拉起一条命令（不阻塞、不继承本进程控制台）。

    返回 Popen 对象；调用方不应 .wait()。子进程在后台独立运行，
    即使本 agent 进程随后被宿主结束，它仍会继续把宿主进程树干掉。
    """
    creationflags = 0
    try:
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0
        )
    except Exception:
        creationflags = 0
    try:
        return subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=True,
        )
    except Exception as e:
        log.error(f"[ExitApplication] 拉起结束命令失败: {cmd!r} -> {e}")
        return None


def _parent_pid_via_ntquery(pid):
    """用 NtQueryInformationProcess 拿父进程 PID（Windows，64 位字段布局）。"""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # PROCESS_BASIC_INFORMATION（x64）：索引 5 = InheritedUniqueProcessId（父 PID）
        PBI = ctypes.c_ulonglong * 6
        pbi = PBI()
        status = kernel32.NtQueryInformationProcess(
            kernel32.GetCurrentProcess(),
            0,
            ctypes.byref(pbi),
            ctypes.sizeof(pbi),
            None,
        )
        if status == 0:
            return int(pbi[5])
    except Exception:
        pass
    return None


def _parent_pid_via_wmic(pid):
    """回退方案：wmic 查父进程 PID。"""
    try:
        out = subprocess.check_output(
            f'wmic process where processid={pid} get parentprocessid',
            shell=True,
            stderr=subprocess.DEVNULL,
        ).decode("gbk", "ignore")
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        # 第一行为表头 ParentProcessId，第二行为数值
        for ln in lines[1:]:
            digits = "".join(ch for ch in ln if ch.isdigit())
            if digits:
                return int(digits)
    except Exception:
        pass
    return None


def _process_name(pid):
    """查某 PID 的映像名（tasklist /fo csv）。"""
    if not pid:
        return None
    try:
        out = subprocess.check_output(
            f'tasklist /fi "PID eq {pid}" /fo csv /nh',
            shell=True,
            stderr=subprocess.DEVNULL,
        ).decode("gbk", "ignore")
        # 形如："MaaEOV.exe","12345","Console","1","123,456 K"
        if "," in out:
            return out.split(",", 1)[0].strip().strip('"')
    except Exception:
        pass
    return None


def _build_kill_cmd(exe_name, graceful, grace_seconds):
    """构造一条「先优雅后强制」的结束命令。

    - 优雅：taskkill 不带 /F（向主窗口发关闭消息），允许应用自行保存退出；
    - 强制：宽限若干秒后 taskkill /F /T 连子树一起杀，确保一定能退出。
    若 graceful 为 False，则直接强制。
    """
    if graceful and grace_seconds > 0:
        return (
            f'taskkill /T /IM "{exe_name}" '
            f'&& timeout /t {int(grace_seconds)} /nobreak >nul '
            f'&& taskkill /F /T /IM "{exe_name}"'
        )
    return f'taskkill /F /T /IM "{exe_name}"'


@AgentServer.custom_action("ExitApplication")
class ExitApplication(CustomAction):
    """终止 MaaEOV / MFA 宿主进程（及其进程树），实现「退出应用」任务。

    参数（JSON，均可选）：
        exe_names:        list[str]，要按名称结束的宿主 exe，默认 ["MaaEOV.exe"]
        kill_parent_tree: bool，是否额外结束「当前 agent Python 的父进程树」，
                          默认 True（覆盖宿主改名 / 启动器场景）
        graceful:         bool，是否先发优雅关闭再强制，默认 True
        grace_seconds:    int，优雅宽限秒数，默认 2
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        p = _parse_param(argv.custom_action_param)
        exe_names = p.get("exe_names") or _DEFAULT_EXE_NAMES
        if isinstance(exe_names, str):
            exe_names = [exe_names]
        kill_parent_tree = bool(p.get("kill_parent_tree", True))
        graceful = bool(p.get("graceful", True))
        grace_seconds = max(0, int(p.get("grace_seconds", 2)))

        log.info(
            f"[ExitApplication] 开始退出应用：exe_names={exe_names} "
            f"kill_parent_tree={kill_parent_tree} graceful={graceful}"
        )
        print(f"[ExitApplication] 正在退出 MaaEOV 应用…", flush=True)

        # 1) 按名称结束宿主 exe（后台异步，不阻塞本动作返回）
        for name in exe_names:
            cmd = _build_kill_cmd(name, graceful, grace_seconds)
            _run_detached(cmd)
            log.info(f"[ExitApplication] 已发起结束命令：{cmd}")

        # 2) 可选：结束父进程树（仅当父进程看起来像宿主，避免误杀无关进程树）
        if kill_parent_tree:
            pid = os.getpid()
            ppid = _parent_pid_via_ntquery(pid) or _parent_pid_via_wmic(pid)
            if ppid:
                parent_name = _process_name(ppid)
                looks_like_host = parent_name and any(
                    h in parent_name.upper() for h in _HOST_NAME_HINTS
                )
                if looks_like_host:
                    log.info(
                        f"[ExitApplication] 父进程 {ppid} ({parent_name}) 命中宿主特征，"
                        f"结束其进程树"
                    )
                    _run_detached(f"taskkill /F /T /PID {ppid}")
                else:
                    log.info(
                        f"[ExitApplication] 父进程 {ppid} ({parent_name}) 不像宿主，跳过"
                    )
            else:
                log.warning("[ExitApplication] 未能解析父进程 PID，跳过父进程树结束")

        # 关键：立即返回 True，让框架先拿到结果；真正的结束命令在后台异步执行，
        # 稍后把 MaaEOV.exe 进程树（含本 agent）干掉，整个应用干净退出。
        return True
