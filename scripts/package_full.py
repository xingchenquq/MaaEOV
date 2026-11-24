import os, re, sys, zipfile, json, subprocess

# 仓库根目录：本脚本位于 <root>/scripts/，由脚本位置推导两级父目录，
# 克隆在任意路径都能打包（不硬编码本机路径）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'dist')  # 必须在项目目录内
os.makedirs(OUT_DIR, exist_ok=True)

# ---- 打包前置：全量校验（死链/同名节点/扫荡链 timeout/ROI 越界/override 断链等），防把坏资源发出去 ----
SKIP_VERIFY = '--skip-verify' in sys.argv
if not SKIP_VERIFY:
    _verify = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'verify_feature.py')])
    if _verify.returncode != 0:
        sys.exit('verify_feature.py 未通过（须 RESULT: ALL_OK 才允许打包）；确认无误可加 --skip-verify 跳过')

# 版本号取自 interface.json，避免写死后与发布版本不一致
VER = json.load(open(os.path.join(ROOT, 'interface.json'), encoding='utf-8'))['version']
# 资源名用 ASCII（与历史 Release 一致；中文会被 gh 吞掉）
OUT = os.path.join(OUT_DIR, 'MaaEOV-%s-full-package.zip' % VER)
if os.path.exists(OUT):
    os.remove(OUT)

# 排除目录（版本控制/调试/缓存/构建产物/日志/输出目录自身）
# vendor/：MFA 源码独立副本（scripts/sync_mfa_src.sh 生成，1GB，含 obj/ 构建中间物），
#          只是开发期参考，发行包不需要；且其中 Avalonia 生成物的路径会导致 zipfile 写入失败。
SKIP_DIRS = {'.git', '.github', '.workbuddy', '.mimosa', 'temp', 'debug', 'docs', 'scripts',
             '__pycache__', '.nicegui', 'backup', '.mfa_build', 'logs', 'dist', 'vendor'}
# 排除文件（开发产物/打包脚本自身）
SKIP_FILES = {'MaaEOV-resource.zip',
              'DependencySetup_依赖库安装_win.bat',
              'package_full.py', 'package_full_log.txt'}


def keep(rel):
    parts = rel.split('/')
    if parts[0] in SKIP_DIRS:
        return False
    if parts[-1] in SKIP_FILES:
        return False
    if parts[-1].endswith('.bak'):
        return False
    # ---- 每台机器不同的运行期配置：不入发布包 ----
    # config/instances/*.json 与 maa_pi_config.json 内含本机模拟器路径 / 端口
    # （如 D:\MuMu\nx_main\MuMuNxMain.exe、127.0.0.1:16384），发出去会导致别的用户
    # 用错误路径启动模拟器。这些由用户首次运行时在 GUI 中自行配置 / 自动检测。
    if rel.startswith('config/instances/'):
        return False
    if rel == 'config/maa_pi_config.json':
        return False
    # monitor_baseline.json 含采集时间戳等本机信息（见 .gitignore）
    if rel == 'config/monitor_baseline.json':
        return False
    return True


def _sanitize_walk(node, removed, path=''):
    """递归剔除所有层级的密钥类键（2026-11-24 修复：此前只扫顶层，
    MFA 通知配置若以嵌套 dict 存储（如 {"Notification": {"Token": ...}}）会漏剔）。"""
    if isinstance(node, dict):
        for k in list(node.keys()):
            p = '.'.join(filter(None, (path, str(k))))
            if isinstance(k, str) and SECRET_KEY_RE.search(k):
                removed.append(p)
                node.pop(k, None)
            else:
                _sanitize_walk(node[k], removed, p)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            _sanitize_walk(item, removed, '%s[%d]' % (path, i))


def sanitize_json(fp, rel):
    """把全局配置 JSON 里的「密钥类」键剔除（返回 新内容bytes, 被剔除键列表）。

    背景：MFAAvalonia 的全局配置里可能保存 GitHubToken（私有库 OTA 用的只读 PAT）、
    DownloadCDK（Mirror酱 CDK）、以及外部通知的 Token/Secret/Password 等。
    这些是「每个用户自己的凭据」，**绝不能随发布包发出去**。

    2026-11-24 修复：JSON 解析失败此前只打 warn 并原样打包（消毒开路），
    现改为硬失败中止打包——消毒不可跳过。
    """
    try:
        with open(fp, encoding='utf-8') as f:
            obj = json.load(f)
    except Exception as e:
        raise SystemExit('密钥消毒中止：%s JSON 解析失败（%r）；禁止原样打包未消毒文件，请先修复该文件' % (rel, e))
    removed = []
    _sanitize_walk(obj, removed)
    if not removed:
        return None, []
    return (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8'), removed


# 可能藏凭据的全局配置（MFA 把全局设置写在 config/config.json 与 appsettings.json）
# 覆盖：GitHubToken（私有库 OTA 的只读 PAT）、DownloadCDK（Mirror酱 CDK）、
#       各类外部通知的 Token/Secret/Password/WebhookUrl/QmsgKey/OneBotKey/ServerChanKey。
# （config/config.template.json 曾列于此，仓库与磁盘均无此文件，2026-11-24 移除死条目）
SECRET_KEY_RE = re.compile(
    r'(?i)(token|secret|password|passwd|cdk|api_?key|(qmsg|onebot|serverchan)key|webhookurl)')
SANITIZE_FILES = ['config/config.json', 'appsettings.json']

n = 0
total = 0
sanitized = []
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    for dp, dirs, fns in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in fns:
            fp = os.path.join(dp, fn)
            rel = os.path.relpath(fp, ROOT).replace('\\', '/')
            if not keep(rel):
                continue
            if rel in SANITIZE_FILES:
                data, removed = sanitize_json(fp, rel)
                if removed:
                    zi = zipfile.ZipInfo.from_file(fp, rel)
                    zi.compress_type = zipfile.ZIP_DEFLATED
                    z.writestr(zi, data)
                    sanitized.append((rel, removed))
                    n += 1
                    total += len(data)
                    continue
            z.write(fp, rel)
            n += 1
            total += os.path.getsize(fp)

print('打包完成: ' + OUT)
print('文件数: %d，源体积: %.0f MB，zip: %.0f MB'
      % (n, total / 1024 / 1024, os.path.getsize(OUT) / 1024 / 1024))

# ---- 密钥消毒报告 + 复核 ----
print('--- 密钥消毒 ---')
if sanitized:
    for rel, removed in sanitized:
        print('  %s：已剔除 %s' % (rel, ', '.join(removed)))
else:
    print('  无需要剔除的密钥键（本机配置里没有 GitHubToken / CDK / 通知凭据等）')

def _find_secret_leaks(node, path=''):
    """递归查找密钥类键名残留（与 _sanitize_walk 同判据，双向一致才有效）。"""
    leaks = []
    if isinstance(node, dict):
        for k, v in node.items():
            p = '.'.join(filter(None, (path, str(k))))
            if isinstance(k, str) and SECRET_KEY_RE.search(k):
                leaks.append(p)
            else:
                leaks.extend(_find_secret_leaks(v, p))
    elif isinstance(node, list):
        for i, item in enumerate(node):
            leaks.extend(_find_secret_leaks(item, '%s[%d]' % (path, i)))
    return leaks


leftover = []
with zipfile.ZipFile(OUT) as z:
    names = set(z.namelist())
    for rel in SANITIZE_FILES:
        if rel not in names:
            continue
        try:
            obj = json.loads(z.read(rel).decode('utf-8'))
        except Exception as e:
            leftover.append('%s（解析失败 %r）' % (rel, e))
            continue
        leftover.extend('%s → %s' % (rel, p) for p in _find_secret_leaks(obj))
print('  复核：' + ('⚠️ 发现残留密钥 → %s' % leftover if leftover else 'OK，包内无密钥残留'))
