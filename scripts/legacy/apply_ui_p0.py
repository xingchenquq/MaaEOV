"""P0 界面配置落地：任务分组 / 顺序 / 默认勾选 / 默认选项（default_case）。

只改 interface.json，不触碰 pipeline 与 agent。
执行前自动备份到 backup/interface.json.bak-<ts>。
"""
import json
import shutil
import sys
import time
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if Path(__file__).parent.name == "local" else Path(__file__).resolve().parents[1]
IFACE = ROOT / "interface.json"

# ---------------------------------------------------------------- 分组定义
GROUPS = [
    ("Daily", "日常", "每天重置的领取与消耗，勾上跑一遍就够。", True),
    ("Cycle", "周期副本", "阈限禁区每周、认知海域双周、联线封锁每月各重置一次。", True),
    ("Event", "活动", "限时活动与活动关卡，换期后可能失效或改名。", True),
    ("System", "系统", "启动与退出游戏。", True),
]

# 任务改名（旧名 -> 新名），实例配置里也要同步迁移
RENAME = {"每周-阈限禁区": "阈限禁区"}

# ---------------------------------------------------------------- 任务顺序 + 归属 + 默认勾选
# 顺序即执行顺序，以用户给定的列表为准（2026-11-11）
TASKS = [
    ("启动游戏", "System", False),
    ("活动领取", "Daily", True),
    ("联线封锁", "Cycle", False),
    ("认知海域", "Cycle", False),
    ("阈限禁区", "Cycle", False),
    ("事务所（解读仪式）", "Daily", True),
    ("危机行动调令", "Daily", True),
    ("当期活动", "Event", False),
    ("往期活动", "Event", False),
    ("清体力", "Daily", True),
    ("外部招募", "Daily", True),
    ("补给站", "Daily", True),
    ("一键领取", "Daily", True),
    ("市区巡逻", "Daily", True),
    ("退出游戏", "System", False),
]

# ---------------------------------------------------------------- 任务图标（resource/base/image/ui/icons/）
ICON_DIR = "image/ui/icons"
ICONS = {
    "启动游戏": "task_start.png",
    "一键领取": "task_claim.png",
    "活动领取": "task_event_claim.png",
    "补给站": "task_supply.png",
    "市区巡逻": "task_patrol.png",
    "事务所（解读仪式）": "task_room.png",
    "外部招募": "task_recruit.png",
    "清体力": "task_stamina.png",
    "阈限禁区": "task_liminal.png",
    "联线封锁": "task_joint.png",
    "当期活动": "task_event_now.png",
    "往期活动": "task_event_past.png",
    "危机行动调令": "task_crisis.png",
    "认知海域": "task_sea.png",
    "退出游戏": "task_exit.png",
}

# ---------------------------------------------------------------- 预设配置
# 注意：ApplyPreset 会按 preset.task 重建任务列表 —— 预设里没列的任务会从界面上消失。
# 所以每个预设都必须把全部任务列全，只用 enabled 控制勾选状态。
ALL_TASKS = {n for n, _, _ in TASKS}
PRESETS = [
    {
        "name": "daily",
        "label": "日常一键",
        "description": "每天重置的 8 项：领取 + 消耗，一次跑完。\n\n不含周期副本与活动，省时间。",
        "enabled": {"活动领取", "事务所（解读仪式）", "危机行动调令", "清体力",
                    "外部招募", "补给站", "一键领取", "市区巡逻"},
    },
    {
        "name": "claim_only",
        "label": "只领取",
        "description": "只做零消耗的领取：邮件 / 补给站 / 日常奖励 / 巡逻奖励。\n\n不消耗体力、调令和任何道具。",
        "enabled": {"活动领取", "补给站", "一键领取", "市区巡逻"},
    },
    {
        "name": "full",
        "label": "全部",
        "description": "除「退出游戏」外全部勾选，用于完整清一遍。\n\n含周期副本与活动，耗时较长。",
        "enabled": ALL_TASKS - {"退出游戏"},
    },
]

# ---------------------------------------------------------------- 默认选项
# 原则：消耗稀缺资源 / 不可逆的操作默认 No；纯收益的领取默认 Yes。
DEFAULT_CASES = {
    # 开关类
    "放弃未完成的战斗": "No",                      # 保留关卡进度
    "阈限禁区-体力不足时使用体力道具": "No",         # 不烧体力道具
    "清体力-使用24小时内过期的体力道具": "Yes",      # 过期即浪费，用掉
    "消耗构想之钥追加档案残片": "No",                # 钥匙稀缺，不默认花
    "消耗构想之钥加速探员休息": "No",
    "分解剩余护符": "No",                          # 分解不可逆
    "一键领取-日常任务奖励": "Yes",
    "一键领取-周常任务奖励": "Yes",
    "一键领取-应对协议奖励": "Yes",
    "活动领取-邮件": "Yes",
    "活动领取-每日行动补给": "Yes",
    "活动领取-短期支援补贴": "Yes",
    "领取活动货柜奖励": "Yes",
    "银心奖章-银锡信息数据": "Yes",
    "银心奖章-外部招聘书": "Yes",
    "银心奖章-急务招聘书": "Yes",
    "紫心奖章-银锡信息数据": "Yes",
    "使用急务招聘书": "No",                        # 招聘书稀缺
    "放弃未完成的联线封锁挑战": "No",                # 放弃按当前进度结算，亏
    # 下拉类：把隐性默认（取第 0 项）显式声明，防止将来调整 cases 顺序导致行为静默改变
    "阈限禁区-选择关卡": "废弃枢纽",
    "清体力-选择关卡": "资源筹备-公平交易（行动资金）",
    "危机行动调令-选择关卡": "混合体 S001（心锚）",
    "解读仪式偏好": "行动资金",
    "当期活动-选择关卡": "AE110",
    "选择往期活动": "处理时间奇物的三项建议",
    "认知海域-目标层": "梦渊层",
    "认知海域-Buff配置": "配置一（原样）",
    "认知海域-券不足时自由探索": "No",              # 券不足直接收工，不打无奖励的探索轮
}


def main(apply: bool = True) -> int:
    raw = IFACE.read_text(encoding="utf-8")
    d = json.loads(raw, object_pairs_hook=OrderedDict)

    errors = []

    # ---- 校验：任务名必须存在且不重不漏（旧名视为新名）
    by_name = {}
    for t in d["task"]:
        by_name[RENAME.get(t.get("name"), t.get("name"))] = t
    plan_names = [n for n, _, _ in TASKS]
    if set(plan_names) != set(by_name):
        errors.append(f"任务集合不匹配:\n  缺: {set(by_name) - set(plan_names)}\n  多: {set(plan_names) - set(by_name)}")

    # ---- 校验：图标文件必须真实存在
    for name, fn in ICONS.items():
        p = ROOT / "resource" / "base" / ICON_DIR / fn
        if not p.is_file():
            errors.append(f"缺少图标文件: {p.relative_to(ROOT)}")

    # ---- 校验：预设引用的任务必须存在，且每个预设都要覆盖全部任务
    for ps in PRESETS:
        unknown = ps["enabled"] - ALL_TASKS
        if unknown:
            errors.append(f"预设 [{ps['name']}] 引用了不存在的任务: {unknown}")

    # ---- 校验：default_case 必须命中真实 case
    opt = d["option"]
    for key, val in DEFAULT_CASES.items():
        if key not in opt:
            errors.append(f"未找到 option: {key}")
            continue
        names = [c.get("name") for c in opt[key].get("cases", [])]
        if val not in names:
            errors.append(f"option [{key}] 无 case [{val}]，实际: {names}")
    for key in opt:
        if key not in DEFAULT_CASES:
            errors.append(f"option [{key}] 未指定 default_case")

    if errors:
        print("校验失败，未写入：")
        for e in errors:
            print(" -", e)
        return 1

    if not apply:
        print(f"校验通过：{len(TASKS)} 个任务 / {len(DEFAULT_CASES)} 个 option")
        return 0

    # ---- 1. 分组定义（插在 task 之前）
    groups = []
    for name, label, desc, expand in GROUPS:
        groups.append(OrderedDict([
            ("name", name),
            ("label", label),
            ("description", desc),
            ("default_expand", expand),
        ]))

    # ---- 2. 任务：按新顺序重排，补 icon / group / default_check
    # 这三个字段由本脚本全权管理，重跑时先剔除，避免旧值回灌
    MANAGED = {"icon", "group", "default_check"}
    new_tasks = []
    for name, group_name, checked in TASKS:
        t = by_name[name]
        # 保持原有字段顺序，把新字段插在 entry 之后
        out = OrderedDict()
        for k, v in t.items():
            if k in MANAGED:
                continue
            out[k] = v
            if k == "entry":
                out["icon"] = f"{ICON_DIR}/{ICONS[name]}"
                out["group"] = [group_name]
                if checked:
                    out["default_check"] = True
        # 没有 entry 的兜底（理论上不会发生）
        if "group" not in out:
            out["group"] = [group_name]
        # 改名：task.name 是唯一键，必须落到新名（OrderedDict 赋值保持原位）
        if out.get("name") in RENAME:
            out["name"] = RENAME[out["name"]]
        new_tasks.append(out)

    # ---- 3. option 补 default_case（放在 cases 之后）
    new_opt = OrderedDict()
    for key, val in opt.items():
        out = OrderedDict()
        for k, v in val.items():
            if k == "default_case":
                continue
            out[k] = v
            if k == "cases":
                out["default_case"] = DEFAULT_CASES[key]
        if "default_case" not in out:
            out["default_case"] = DEFAULT_CASES[key]
        new_opt[key] = out

    # ---- 4. 预设：列全所有任务，只用 enabled 控制勾选
    presets = []
    for ps in PRESETS:
        preset_tasks = []
        for tname, _, _ in TASKS:
            preset_tasks.append(OrderedDict([
                ("name", tname),
                ("enabled", tname in ps["enabled"]),
            ]))
        presets.append(OrderedDict([
            ("name", ps["name"]),
            ("label", ps["label"]),
            ("description", ps["description"]),
            ("task", preset_tasks),
        ]))

    # ---- 5. 组装顶层（保持原有 key 顺序，group 统一插在 task 前）
    result = OrderedDict()
    for k, v in d.items():
        if k in ("group", "preset"):
            continue
        if k == "task":
            result["group"] = groups
        if k == "option":
            result["preset"] = presets
        result[k] = v
    result["task"] = new_tasks
    result["option"] = new_opt
    if "preset" not in result:
        result["preset"] = presets

    if not apply:
        print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
        return 0

    bak = ROOT / "backup" / f"interface.json.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(IFACE, bak)
    IFACE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入 {IFACE.name}（备份: {bak.relative_to(ROOT)}）")
    print(f"  分组 {len(groups)} 个 / 任务 {len(new_tasks)} 个 / "
          f"default_case {len(new_opt)} 个 / 预设 {len(presets)} 套")
    return 0


if __name__ == "__main__":
    sys.exit(main(apply="--dry-run" not in sys.argv))
