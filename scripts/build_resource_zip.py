import os, zipfile, json

# 资源 OTA 包构建（参照 Maadori 拆包发版规范，2026-10-05 适配 MaaEOV）
#
# 关键约束（MaaEOV 与 Maadori 同宿主 MFAAvalonia，GitHub 源「检查更新」恒为全量更新）：
#   1. 全量更新会无条件删除用户侧 resource/ 与 agent/，再按包内容复制。
#      → 本包【必须含完整 agent/】，否则会把用户 agent/ 删空、程序失效。
#   2. 本包【绝不含 MFA 程序文件】（exe/dll/runtimes/libs/python/plugins 等），
#      否则触发 MFA「二合一」：运行时 exe 改名 .backupMFA、主入口判成 MFAAvalonia.exe、
#      用户 config 被覆盖，旧版还会卡 70% 回滚。
#   3. 包名带 win-x64 → MFA GetAssetPriority 给 100 分，稳定胜出「检查更新」，
#      完整包（无平台词）0 分不会被误选。
#
# 内容：根 interface.json + resource/ + agent/（排除字节码/缓存/运行期产物）。

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 本脚本在 <root>/scripts/ 下
VER = json.load(open(os.path.join(ROOT, 'interface.json'), encoding='utf-8'))['version']
OUT_DIR = os.path.join(ROOT, 'dist')  # 与完整包同目录，便于一起发布
os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, 'MaaEOV-%s-resource-win-x64.zip' % VER)

# 排除目录：原始素材截图源 / 字节码缓存 / 运行期产物 / 版本控制 / 运行时配置
EXCLUDE_DIRS = {
    'resource/base/image/SeaOfCognition/raw',  # 裁模板用的源图，不随包分发
    '__pycache__', 'debug', 'logs', 'temp', 'backup', '.git', '.workbuddy',
}
# 排除文件
EXCLUDE_FILES = {'resource/mfa_layout.json'}
# 排除后缀
EXCLUDE_SUFFIXES = ('.pyc', '.bak')


def should_skip(rel):
    rel = rel.replace('\\', '/')
    if rel in EXCLUDE_FILES:
        return True
    for d in EXCLUDE_DIRS:
        if rel == d or rel.startswith(d + '/'):
            return True
    if rel.endswith(EXCLUDE_SUFFIXES):
        return True
    return False


if os.path.exists(OUT):
    os.remove(OUT)

count = 0
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    # 根 interface.json
    z.write(os.path.join(ROOT, 'interface.json'), 'interface.json')
    count += 1
    # resource/ + agent/（不含程序文件；agent/ 必须完整）
    for base in ('resource', 'agent'):
        bd = os.path.join(ROOT, base)
        if not os.path.isdir(bd):
            continue
        for dp, dn, fn in os.walk(bd):
            dn[:] = [d for d in dn
                     if not should_skip(os.path.relpath(os.path.join(dp, d), ROOT).replace('\\', '/'))]
            for f in fn:
                fp = os.path.join(dp, f)
                rel = os.path.relpath(fp, ROOT).replace('\\', '/')
                if should_skip(rel):
                    continue
                z.write(fp, rel)
                count += 1

sz = os.path.getsize(OUT)
print("DONE entries=%d size=%.2f MB" % (count, sz / 1024 / 1024))
print("OUT=", OUT)

# ---- 安全复核：绝不能含 MFA 程序文件，必须含 interface.json / resource/ / agent/ ----
LEAK_MARKERS = ('runtimes/', 'libs/', 'plugins/', 'python/', '.exe', '.dll',
               'MaaEOV.exe', 'MaaEOV.desktop', 'uiohook', 'MFAAvalonia', 'av_libglesv2')
with zipfile.ZipFile(OUT) as z:
    names = z.namelist()
    leaks = [n for n in names if any(m.lower() in n.lower() for m in LEAK_MARKERS)]
    has_iface = 'interface.json' in names
    has_resource = any(n.startswith('resource/') for n in names)
    has_agent = any(n.startswith('agent/') for n in names)
    print("  复核：leak=%s iface=%s resource=%s agent=%s" %
          (leaks if leaks else '无', has_iface, has_resource, has_agent))
    if leaks:
        raise SystemExit("资源包泄漏了 MFA 程序文件，已中止上传：%s" % leaks)
    if not (has_iface and has_resource and has_agent):
        raise SystemExit("资源包缺少必含项（interface/resource/agent）")
