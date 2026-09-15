#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包「资源更新包」MaaEOV-resource.zip —— 供 MFAAvalonia 通过 GitHub Releases 做资源自动更新。

依据（MFAAvalonia VersionChecker.cs 已核实）：
- 资源包解压后，GUI 会把包内 interface.json 的 version 改写为 release tag 并写回应用根目录，
  同时把包内 resource/ 覆盖合并到应用资源目录。
- 因此资源包【必须】同时包含 interface.json（含正确版本）与 resource/，否则本地版本号不涨，
  会每次启动都重复提示更新。
- zip 内部布局（与 MFAAvalonia 期望一致）：
      MaaEOV-resource.zip
      ├── interface.json      # 完整 interface.json（version 与 release tag 一致）
      └── resource/
          ├── base/
          ├── announcement/Changelog.md
          └── mfa_layout.json

用法
----
    python scripts/pack_resource.py
    python scripts/pack_resource.py --version v1.12
    python scripts/pack_resource.py --out dist/MaaEOV-resource.zip
    python scripts/pack_resource.py --resource-only     # 仅打 resource/（不推荐，见上）
"""
import os
import sys
import json
import zipfile
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCE_DIR = os.path.join(ROOT, "resource")
INTERFACE_JSON = os.path.join(ROOT, "interface.json")
DEFAULT_OUT = os.path.join(ROOT, "MaaEOV-resource.zip")

# 资源包内不应出现的目录 / 扩展名
EXCLUDE_DIRS = {".git", "__pycache__"}
EXCLUDE_EXTS = {".pyc"}


def iter_resource_files():
    for dirpath, dirnames, filenames in os.walk(RESOURCE_DIR):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            ext = os.path.splitext(fn)[1].lower()
            if ext in EXCLUDE_EXTS:
                continue
            arcname = os.path.relpath(full, ROOT).replace(os.sep, "/")
            yield full, arcname


def load_interface(version_override=None):
    with open(INTERFACE_JSON, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if version_override:
        data["version"] = version_override
    return data


def pack(out_path, version_override=None, resource_only=False):
    if not os.path.isdir(RESOURCE_DIR):
        print(f"[ERROR] resource/ 不存在: {RESOURCE_DIR}")
        sys.exit(1)
    parent = os.path.dirname(os.path.abspath(out_path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)

    count = 0
    total_bytes = 0
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1) interface.json 作为更新包根文件（含版本号，供 MFAAvalonia 回写）
        if not resource_only:
            if not os.path.isfile(INTERFACE_JSON):
                print(f"[ERROR] 缺少 interface.json: {INTERFACE_JSON}")
                sys.exit(1)
            data = load_interface(version_override)
            zf.writestr("interface.json",
                        json.dumps(data, ensure_ascii=False, indent=2))
            count += 1
            total_bytes += os.path.getsize(INTERFACE_JSON)
            print(f"[OK] 写入 interface.json (version={data.get('version')})")

        # 2) resource/ 整体
        for full, arcname in iter_resource_files():
            zf.write(full, arcname)
            count += 1
            total_bytes += os.path.getsize(full)

    # 校验
    with zipfile.ZipFile(out_path, "r") as zf:
        bad = zf.testzip()
    if bad is not None:
        print(f"[ERROR] 压缩包损坏: {bad}")
        sys.exit(1)

    size_mb = total_bytes / 1e6
    print(f"[OK] 已生成资源包: {out_path}")
    print(f"     文件数: {count}  大小: {size_mb:.2f} MB")
    names = zipfile.ZipFile(out_path).namelist()
    print(f"     含 interface.json: {'interface.json' in names}  "
          f"含 resource/: {any(n.startswith('resource/') for n in names)}")


def main():
    ap = argparse.ArgumentParser(description="打包 MaaEOV 资源更新包")
    ap.add_argument("--out", default=DEFAULT_OUT, help="输出 zip 路径")
    ap.add_argument("--version", default=None,
                    help="覆盖写入包内 interface.json 的 version（默认沿用当前文件）")
    ap.add_argument("--resource-only", action="store_true",
                    help="仅打 resource/（不推荐：缺 interface.json 会导致重复更新提示）")
    args = ap.parse_args()
    pack(args.out, args.version, args.resource_only)


if __name__ == "__main__":
    main()
