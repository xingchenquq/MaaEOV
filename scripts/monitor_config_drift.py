# -*- coding: utf-8 -*-
"""配置漂移检测 + 模拟器状态监控。

用途：定时任务里「启动模拟器 → 逐项核对 MaaEOV 设置是否与预设一致 → 持续监控 → 出报告」。

为什么不用 GUI 校验：启动 MaaEOV.exe 会在退出时把内存里的任务列表写回
`config/instances/*.json`，等于自己改自己的基线，噪声大。这里的判据全部来自磁盘文件，
读的是 GUI **加载时**唯一权威的两份：`interface.json`（任务/选项定义）与
`config/instances/*.json`（用户实际勾选与选项值）。

用法：
    python scripts/monitor_config_drift.py snapshot           # 生成/更新基线
    python scripts/monitor_config_drift.py check              # 比对一次，退出码 0=一致 1=有偏差
    python scripts/monitor_config_drift.py watch --minutes 40 # 持续监控（默认 40 分钟，60s 一采样）
    python scripts/monitor_config_drift.py launch-emulator    # 启动模拟器并等 adb 就绪
    python scripts/monitor_config_drift.py all --minutes 40   # 启动 + 比对 + 监控（定时任务用这个）

产出：`debug/monitor/<时间戳>/` 下
    events.jsonl   每条采样/事件一行
    report.md      人读的报告（一致项 / 偏差项 / 异常）
退出码：0 = 全部一致且无异常；1 = 有偏差或异常（便于上层判断）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

import pj  # noqa: E402

IFACE = os.path.join(ROOT, "interface.json")
INST_DIR = os.path.join(ROOT, "config", "instances")
PI_CONFIG = os.path.join(ROOT, "config", "maa_pi_config.json")
BASELINE = os.path.join(ROOT, "config", "monitor_baseline.json")
MUMU_MANAGER = "D:/MuMu/nx_main/MuMuManager.exe"
MUMU_ADB = "D:/MuMu/nx_main/adb.exe"

#: 哈希只覆盖会改变行为的文件；图片/公告这类纯展示资源不纳入（改图标不该报"偏差"）。
HASH_GLOBS = ("resource/base/pipeline/*.json",)
#: 实例里会随 GUI 运行变化的字段，比对时忽略。
INSTANCE_IGNORE_FIELDS = (
    "ResolvedIcon", "HasIcon", "UI.LiveView.EnableLiveView",
    "CurrentController", "CurrentControllerName", "AdbDevice",
)
SEP = "<|||>"


# ---------------------------------------------------------------- 采集

def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _load_json(path: str) -> dict:
    try:
        return pj.load_jsonc(path)
    except Exception:  # noqa: BLE001
        return {}


def collect_interface() -> dict:
    d = _load_json(IFACE)
    tasks = []
    for t in d.get("task") or []:
        tasks.append({
            "name": t.get("name"),
            "entry": t.get("entry"),
            "group": t.get("group"),
            "icon": t.get("icon"),
            "default_check": bool(t.get("default_check")),
            "option": list(t.get("option") or []),
        })
    options = {}
    for k, o in (d.get("option") or {}).items():
        options[k] = {
            "default_case": o.get("default_case"),
            "cases": [c.get("name") for c in (o.get("cases") or [])],
        }
    return {
        "version": d.get("version"),
        "task_count": len(tasks),
        "tasks": tasks,
        "options": options,
        "groups": [g.get("name") for g in (d.get("group") or [])],
        "preset": [p.get("name") for p in (d.get("preset") or [])],
    }


def collect_instances() -> dict:
    out: dict[str, dict] = {}
    if not os.path.isdir(INST_DIR):
        return out
    for fn in sorted(os.listdir(INST_DIR)):
        if not fn.endswith(".json") or ".bak-" in fn:
            continue
        path = os.path.join(INST_DIR, fn)
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            out[fn] = {"_error": "无法解析"}
            continue
        items = []
        for t in d.get("TaskItems") or []:
            items.append({
                "name": t.get("name"),
                "entry": t.get("entry"),
                "default_check": bool(t.get("default_check")),
                "option": [{"name": o.get("name"), "index": o.get("index")}
                           for o in (t.get("option") or [])],
            })
        out[fn] = {
            "InstanceName": d.get("InstanceName"),
            "Resource": d.get("Resource"),
            "TaskItems": items,
            "CurrentTasks": [x.split(SEP)[0] for x in (d.get("CurrentTasks") or [])],
        }
    return out


def collect_files() -> dict:
    import glob  # noqa: PLC0415
    out = {"interface.json": _sha(IFACE)}
    for pattern in HASH_GLOBS:
        for p in sorted(glob.glob(os.path.join(ROOT, pattern))):
            out[os.path.relpath(p, ROOT).replace("\\", "/")] = _sha(p)
    return out


def collect_env() -> dict:
    cfg = _load_json(PI_CONFIG).get("adb") or {}
    return {"adb_path": cfg.get("adb_path"), "address": cfg.get("address")}


def snapshot() -> dict:
    return {
        "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "interface": collect_interface(),
        "instances": collect_instances(),
        "files": collect_files(),
        "env": collect_env(),
    }


# ---------------------------------------------------------------- 比对

def diff_settings(base: dict, now: dict) -> list[dict]:
    """逐项比对，只报"设置"层面的差异。返回 [{scope, item, expected, actual}]。"""
    out: list[dict] = []

    bi, ni = base.get("interface") or {}, now.get("interface") or {}
    for key in ("version", "task_count", "groups", "preset"):
        if bi.get(key) != ni.get(key):
            out.append({"scope": "interface", "item": key,
                        "expected": bi.get(key), "actual": ni.get(key)})

    b_tasks = {t["name"]: t for t in (bi.get("tasks") or [])}
    n_tasks = {t["name"]: t for t in (ni.get("tasks") or [])}
    for name in sorted(set(b_tasks) - set(n_tasks)):
        out.append({"scope": "interface.task", "item": name,
                    "expected": "存在", "actual": "缺失"})
    for name in sorted(set(n_tasks) - set(b_tasks)):
        out.append({"scope": "interface.task", "item": name,
                    "expected": "不存在", "actual": "新增"})
    for name in sorted(set(b_tasks) & set(n_tasks)):
        for f in ("entry", "group", "icon", "default_check", "option"):
            if b_tasks[name].get(f) != n_tasks[name].get(f):
                out.append({"scope": f"interface.task.{name}", "item": f,
                            "expected": b_tasks[name].get(f),
                            "actual": n_tasks[name].get(f)})

    b_opt = bi.get("options") or {}
    n_opt = ni.get("options") or {}
    for name in sorted(set(b_opt) | set(n_opt)):
        if b_opt.get(name) != n_opt.get(name):
            out.append({"scope": "interface.option", "item": name,
                        "expected": b_opt.get(name), "actual": n_opt.get(name)})

    b_inst = base.get("instances") or {}
    n_inst = now.get("instances") or {}
    for fn in sorted(set(b_inst) - set(n_inst)):
        out.append({"scope": "instance", "item": fn, "expected": "存在", "actual": "缺失"})
    for fn in sorted(set(n_inst) - set(b_inst)):
        out.append({"scope": "instance", "item": fn, "expected": "不存在", "actual": "新增"})
    for fn in sorted(set(b_inst) & set(n_inst)):
        b, n = b_inst[fn], n_inst[fn]
        if b.get("InstanceName") != n.get("InstanceName"):
            out.append({"scope": f"instance.{fn}", "item": "InstanceName",
                        "expected": b.get("InstanceName"), "actual": n.get("InstanceName")})
        b_items = {t["name"]: t for t in (b.get("TaskItems") or [])}
        n_items = {t["name"]: t for t in (n.get("TaskItems") or [])}
        for name in sorted(set(b_items) - set(n_items)):
            out.append({"scope": f"instance.{fn}.task", "item": name,
                        "expected": "在任务列表", "actual": "被移除"})
        for name in sorted(set(n_items) - set(b_items)):
            out.append({"scope": f"instance.{fn}.task", "item": name,
                        "expected": "不在任务列表", "actual": "被添加"})
        for name in sorted(set(b_items) & set(n_items)):
            b_o = {o["name"]: o["index"] for o in (b_items[name].get("option") or [])}
            n_o = {o["name"]: o["index"] for o in (n_items[name].get("option") or [])}
            for on in sorted(set(b_o) | set(n_o)):
                if b_o.get(on) != n_o.get(on):
                    out.append({"scope": f"instance.{fn}.option", "item": f"{name} / {on}",
                                "expected": f"index={b_o.get(on)}", "actual": f"index={n_o.get(on)}"})
        if b.get("CurrentTasks") != n.get("CurrentTasks"):
            out.append({"scope": f"instance.{fn}", "item": "CurrentTasks",
                        "expected": f"{len(b.get('CurrentTasks') or [])} 项",
                        "actual": f"{len(n.get('CurrentTasks') or [])} 项"})

    bf = base.get("files") or {}
    nf = now.get("files") or {}
    for name in sorted(set(bf) | set(nf)):
        if bf.get(name) != nf.get(name):
            out.append({"scope": "file", "item": name,
                        "expected": f"sha {bf.get(name) or '—'}",
                        "actual": f"sha {nf.get(name) or '—'}"})

    be = base.get("env") or {}
    ne = now.get("env") or {}
    for key in ("adb_path", "address"):
        if be.get(key) != ne.get(key):
            out.append({"scope": "env", "item": key,
                        "expected": be.get(key), "actual": ne.get(key)})
    return out


# ---------------------------------------------------------------- 环境

def _run(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return -1, str(e)


def emulator_pid() -> str:
    """MuMu 主程序进程（注意：主程序开着 ≠ 模拟器实例在跑，实例是否可用只看 adb）。"""
    rc, out = _run(["tasklist", "/FI", "IMAGENAME eq MuMuNxMain.exe", "/NH"])
    for line in out.splitlines():
        if "MuMuNxMain.exe" in line:
            for p in line.split():
                if p.isdigit():
                    return p
    return ""


def adb_devices(address: str = "") -> list[str]:
    rc, out = _run([MUMU_ADB, "devices"])
    devs = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("list of"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devs.append(parts[0])
    return devs


def adb_ensure(address: str) -> list[str]:
    """确保目标地址出现在 adb 列表里。

    ⚠️ 必须显式 connect：实测 adb server 重启（kill-server / 新进程拉起）之后，
    MuMu 实例只剩 `emulator-5554` 这一条，`127.0.0.1:16384` 会消失 ——
    而 MaaEOV 的控制器配的就是 `127.0.0.1:16384`，此时它会报找不到设备。
    所以判「在线」不能只看 devices，要先补连一次。
    """
    devs = adb_devices()
    if address and address not in devs:
        _run([MUMU_ADB, "connect", address], timeout=30)
        time.sleep(1)
        devs = adb_devices()
    return devs


def launch_emulator(address: str, wait_sec: int = 240) -> dict:
    """启动模拟器实例，等 adb 目标地址上线。

    ⚠️ 判据必须是 adb 而不是进程：实测 MuMu 主程序 (`MuMuNxMain.exe`) 常驻，
    但模拟器实例（跑游戏的那个）可以单独关掉 —— 那时 tasklist 里主程序还在，
    若按进程判「已在运行」就会误跳过启动，后面所有检测都对着空设备。
    实例进程是 `MuMuNxDevice.exe`；是否真正可用只看 adb 能不能连上。
    """
    rec = {"action": "launch_emulator", "ts": time.strftime("%H:%M:%S")}
    devs = adb_ensure(address)
    if address in devs:
        rec["already_running"] = True
        rec["devices"] = devs
        rec["ok"] = True
        return rec
    rc, out = _run([MUMU_MANAGER, "control", "-v", "0", "launch"], timeout=180)
    rec["launch_rc"] = rc
    rec["launch_out"] = out.strip()[:400]
    t0 = time.time()
    while time.time() - t0 < wait_sec:
        devs = adb_ensure(address)
        if address in devs:
            rec["adb_ready_after_s"] = round(time.time() - t0, 1)
            rec["devices"] = devs
            rec["ok"] = True
            return rec
        time.sleep(5)
    rec["ok"] = False
    rec["error"] = f"{wait_sec}s 内 adb 未就绪（{address}）"
    rec["devices"] = adb_devices()
    return rec


# ---------------------------------------------------------------- 报告

def write_report(outdir: str, title: str, diffs: list, events: list, samples: int) -> str:
    os.makedirs(outdir, exist_ok=True)
    lines = [f"# {title}", "",
             f"- 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}",
             f"- 采样次数：{samples}", ""]
    errs = [e for e in events if e.get("level") in ("error", "warn")]
    lines += ["## 结论", "",
              f"- 配置偏差：**{len(diffs)} 项**",
              f"- 异常事件：**{len(errs)} 条**", ""]
    if diffs:
        lines += ["## 不一致项", "", "| 范围 | 项 | 预设 | 实际 |", "|---|---|---|---|"]
        for d in diffs:
            lines.append(f"| `{d['scope']}` | {d['item']} | `{d['expected']}` | `{d['actual']}` |")
        lines.append("")
    else:
        lines += ["## 不一致项", "", "无。所有设置与预设一致。", ""]
    if errs:
        lines += ["## 异常事件", ""]
        for e in errs:
            lines.append(f"- `{e.get('ts')}` **{e.get('level')}** {e.get('kind')}：{e.get('detail')}")
        lines.append("")
    lines += ["## 事件流水", "", "```"]
    for e in events[-60:]:
        lines.append(f"{e.get('ts')} [{e.get('level')}] {e.get('kind')} {e.get('detail')}")
    lines += ["```", ""]
    path = os.path.join(outdir, "report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


class Journal:
    def __init__(self, outdir: str) -> None:
        self.outdir = outdir
        os.makedirs(outdir, exist_ok=True)
        self.path = os.path.join(outdir, "events.jsonl")
        self.events: list[dict] = []

    def log(self, level: str, kind: str, detail: str) -> dict:
        e = {"ts": time.strftime("%H:%M:%S"), "level": level, "kind": kind, "detail": detail}
        self.events.append(e)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
        flag = {"info": "  ", "warn": "! ", "error": "!!"}.get(level, "  ")
        print(f"{flag}{e['ts']} {kind}: {detail}")
        return e


def _outdir(tag: str) -> str:
    d = os.path.join(ROOT, "debug", "monitor", f"{time.strftime('%Y%m%d_%H%M%S')}_{tag}")
    os.makedirs(d, exist_ok=True)
    return d


# ---------------------------------------------------------------- 主流程

def cmd_snapshot() -> int:
    snap = snapshot()
    os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
    with open(BASELINE, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    print(f"基线已写入 {os.path.relpath(BASELINE, ROOT)}")
    print(f"  interface {snap['interface']['version']} / {snap['interface']['task_count']} 任务 "
          f"/ {len(snap['interface']['options'])} 选项")
    for fn, d in snap["instances"].items():
        print(f"  {fn} ({d.get('InstanceName')}) {len(d.get('TaskItems') or [])} 任务")
    print(f"  文件哈希 {len(snap['files'])} 个")
    return 0


def cmd_check(baseline_path: str = BASELINE, quiet: bool = False) -> tuple[int, list, str]:
    if not os.path.exists(baseline_path):
        print(f"缺少基线：{baseline_path}\n先跑 `snapshot` 落一份。")
        return 2, [], ""
    base = json.load(open(baseline_path, encoding="utf-8"))
    now = snapshot()
    diffs = diff_settings(base, now)
    if not quiet:
        if not diffs:
            print(f"[一致] 与基线（{base.get('captured_at')}）无差异")
        else:
            print(f"[偏差] {len(diffs)} 项与基线（{base.get('captured_at')}）不一致：")
            for d in diffs:
                print(f"  - {d['scope']} / {d['item']}: 预设={d['expected']!r} 实际={d['actual']!r}")
    return (0 if not diffs else 1), diffs, base.get("captured_at", "")


def cmd_watch(minutes: int, interval: int, outdir: str, journal: Journal,
              baseline_path: str = BASELINE) -> int:
    cfg = collect_env()
    address = cfg.get("address") or "127.0.0.1:16384"
    end = time.time() + minutes * 60
    samples = 0
    last_diffs: list = []
    last_sig = None
    while time.time() < end:
        samples += 1
        # 1) 模拟器实例 + adb（判据是 adb 在线，不是主程序进程）
        pid = emulator_pid()
        devs = adb_devices()
        if address not in devs:
            # 地址掉了先尝试补连（adb server 重启会让 127.0.0.1:<port> 消失），再判是否真掉线
            devs = adb_ensure(address)
            if address in devs:
                # 补连成功记 info：这是 adb server 重启后的正常恢复，不算设置偏差
                journal.log("info", "adb", f"补连 {address} 成功（当前设备 {devs}）")
        online = address in devs
        sig = (bool(pid), online, tuple(devs))
        if sig != last_sig:
            if not online:
                journal.log("error", "adb",
                            f"adb 里没有 {address}（当前设备 {devs or '无'}，MuMu 主程序 "
                            f"{'在' if pid else '不在'}）→ 模拟器实例已关闭或掉线")
            else:
                journal.log("info", "env", f"模拟器在线 pid={pid or '?'} adb={address}")
            last_sig = sig
        elif not online:
            journal.log("error", "adb", f"第 {samples} 次采样仍无 {address}，持续离线")

        # 2) 配置漂移
        rc, diffs, _ = cmd_check(baseline_path, quiet=True)
        if diffs != last_diffs:
            if diffs:
                for d in diffs:
                    journal.log("warn", "drift",
                                f"{d['scope']} / {d['item']}: 预设={d['expected']!r} → 实际={d['actual']!r}")
            else:
                journal.log("info", "drift", "配置已恢复与预设一致")
            last_diffs = diffs

        time.sleep(max(5, interval))
    return samples


def cmd_all(minutes: int, interval: int) -> int:
    outdir = _outdir("all")
    j = Journal(outdir)
    cfg = collect_env()
    address = cfg.get("address") or "127.0.0.1:16384"

    j.log("info", "start", f"开始：目标 adb={address}，监控 {minutes} 分钟 / {interval}s 一采样")

    rec = launch_emulator(address)
    j.log("info" if rec.get("ok") else "error", "launch", json.dumps(rec, ensure_ascii=False))

    rc, diffs, base_ts = cmd_check()
    if rc == 2:
        j.log("error", "baseline", "缺少基线文件，无法比对设置")
    elif diffs:
        j.log("warn", "drift", f"检测到 {len(diffs)} 项不一致（基线 {base_ts}）")
    else:
        j.log("info", "drift", f"设置与基线完全一致（基线 {base_ts}）")

    n_samples = cmd_watch(minutes, interval, outdir, j)

    # 结束后再比对一次，抓"监控期间被改动"的最终状态
    rc2, diffs2, _ = cmd_check(quiet=True)
    if diffs2 != diffs:
        j.log("warn" if diffs2 else "info", "drift_final",
              f"监控结束时偏差 {len(diffs2)} 项" + ("" if diffs2 else "（已恢复）"))
    report = write_report(outdir, "MaaEOV 配置核对与运行监控", diffs2 or diffs, j.events, n_samples)
    print(f"\n报告：{report}")
    bad = bool(diffs2 or diffs) or any(e["level"] in ("error", "warn") for e in j.events)
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["snapshot", "check", "watch", "launch-emulator", "all"])
    ap.add_argument("--minutes", type=int, default=40, help="监控时长（分钟，默认 40）")
    ap.add_argument("--interval", type=int, default=60, help="采样间隔（秒，默认 60）")
    ap.add_argument("--baseline", default=BASELINE)
    args = ap.parse_args()

    if args.cmd == "snapshot":
        return cmd_snapshot()
    if args.cmd == "check":
        return cmd_check(args.baseline)[0]
    if args.cmd == "launch-emulator":
        rec = launch_emulator(collect_env().get("address") or "127.0.0.1:16384")
        print(json.dumps(rec, ensure_ascii=False, indent=1))
        return 0 if rec.get("ok") else 1
    if args.cmd == "watch":
        outdir = _outdir("watch")
        j = Journal(outdir)
        j.log("info", "start", f"开始监控 {args.minutes} 分钟 / {args.interval}s")
        n = cmd_watch(args.minutes, args.interval, outdir, j, args.baseline)
        print(f"\n报告：{write_report(outdir, 'MaaEOV 运行监控', [], j.events, n)}")
        return 0
    return cmd_all(args.minutes, args.interval)


if __name__ == "__main__":
    sys.exit(main())
