"""给下拉类 option 的 case 补短 label。

`name` 是 pipeline_override / 实例配置的键，绝不能动；
`label` 只影响界面显示（MaaInterfaceOptionCase.DisplayName 优先取 label）。

只处理 select 类长名单，17 组 Yes/No 双 case 不动
（TaskOptionGenerator 靠「case 数==2 且名字含 yes/no」判定是否渲染成开关）。
"""
import json
import re
import shutil
import sys
import time
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IFACE = ROOT / "interface.json"

# 需要加 label 的 option（长名单）
TARGETS = ["清体力-选择关卡", "危机行动调令-选择关卡", "解读仪式偏好"]

PREFIX_RES = ("资源筹备-", "晋阶考核-", "阈限禁区-")


def short(name: str) -> str:
    n = name

    if n.startswith("活动关卡"):
        return "活动关卡（常驻）"

    if n.startswith("资源筹备-"):
        # 保留资源类型，去掉分类前缀：资源筹备-公平交易（行动资金） -> 公平交易（行动资金）
        return n[len("资源筹备-"):]

    if n.startswith("晋阶考核-"):
        # 晋阶考核-火线特攻G601（技能/时装升级材料） -> 火线特攻 G601
        body = n[len("晋阶考核-"):]
        body = re.sub(r"（[^）]*）$", "", body)
        body = re.sub(r"(?<=\D)(G\d+)$", r" \1", body)
        return body

    if n.startswith("阈限禁区-"):
        body = n[len("阈限禁区-"):]
        body = re.sub(r"（[^）]*）$", "", body)
        return f"{body}（阈限）"

    # 混合体 S001（心锚）/ 罪与罚 S701（紫心奖章） -> 去掉末尾括号
    return re.sub(r"（[^）]*）$", "", n)


def main(apply: bool = True) -> int:
    d = json.loads(IFACE.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)
    opt = d["option"]

    errors, plan = [], {}
    for key in TARGETS:
        if key not in opt:
            errors.append(f"未找到 option: {key}")
            continue
        labels, mapping = [], OrderedDict()
        for case in opt[key].get("cases", []):
            name = case.get("name")
            lb = short(name)
            if not lb:
                errors.append(f"[{key}] {name} 生成了空 label")
            if lb in labels:
                errors.append(f"[{key}] label 重复: {lb}（来自 {name}）")
            labels.append(lb)
            mapping[name] = lb
        plan[key] = mapping

    if errors:
        print("校验失败，未写入：")
        for e in errors:
            print(" -", e)
        return 1

    for key, mapping in plan.items():
        print(f"== {key}（{len(mapping)} 项）")
        for name, lb in list(mapping.items())[:6]:
            print(f"   {name}  ->  {lb}")
        if len(mapping) > 6:
            print(f"   …共 {len(mapping)} 项")

    if not apply:
        print("\n[dry-run] 未写入")
        return 0

    for key, mapping in plan.items():
        new_cases = []
        for case in opt[key]["cases"]:
            out = OrderedDict()
            for k, v in case.items():
                if k == "label":
                    continue
                out[k] = v
                if k == "name":
                    out["label"] = mapping[case["name"]]
            new_cases.append(out)
        opt[key]["cases"] = new_cases

    bak = ROOT / "backup" / f"interface.json.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(IFACE, bak)
    IFACE.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(len(m) for m in plan.values())
    print(f"\n已写入 {total} 个 case label（备份 {bak.name}）")
    return 0


if __name__ == "__main__":
    sys.exit(main(apply="--dry-run" not in sys.argv))
