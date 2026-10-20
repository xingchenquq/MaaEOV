#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MaaEOV 工作目录整理工具（配套 docs/重构与目录整理方案-2026-10-20.md）。

默认**只读盘点**，任何写操作都必须显式给子命令 + `--apply`。

用法
----
    python scripts/migrate_layout.py                      # 盘点：分类、体积、可回收空间
    python scripts/migrate_layout.py images --apply       # image 根散图归位到 BCR/ 并改写引用
    python scripts/migrate_layout.py archive --apply      # 已跟踪的一次性脚本归档到 scripts/legacy/
    python scripts/migrate_layout.py purge --yes          # 删除过期产物（旧完整包 / 重复资源包）

设计约束
--------
1. 不碰 MFA 强制的目录位置：interface.json / resource/ / agent/ / config/ / debug/ / logs/
   必须留在程序根，移动即失效。
2. `images` 只做**文本级**字符串替换（`"x.png"` -> `"BCR/x.png"`），不 json.load/dump，
   否则 pipeline 里的 `//` 注释会被整体丢弃。
3. `purge` 只删本脚本白名单内的产物，且必须 `--yes`；不做递归删除。
4. 未跟踪的本机专用脚本（.gitignore 列出的 16 个）不在本脚本处理范围——它们含本机绝对
   路径，处置需人工确认。
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_ROOT = os.path.join(ROOT, "resource", "base", "image")
PIPELINE_DIR = os.path.join(ROOT, "resource", "base", "pipeline")
INTERFACE = os.path.join(ROOT, "interface.json")

# ── 分类定义（用于 report） ────────────────────────────────────────────────
RUNTIME_REQUIRED = {
    "interface.json", "resource", "agent", "config", "Assets",
    "python", "runtimes", "libs", "plugins",
    "MaaEOV.exe", "MaaEOV.desktop", "SukiUI.xml", "appsettings.json",
    "av_libglesv2.dll", "libHarfBuzzSharp.dll", "libSkiaSharp.dll",
    "libonigwrap.dll", "miniaudio.dll", "uiohook.dll",
    "DependencySetup_依赖库安装_win.bat",
}
DEV_ASSETS = {"scripts", "docs", "开发记录.md", "README.md", "LICENSE", ".github", ".gitignore",
              "package_full.py", "build_resource_zip.py"}
RUNTIME_OUTPUT = {"debug", "logs", "temp", "backup", "dist", ".mfa_build", ".nicegui", ".mimosa", ".workbuddy"}
VCS_ONLY = {".git"}

# ── image 散图归位映射（全部为 BCR 子系统图，见方案文档 §4.3） ──────────────
IMAGE_MAP = {
    "公平交易.png": "BCR",
    "共时性.png": "BCR",
    "危机行动.png": "BCR",
    "危机行动调令.png": "BCR",
    "特别行动.png": "BCR",
    "巅峰时刻.png": "BCR",
    "火线特攻.png": "BCR",
    "虎胆龙威.png": "BCR",
    "铜墙铁壁.png": "BCR",
    "诡形物语.png": "BCR",
}

# ── 归档清单：仅处理「已被 git 跟踪」的一次性脚本（保留历史，入库合规） ──────
LEGACY_TRACKED = [
    "add_soc_focus.py",
    "apply_pipeline_split.py",
    "crop_soc_templates.py",
    "migrate_pipeline_v5.py",
    "recrop_ibb.py",
    "recrop_soc_buff_templates.py",
    "soc_trace.py",
    "split_pipeline.py",
]

# ── 清理白名单（相对路径，精确匹配，不做通配） ──────────────────────────────
PURGE_ALLOW = [
    "dist/MaaEOV-v1.14.6-full-package.zip",  # 已被 v1.14.7 取代，Release 有存档
    "MaaEOV-resource.zip",                    # 与 dist/MaaEOV-<ver>-resource-win-x64.zip 重复
]


def human(n):
    for unit in ("B", "K", "M", "G"):
        if n < 1024 or unit == "G":
            return f"{n:.1f}{unit}" if unit != "B" else f"{n:.0f}B"
        n /= 1024
    return f"{n:.1f}G"


def du(path):
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for dp, _dn, fns in os.walk(path):
        for f in fns:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return total


def tracked(rel):
    """该相对路径是否被 git 跟踪。"""
    try:
        r = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel],
            cwd=ROOT, capture_output=True, text=True,
        )
        return r.returncode == 0
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════
# report
# ══════════════════════════════════════════════════════════════════════════
def cmd_report(_args):
    print("=" * 72)
    print("MaaEOV 目录盘点  (root = %s)" % ROOT)
    print("=" * 72)

    groups = {
        "运行必需（MFA 强制位置，不可移动）": RUNTIME_REQUIRED,
        "开发资产（建议分层整理）": DEV_ASSETS,
        "运行期产物（不入库，可清理）": RUNTIME_OUTPUT,
        "版本控制内部": VCS_ONLY,
    }
    seen = set()
    for title, names in groups.items():
        print("\n[%s]" % title)
        for name in sorted(names):
            p = os.path.join(ROOT, name)
            if not os.path.exists(p):
                continue
            seen.add(name)
            if name in VCS_ONLY:
                print("  %-42s %8s  vcs" % (name, human(du(p))))
                continue
            flag = "tracked" if tracked(name) else "untracked"
            print("  %-42s %8s  %s" % (name, human(du(p)), flag))

    unknown = [n for n in os.listdir(ROOT) if n not in seen]
    if unknown:
        print("\n[未归类]")
        for n in sorted(unknown):
            p = os.path.join(ROOT, n)
            print("  %-42s %8s" % (n, human(du(p))))

    # 可回收空间
    print("\n" + "-" * 72)
    print("[可回收空间]")
    reclaim = 0
    for rel in PURGE_ALLOW:
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            s = os.path.getsize(p)
            reclaim += s
            print("  %-52s %8s" % (rel, human(s)))
    print("  合计 %.0f MB（用 `purge --yes` 执行）" % (reclaim / 1024 / 1024))

    # 散图
    loose = sorted(
        f for f in os.listdir(IMAGE_ROOT)
        if f.lower().endswith(".png") and os.path.isfile(os.path.join(IMAGE_ROOT, f))
    )
    print("\n[image/ 根散图] %d 张（用 `images --apply` 归位）" % len(loose))
    for f in loose:
        print("  %-24s -> %s/" % (f, IMAGE_MAP.get(f, "（未映射，需人工决定）")))

    # 归档
    print("\n[待归档的一次性脚本]")
    for f in LEGACY_TRACKED:
        p = os.path.join(ROOT, "scripts", f)
        if os.path.exists(p):
            print("  scripts/%-40s -> scripts/legacy/  (%s)"
                  % (f, "tracked" if tracked("scripts/" + f) else "untracked，跳过"))
    return 0


# ══════════════════════════════════════════════════════════════════════════
# images
# ══════════════════════════════════════════════════════════════════════════
def cmd_images(args):
    loose = sorted(
        f for f in os.listdir(IMAGE_ROOT)
        if f.lower().endswith(".png") and os.path.isfile(os.path.join(IMAGE_ROOT, f))
    )
    if not loose:
        print("image/ 根目录无散图，无需处理。")
        return 0

    unmapped = [f for f in loose if f not in IMAGE_MAP]
    if unmapped:
        print("[FAIL] 以下散图未在 IMAGE_MAP 中定义目标目录，请先补充映射：")
        for f in unmapped:
            print("  " + f)
        return 1

    # 目标 JSON：pipeline 全部 + interface
    targets = [INTERFACE] + [
        os.path.join(PIPELINE_DIR, f) for f in sorted(os.listdir(PIPELINE_DIR))
        if f.endswith(".json")
    ]

    print("=" * 72)
    print("image 散图归位 %d 张" % len(loose))
    print("=" * 72)

    plan = []
    for f in loose:
        dst_dir = os.path.join(IMAGE_ROOT, IMAGE_MAP[f])
        old_ref = f
        new_ref = "%s/%s" % (IMAGE_MAP[f], f)
        hit_files = []
        for t in targets:
            if not os.path.exists(t):
                continue
            src = open(t, encoding="utf-8").read()
            if '"%s"' % old_ref in src:
                hit_files.append(t)
        plan.append((f, dst_dir, old_ref, new_ref, hit_files))

    for f, dst_dir, old_ref, new_ref, hit_files in plan:
        print("  %-22s -> %s/   引用 %d 个文件（%s）"
              % (f, IMAGE_MAP[f], len(hit_files),
                 ", ".join(os.path.basename(h) for h in hit_files) or "-"))

    if not args.apply:
        print("\n[DRY-RUN] 未做任何修改。加 --apply 执行。")
        return 0

    # 1) 移动图片
    for f, dst_dir, _o, _n, _h in plan:
        os.makedirs(dst_dir, exist_ok=True)
        src = os.path.join(IMAGE_ROOT, f)
        dst = os.path.join(dst_dir, f)
        if os.path.exists(dst):
            print("  [SKIP] 目标已存在：%s" % dst)
            continue
        shutil.move(src, dst)

    # 2) 文本级改写引用（保留注释与格式）
    changed = 0
    for t in targets:
        if not os.path.exists(t):
            continue
        src = open(t, encoding="utf-8").read()
        out = src
        for f, _d, old_ref, new_ref, _h in plan:
            out = out.replace('"%s"' % old_ref, '"%s"' % new_ref)
        if out != src:
            open(t, "w", encoding="utf-8", newline="\n").write(out)
            changed += 1
            print("  [改] %s" % os.path.relpath(t, ROOT))

    print("\n[DONE] 移动 %d 张图，改写 %d 个文件。" % (len(plan), changed))
    print("下一步：python scripts/verify_feature.py  （必须 ALL_OK）")
    return 0


# ══════════════════════════════════════════════════════════════════════════
# archive
# ══════════════════════════════════════════════════════════════════════════
def cmd_archive(args):
    dst_dir = os.path.join(ROOT, "scripts", "legacy")
    print("=" * 72)
    print("一次性脚本归档 -> scripts/legacy/")
    print("=" * 72)

    todo = []
    for f in LEGACY_TRACKED:
        rel = "scripts/" + f
        if not os.path.exists(os.path.join(ROOT, rel)):
            continue
        if not tracked(rel):
            print("  [SKIP] %-40s 未被 git 跟踪（本机专用，人工处置）" % rel)
            continue
        todo.append(f)
        print("  %-40s -> scripts/legacy/%s" % (rel, f))

    if not todo:
        print("  无需处理。")
        return 0
    if not args.apply:
        print("\n[DRY-RUN] 未做任何修改。加 --apply 执行（使用 git mv 保留历史）。")
        return 0

    os.makedirs(dst_dir, exist_ok=True)
    for f in todo:
        subprocess.run(["git", "mv", "scripts/" + f, "scripts/legacy/" + f],
                       cwd=ROOT, check=True)
        print("  [MOVE] scripts/%s -> scripts/legacy/%s" % (f, f))

    print("\n[DONE] 已归档 %d 个脚本。" % len(todo))
    print("下一步：")
    print("  1) 更新 scripts/README.md 中的路径（legacy 章节）")
    print("  2) 检查 .github/workflows、package_full.py 是否引用了被移动的文件")
    return 0


# ══════════════════════════════════════════════════════════════════════════
# purge
# ══════════════════════════════════════════════════════════════════════════
def cmd_purge(args):
    print("=" * 72)
    print("清理过期产物（白名单，不回收到回收站）")
    print("=" * 72)

    existing = [(rel, os.path.join(ROOT, rel)) for rel in PURGE_ALLOW
                if os.path.exists(os.path.join(ROOT, rel))]
    if not existing:
        print("  无匹配文件。")
        return 0

    total = 0
    print("\n将被删除：")
    for rel, p in existing:
        s = du(p)
        total += s
        print("  %-52s %8s" % (rel, human(s)))
    print("  合计 %.0f MB" % (total / 1024 / 1024))

    if not args.yes:
        print("\n[中止] 未给 --yes，未删除任何文件。")
        print("确认执行：python scripts/migrate_layout.py purge --yes")
        return 0

    for rel, p in existing:
        os.remove(p)
        print("  [DEL] %s" % rel)
    print("\n[DONE] 释放 %.0f MB" % (total / 1024 / 1024))
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="MaaEOV 目录整理工具（默认只读盘点）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("report", help="只读盘点（默认命令）")

    p_img = sub.add_parser("images", help="image 根散图归位并改写引用")
    p_img.add_argument("--apply", action="store_true", help="实际执行（默认 dry-run）")

    p_arc = sub.add_parser("archive", help="一次性脚本归档到 scripts/legacy/")
    p_arc.add_argument("--apply", action="store_true", help="实际执行（默认 dry-run）")

    p_pur = sub.add_parser("purge", help="删除白名单内的过期产物")
    p_pur.add_argument("--yes", action="store_true", help="确认删除")

    args = ap.parse_args()
    if args.cmd is None or args.cmd == "report":
        return cmd_report(args)
    if args.cmd == "images":
        return cmd_images(args)
    if args.cmd == "archive":
        return cmd_archive(args)
    if args.cmd == "purge":
        return cmd_purge(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
