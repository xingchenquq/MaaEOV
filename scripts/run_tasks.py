# -*- coding: utf-8 -*-
"""逐任务实机冒烟 / 回归驱动。

用途：改完 pipeline 后，按任务逐个跑一遍并拿到「真实走过的节点序列」，
     用于对照 `docs/任务流程与UI重测清单.md` 的预期主链路查偏差。

前置：MFA 已保存的实例配置（`config/maa_pi_config.json`）里填好 adb 路径与地址；
     脚本不自带硬编码路径，换机后无需改代码。

几个必须知道的点（2026-10-22 实测）：
* **option 取值读 `config/instances/default.json` 的用户实际选择**，不要用 `cases[0]` ——
  补给站 5 项、清体力/事务所的道具项，`cases[0]` 都是「会花奖章 / 吃道具」的 Yes。
* **MaaFW 只向 agent 转发 `Tasker.Task.*` 事件，不发节点级通知** ——
  所以节点序列取自任务结束后的 `TaskDetail.nodes`，不是 EventSink。
* **agent 必须在子进程中拉起**：本进程 import `agent/*.py` 会触发 `_set_api_properties`
  改写 ctypes 签名，导致后续 `MaaTaskerCreate` 失败（实测 Failed to create tasker）。
* **adb server 在沙箱/CI 里活不过命令结束**：本脚本自身 spawn 的 adb 在进程内有效，
  但如果你在 shell 里手工预热 server，需要与后续命令放在同一次调用中。

用法：
    python scripts/run_tasks.py --list                    # 列出任务与 entry
    python scripts/run_tasks.py --only 一键领取           # 单任务
    python scripts/run_tasks.py --smoke                   # 按预设顺序全跑（不含挂起任务）
    python scripts/run_tasks.py --only 活动领取 --timeout 200
    python scripts/run_tasks.py --only 清体力 --override '{"_SweepFromLevel":{"enabled":false}}'
    python scripts/run_tasks.py --only 危机行动调令 --disable "~危机行动调令为零"

产出：`debug/task_runs/report_<时间戳>.json`（含节点路径、点击 text/score/box、失败截图）。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "python", "Lib", "site-packages"))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

import pj  # noqa: E402
from maa.controller import AdbController  # noqa: E402
from maa.resource import Resource  # noqa: E402
from maa.tasker import Tasker, TaskerEventSink  # noqa: E402
from maa.toolkit import Toolkit  # noqa: E402

OUT_DIR = os.path.join(ROOT, "debug", "task_runs")
PI_CONFIG = os.path.join(ROOT, "config", "maa_pi_config.json")

# 冒烟顺序：从轻到重，退出游戏收尾。
# 「认知海域」「自动推图」按当前进度挂起，未纳入（需要时用 --only 单独跑）。
SMOKE_ORDER = [
    "启动游戏",
    "一键领取",
    "活动领取",
    "市区巡逻",
    "事务所（解读仪式）",
    "外部招募",
    "补给站",
    "每周-阈限禁区",
    "危机行动调令",
    "联线封锁",
    "当期活动",
    "往期活动",
    "清体力",
    "退出游戏",
]


class NodeSink(TaskerEventSink):
    """只用于统计 Tasker.Task.* 事件；节点序列改从 TaskDetail.nodes 取（框架不发节点通知）。"""

    def __init__(self, debug: bool = False) -> None:
        self.events: list[tuple[float, str, dict]] = []
        self.debug = debug

    def on_raw_notification(self, tasker, msg: str, details: dict) -> None:
        self.events.append((time.time(), msg, details or {}))
        if self.debug:
            print(f"    [evt] {msg} {list((details or {}).keys())}")

    def msg_types(self) -> dict[str, int]:
        agg: dict[str, int] = {}
        for _t, msg, _d in self.events:
            agg[msg] = agg.get(msg, 0) + 1
        return agg


def load_adb_config():
    """从 MFA 实例配置读 adb 路径与设备地址（换机免改代码）。"""
    try:
        cfg = json.load(open(PI_CONFIG, encoding="utf-8"))
        adb = cfg.get("adb") or {}
        return adb.get("adb_path"), adb.get("address")
    except Exception:  # noqa: BLE001
        return None, None


def parse_extra_override(raw: str) -> dict:
    if not raw:
        return {}
    if os.path.exists(raw):
        with open(raw, encoding="utf-8") as f:
            return json.load(f)
    return json.loads(raw)


def build_override(task: dict, iface: dict, idx_map: dict[str, int]) -> dict:
    """把任务挂的 option 按用户实例选择合成 pipeline_override。"""
    ov: dict[str, dict] = {}
    for on in task.get("option") or []:
        cases = ((iface.get("option") or {}).get(on) or {}).get("cases") or []
        if not cases:
            continue
        idx = idx_map.get(on, 0)
        if not isinstance(idx, int) or idx >= len(cases):
            idx = 0
        for node, patch in (cases[idx].get("pipeline_override") or {}).items():
            ov.setdefault(node, {})
            if isinstance(patch, dict):
                ov[node].update(patch)
    return ov


def start_agent(resource, controller, tasker):
    """官方 AgentClient 流程拉起 agent 子进程（custom_action/recognition 都依赖它）。"""
    from maa.agent_client import AgentClient  # noqa: PLC0415

    py = os.path.join(ROOT, "python", "python.exe")
    main_py = os.path.join(ROOT, "agent", "main.py")
    if not os.path.exists(py) or not os.path.exists(main_py):
        print("  [warn] 找不到 python/agent 入口，跳过 agent（自定义动作会失败）")
        return None, None

    client = AgentClient()
    ident = client.identifier
    client.bind(resource)
    client.register_sink(resource, controller, tasker)
    proc = subprocess.Popen([py, main_py, ident], cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok = client.connect()
    print(f"  agent: identifier={ident} connected={ok}")
    return client, proc


def shot(adb: str, addr: str, tag: str) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    p = os.path.join(OUT_DIR, f"{tag}.png")
    with open(p, "wb") as f:
        subprocess.run([adb, "-s", addr, "exec-out", "screencap", "-p"],
                       stdout=f, stderr=subprocess.DEVNULL, timeout=30)
    return p


def fmt_seq(nodes: list[str], limit: int = 14) -> str:
    if len(nodes) <= limit:
        return " -> ".join(nodes)
    return " -> ".join(nodes[: limit // 2]) + f" ... ({len(nodes) - limit} 省略) ... " + \
           " -> ".join(nodes[-(limit // 2):])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="任务名，逗号分隔")
    ap.add_argument("--smoke", action="store_true", help="按 SMOKE_ORDER 全跑")
    ap.add_argument("--list", action="store_true", help="列出任务与 entry")
    ap.add_argument("--timeout", type=int, default=300, help="单任务超时秒（默认 300）")
    ap.add_argument("--debug", action="store_true", help="打印原始事件类型")
    ap.add_argument("--no-agent", action="store_true", help="不启动 agent（仅测无自定义动作的任务）")
    ap.add_argument("--override", default="", help="临时覆盖节点（JSON 字符串或 .json 文件路径）")
    ap.add_argument("--disable", default="", help="临时禁用节点（逗号分隔）")
    ap.add_argument("--adb", default="", help="adb 路径（默认读 config/maa_pi_config.json）")
    ap.add_argument("--address", default="", help="设备地址（默认读 config/maa_pi_config.json）")
    args = ap.parse_args()

    iface = pj.load_jsonc(os.path.join(ROOT, "interface.json"))
    tasks = {t["name"]: t for t in iface["task"]}

    if args.list:
        for n, t in tasks.items():
            print(f"{n:22s} {t['entry']:26s} option={len(t.get('option') or [])}")
        return 0

    if args.smoke:
        order = [n for n in SMOKE_ORDER if n in tasks]
    else:
        order = [s.strip() for s in args.only.split(",") if s.strip()]
    if not order:
        print("没有指定任务：用 --smoke 或 --only <任务名>（--list 看清单）")
        return 2
    missing = [n for n in order if n not in tasks]
    if missing:
        print("任务名不存在:", missing)
        return 2

    adb_path, address = load_adb_config()
    adb_path = args.adb or adb_path
    address = args.address or address
    if not adb_path or not address:
        print("未配置 adb：请在 config/maa_pi_config.json 的 adb.adb_path / adb.address 填好，"
              "或用 --adb / --address 指定")
        return 3

    inst_path = os.path.join(ROOT, "config", "instances", "default.json")
    idx_map = {}
    if os.path.exists(inst_path):
        inst = pj.load_jsonc(inst_path)
        for t in inst.get("TaskItems", []):
            for i in t.get("option") or []:
                if isinstance(i.get("index"), int):
                    idx_map[i["name"]] = i["index"]

    dev = Toolkit.find_adb_devices(adb_path)
    if not dev:
        print(f"未发现设备（adb={adb_path}）；确认模拟器已启动且 adb 连通")
        return 3
    target = next((d for d in dev if d.address == address), dev[0])
    c = AdbController(adb_path, target.address, target.screencap_methods,
                      target.input_methods, config={})
    c.post_connection().wait()
    if not c.connected:
        print("controller 连接失败")
        return 3
    r = Resource()
    r.post_bundle(os.path.join(ROOT, "resource", "base")).wait()
    if not r.loaded:
        print("资源加载失败")
        return 3
    t = Tasker()
    if not t.bind(r, c):
        print("tasker 绑定失败")
        return 3
    agent_client = agent_proc = None
    if not args.no_agent:
        agent_client, agent_proc = start_agent(r, c, t)
    sink = NodeSink(debug=args.debug)
    t.add_sink(sink)

    extra_ov = parse_extra_override(args.override)
    for n in [s.strip() for s in args.disable.split(",") if s.strip()]:
        extra_ov.setdefault(n, {})["enabled"] = False

    os.makedirs(OUT_DIR, exist_ok=True)
    report = []
    for name in order:
        task = tasks[name]
        ov = build_override(task, iface, idx_map)
        for node, patch in extra_ov.items():
            ov.setdefault(node, {})
            if isinstance(patch, dict):
                ov[node].update(patch)

        sink.events.clear()
        t0 = time.time()
        job = t.post_task(task["entry"], ov)
        timed_out = False
        while not job.done:
            if time.time() - t0 > args.timeout:
                timed_out = True
                t.post_stop().wait()
                break
            time.sleep(0.5)
        cost = round(time.time() - t0, 1)
        st = job.status

        seq: list[str] = []
        rows: list[dict] = []
        try:
            detail = job.wait().get()
            for nd in (getattr(detail, "nodes", None) or []):
                rd = nd.recognition
                ad = nd.action
                best = getattr(rd, "best_result", None) if rd else None
                row = {
                    "node": nd.name,
                    "reco": getattr(rd, "algorithm", None) if rd else None,
                    "hit": getattr(rd, "hit", None) if rd else None,
                    "action": str(getattr(ad, "action", "")) if ad else None,
                    "ok": getattr(nd, "completed", None),
                    "text": getattr(best, "text", None) if best else None,
                    "score": round(float(getattr(best, "score", 0) or 0), 4) if best else None,
                    "box": str(getattr(rd, "box", None)) if rd else None,
                }
                seq.append(nd.name)
                rows.append(row)
        except Exception as e:  # noqa: BLE001
            print("   [warn] 读取 TaskDetail 失败:", e)

        rec = {
            "task": name, "entry": task["entry"],
            "status": "succeeded" if st.succeeded else ("failed" if st.failed else str(st)),
            "timeout": timed_out, "seconds": cost,
            "node_count": len(seq), "nodes": seq, "rows": rows,
        }
        if timed_out or st.failed:
            rec["screenshot"] = shot(adb_path, target.address,
                                     f"{name}_{'timeout' if timed_out else 'fail'}")
        report.append(rec)

        flag = "TIMEOUT" if timed_out else ("OK " if st.succeeded else "FAIL")
        print(f"\n[{flag}] {name}  {cost}s  节点{len(seq)}  事件{len(sink.events)}")
        if args.debug and not seq:
            print("   事件类型:", sink.msg_types())
        print("   路径:", fmt_seq(seq))
        clicks = [x for x in rows if x.get("text")]
        if clicks:
            print("   识别明细:")
            for x in clicks:
                print(f"      {x['node']}: text={x['text']!r} score={x['score']} box={x['box']}")
        if rec.get("screenshot"):
            print("   截图:", rec["screenshot"])

    tag = time.strftime("%Y%m%d_%H%M%S")
    out = os.path.join(OUT_DIR, f"report_{tag}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("\n报告:", out)

    ok = sum(1 for x in report if x["status"] == "succeeded" and not x["timeout"])
    print(f"汇总: OK={ok} FAIL={sum(1 for x in report if x['status'] == 'failed')} "
          f"TIMEOUT={sum(1 for x in report if x['timeout'])} / {len(report)}")

    if agent_client is not None:
        try:
            agent_client.disconnect()
        except Exception:  # noqa: BLE001
            pass
    if agent_proc is not None:
        try:
            agent_proc.terminate()
        except Exception:  # noqa: BLE001
            pass
    return 0 if ok == len(report) else 1


if __name__ == "__main__":
    sys.exit(main())
