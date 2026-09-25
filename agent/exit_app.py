"""退出 MaaEOV 应用（MFA 进程）CustomAction（MaaEOV）

提供的 CustomAction：
- ExitApplication：终止 MaaEOV / MFA 主进程（及其进程树），用于「退出应用」任务。

设计要点（v1.14.2 重写，修 v1.14/v1.14.1 仍不生效）
  运行架构：MFAAvalonia 宿主（MaaEOV.exe）经 interface.json 的 ``agent.child_exec``
  拉起内嵌 Python（python/python.exe）运行 agent/main.py。因此「退出应用」= 关掉
  MaaEOV.exe 这个宿主进程；其下的 agent Python 作为子进程随进程树一并被终止。

  v1.14.1 的问题（"不生效"的真正根因）：
    直接用 subprocess.Popen 拉起 ``taskkill /F /T /PID <ppid>``。这个 taskkill
    本身也是 MaaEOV 进程树的**后代**（host → agent → cmd → taskkill）。而
    ``taskkill /T`` 会遍历并强制结束目标整棵进程树，**把自己也杀掉** → 结束命令
    来不及对宿主生效，程序纹丝不动。

  v1.14.2 的修复（两层，互不依赖）：
    1. 可靠主路径 —— **不使用 /T**：直接 ``taskkill /F /PID <ppid>`` 与
       ``taskkill /F /IM MaaEOV.exe``。因为不遍历后代，taskkill 不会杀到自身，
       一定能完整执行并强制终止宿主进程 → GUI 关闭。
    2. 整树清理（真机补充）—— 通过 ``wmic process create "taskkill /F /T /PID ..."``
       启动结束命令。wmic 创建的进程父进程是 wmiprvse.exe / services.exe，
       **不在 MaaEOV 进程树内**，因此即使带 /T 也不会杀到自身，可顺带清理 agent 等后代。

  三层降级（确保至少一条能命中）：
    a. 主：taskkill /F /PID <ppid>（无 /T，绝对可靠）
    b. 辅：taskkill /F /IM MaaEOV.exe（无 /T，按名兜底，覆盖父 PID 解析失败）
    c. 增强（wmic 可用时）：wmic 创建 taskkill /F /T /PID <ppid> 与 /F /T /IM MaaEOV.exe（整树）

  安全性：
    - 父 PID 若命中系统进程黑名单（System/explorer/services…）则放弃按 PID 结束，
      仅走按名路径。
    - 不会波及模拟器（MuMu / 雷电）：它们属于独立进程树，不在 MaaEOV.exe 子树内。
"""
import os
import subprocess
import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from mfalog import mfa_log, mfa_err, mfa_warn

_MODULE = "ExitApplication"

# 默认要结束的宿主 exe（与发布包根目录 MaaEOV.exe 对应），仅作「父 PID 解析失败」时的备份
_DEFAULT_EXE_NAMES = ["MaaEOV.exe"]
# 系统进程黑名单：父 PID 命中这些名字时绝不按 PID 结束其树，避免误杀桌面 / 服务
_SYSTEM_PROC = {
    "SYSTEM", "IDLE", "CSRSS.EXE", "WININIT.EXE", "SERVICES.EXE", "LSASS.EXE",
    "SVCHOST.EXE", "EXPLORER.EXE", "DESKTOPSHELL.EXE", "CONHOST.EXE",
    "TASKHOSTW.EXE", "DWM.EXE", "WINLOGON.EXE", "SMSS.EXE", "LOGONUI.EXE",
}


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


def _marker_path():
    """返回一个调试标记文件路径，用于确认 ExitApplication 真的执行过。"""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    debug_dir = os.path.join(root, "debug")
    os.makedirs(debug_dir, exist_ok=True)
    return os.path.join(debug_dir, f"exit_app_marker_{os.getpid()}_{int(time.time())}.txt")


def _write_marker(text):
    """把调试信息立即落盘并强制同步，确保宿主被杀后仍能看到。"""
    try:
        with open(_marker_path(), "w", encoding="utf-8") as f:
            f.write(text + "\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        pass


def _run_detached(cmd_list):
    """以脱离控制台、独立进程组的方式异步拉起一条命令（不阻塞、不继承本进程控制台）。

    cmd_list 必须已拆分为 argv 列表（不经过 shell 转义）。
    返回 Popen 对象；调用方不应 .wait()。
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
            cmd_list,
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
            close_fds=True,
        )
    except Exception as e:
        mfa_err(_MODULE, "run_detached", f"拉起命令失败: {cmd_list!r}", error=e)
        return None


def _taskkill_pid_noreap(pid):
    """可靠主路径：taskkill /F /PID <pid>（**不加 /T**）。

    不带 /T 就不会遍历、杀掉自身（taskkill 是宿主树后代），因此一定能完整执行、
    强制终止宿主进程。宿主死后其后代（agent）随连接断开而退出。
    """
    return _run_detached(["taskkill", "/F", "/PID", str(pid)])


def _taskkill_name_noreap(name):
    """可靠辅路径：taskkill /F /IM <name>（**不加 /T**），按名结束宿主。"""
    return _run_detached(["taskkill", "/F", "/IM", name])


def _spawn_taskkill_via_wmic(taskkill_args):
    """增强：通过 wmic process create 启动 taskkill（可带 /T 做整树清理）。

    wmic 创建的进程父进程是 wmiprvse.exe / services.exe，**不在 MaaEOV 进程树内**，
    因此即使带 /T 也不会杀到自身。
    """
    cmdline = " ".join(taskkill_args)
    return _run_detached(["wmic", "process", "create", cmdline])


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
        for ln in lines[1:]:
            digits = "".join(ch for ch in ln if ch.isdigit())
            if digits:
                return int(digits)
    except Exception:
        pass
    return None


def _process_name(pid):
    """查某 PID 的映像名（tasklist /fo csv）。失败返回 None。"""
    if not pid:
        return None
    try:
        out = subprocess.check_output(
            f'tasklist /fi "PID eq {pid}" /fo csv /nh',
            shell=True,
            stderr=subprocess.DEVNULL,
        ).decode("gbk", "ignore")
        if "," in out:
            return out.split(",", 1)[0].strip().strip('"')
    except Exception:
        pass
    return None


@AgentServer.custom_action("ExitApplication")
class ExitApplication(CustomAction):
    """终止 MaaEOV / MFA 宿主进程（及其进程树），实现「退出应用」任务。

    参数（JSON，均可选）：
        exe_names:        list[str]，按名字结束的宿主 exe（仅作备份），默认 ["MaaEOV.exe"]
        kill_parent_tree: bool，是否按 PID 结束「当前 agent Python 的父进程树」，
                          默认 True（这是最可靠的结束路径，与 exe 名无关）
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        p = _parse_param(argv.custom_action_param)
        exe_names = p.get("exe_names") or _DEFAULT_EXE_NAMES
        if isinstance(exe_names, str):
            exe_names = [exe_names]
        kill_parent_tree = bool(p.get("kill_parent_tree", True))

        mfa_log(_MODULE, "exit_app", "info", "正在退出 MaaEOV 应用…")

        # ── 解析父 PID / 父名 ──────────────────────────────────────────────
        ppid = _parent_pid_via_ntquery(os.getpid()) or _parent_pid_via_wmic(os.getpid())
        parent_name = _process_name(ppid) if ppid else None
        mfa_log(
            _MODULE, "exit_app", "info",
            f"本进程 PID={os.getpid()} 父 PID={ppid} 父映像名={parent_name!r}",
        )

        # 先落盘调试标记，方便后续查 log（宿主被杀后日志未必 flush）
        _write_marker(
            f"pid={os.getpid()} ppid={ppid} parent={parent_name} "
            f"kill_parent_tree={kill_parent_tree} exe_names={exe_names}"
        )

        launched = False

        # ── 主路径：taskkill /F /PID（无 /T，绝对可靠）──────────────────────
        if kill_parent_tree and ppid:
            up = (parent_name or "").upper()
            if up not in _SYSTEM_PROC:
                mfa_log(_MODULE, "exit_app", "info", f"直接 taskkill /F /PID {ppid}（无 /T）")
                mfa_log(_MODULE, "exit_app", "ok", f"结束宿主进程 PID={ppid}")
                _taskkill_pid_noreap(ppid)
                launched = True
            else:
                mfa_warn(
                    _MODULE, "exit_app",
                    f"父进程 {ppid}({parent_name}) 命中系统黑名单，放弃按 PID 结束，仅走按名路径",
                )
        elif kill_parent_tree and not ppid:
            mfa_warn(_MODULE, "exit_app", "未能解析父进程 PID，仅走按名路径")

        # ── 辅路径：taskkill /F /IM（无 /T，按名兜底）──────────────────────
        for name in exe_names:
            mfa_log(_MODULE, "exit_app", "info", f"直接 taskkill /F /IM {name}（无 /T）")
            _taskkill_name_noreap(name)
            launched = True

        # ── 增强：wmic 创建 taskkill /F /T（整树清理，真机可用）─────────────
        # wmic 不可用时（极少数环境）跳过，不影响上面无 /T 的可靠结束。
        if kill_parent_tree and ppid:
            up = (parent_name or "").upper()
            if up not in _SYSTEM_PROC:
                _spawn_taskkill_via_wmic(["taskkill", "/F", "/T", "/PID", str(ppid)])
        for name in exe_names:
            _spawn_taskkill_via_wmic(["taskkill", "/F", "/T", "/IM", name])

        if not launched:
            # 理论不可达：连按名都没发起时，最后兜底用带 /T 的旧式按名结束
            for name in exe_names:
                mfa_warn(_MODULE, "exit_app", f"兜底 taskkill /F /T /IM {name}")
                _run_detached(["taskkill", "/F", "/T", "/IM", name])

        # 立即返回 True：结束命令已在后台异步拉起，稍后把宿主进程（含本 agent）
        # 干掉，整个应用干净退出。
        return True
