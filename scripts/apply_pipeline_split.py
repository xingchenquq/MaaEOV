# -*- coding: utf-8 -*-
"""真迁移：把 Tasks.json 拆出的多文件正式写入 resource/base/pipeline/。

步骤（先备份，再落地）：
1. 将当前 resource/base/pipeline/ 全部文件备份到 temp/_pipeline_backup/<时间戳>/。
2. 把 temp/pipeline_split/pipeline/ 下的拆分文件复制进 resource/base/pipeline/。
3. 删除 resource/base/pipeline/Tasks.json（内容已拆入多文件）。
4. 打印结果文件清单。

不修改 推图.json / 认知海域.json。
"""
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_PIPE = os.path.join(ROOT, "resource", "base", "pipeline")
SPLIT_PIPE = os.path.join(ROOT, "temp", "pipeline_split", "pipeline")
BACKUP_ROOT = os.path.join(ROOT, "temp", "_pipeline_backup")
TASKS = "Tasks.json"


def main():
    if not os.path.isdir(SPLIT_PIPE):
        print("ERROR: split dir not found: %s" % SPLIT_PIPE)
        return 2
    split_files = sorted(f for f in os.listdir(SPLIT_PIPE) if f.endswith(".json"))
    if len(split_files) < 2:
        print("ERROR: split dir has too few json: %d" % len(split_files))
        return 2

    ts = time.strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_ROOT, ts)
    os.makedirs(backup, exist_ok=True)
    before = sorted(f for f in os.listdir(SRC_PIPE) if f.endswith(".json"))
    for fn in before:
        shutil.copy(os.path.join(SRC_PIPE, fn), os.path.join(backup, fn))
    print("BACKUP -> %s (%d files)" % (backup, len(before)))

    for fn in split_files:
        shutil.copy(os.path.join(SPLIT_PIPE, fn), os.path.join(SRC_PIPE, fn))
    print("COPIED split files: %d" % len(split_files))

    tasks_path = os.path.join(SRC_PIPE, TASKS)
    if os.path.exists(tasks_path):
        os.remove(tasks_path)
        print("REMOVED %s" % TASKS)
    else:
        print("NOTE: %s not present (already migrated?)" % TASKS)

    after = sorted(f for f in os.listdir(SRC_PIPE) if f.endswith(".json"))
    print("PIPELINE NOW (%d files):" % len(after))
    for fn in after:
        print("  - %s" % fn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
