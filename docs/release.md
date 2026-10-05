# MaaEOV 完整包发布 SOP

> 当前发布策略（2026-09 起）：**完整包 + 资源 OTA 双资产**，同一 tag 下挂两个资产。
> - 完整包 `MaaEOV-v<版本>-full-package.zip`：含 MFA / agent / python / maa 等全部二进制（均在 `.gitignore`，CI 拿不到），只能**本机构建**后手动上传。
> - 资源 OTA `MaaEOV-v<版本>-resource-win-x64.zip`：仅含 `interface.json` + `resource/` + **完整 `agent/`**，**绝不含任何 MFA 程序文件**（exe / dll / runtimes / libs / python / plugins）。
> 资源 OTA 供 GUI「检查更新」增量下发；MFA「检查更新」为**全量更新**（先删空用户 `resource/` 与 `agent/` 再复制），故资源 OTA 必须自带完整 `agent/`，否则会清空用户 agent。包名带 `win-x64` 以稳胜「检查更新」选择。
> 本文档是仓库内唯一权威发布流程，替代仓库外 skill 的口口相传。

## 前置条件

- Windows 本机（完整包含 Windows 二进制）；
- 仓库克隆在任意路径均可（`package_full.py` 由脚本位置推导根目录，不依赖本机绝对路径）；
- 发布权限：对该仓库有 `Contents: write` 的 GitHub 账号（gh CLI 已登录，或可用 PAT 走 curl）。

## 标准流程

### 1. 版本号三处同步

| 位置 | 改什么 |
|---|---|
| `interface.json` | `"version": "v1.14.x"` 与 `"custom_title"` 里的版本号 |
| `resource/announcement/Changelog.md` | 追加本版变更说明（用户可见） |
| `开发记录.md` | 追加变更条目（含根因；涉及 `agent/` 须标注「须随完整包分发」） |

### 2. 本地校验（打包脚本会自动执行第 1 项）

```bash
python scripts/verify_feature.py   # 须 RESULT: ALL_OK
python scripts/gen_flow_doc.py     # 再生流程文档，git diff 应无变化
```

### 3. 打包

```bash
python package_full.py
# 校验已确认无误但需跳过时（不推荐）：python package_full.py --skip-verify
```

脚本自动完成：前置全量校验 → 按排除规则收集文件 → 对 `config/config.json`、
`appsettings.json` 等做**密钥消毒**（剔除 GitHubToken / CDK / 通知凭据键）→
复核包内无密钥残留 → 产出 `dist/MaaEOV-<版本>-full-package.zip`。

### 3.5 构建资源 OTA 包（供 GUI「检查更新」增量下发）

```bash
python build_resource_zip.py
```

脚本按 Maadori 同源安全规范构建 `dist/MaaEOV-<版本>-resource-win-x64.zip`：

- 打包内容：`interface.json` + `resource/`（全量）+ `agent/`（全量）；
- **排除** MFA 程序文件（exe / dll / runtimes / libs / python / plugins）、`resource/base/image/SeaOfCognition/raw`、`debug/`、`logs/`、`temp/`、`__pycache__/`、所有 `*.pyc` / `*.bak`、`resource/mfa_layout.json`；
- 构建后**自校验**：扫描泄漏标记（runtimes/、libs/、plugins/、python/、.exe、.dll、MaaEOV.exe、MFAAvalonia 等），任一项命中即中止；并确认 `interface.json` / `resource/` / `agent/` 三者俱全。自校验通过才允许上传。

> 安全铁律：资源 OTA **必须含完整 `agent/`** 且 **绝不含任何 MFA 程序文件**。MFA「检查更新」为全量更新，会先删空用户 `resource/` 与 `agent/` 再复制包内容；若资源 OTA 缺 `agent/`，用户 agent 将被清空导致程序失效；若含 MFA 程序文件，则触发「二合一」改名（运行中 exe → `.backupMFA`、入口变 `MFAAvalonia.exe`）并可能覆盖 `config/`。

### 4. 包内容自查

```bash
python -c "import zipfile; print('\n'.join(sorted(zipfile.ZipFile(r'dist/<包名>.zip').namelist())))"
```

确认清单：

- [ ] `agent/`、`python/`、`resource/`、`interface.json`、MFA 二进制齐全且**同版本**；
- [ ] **不含** `config/instances/`、`config/maa_pi_config.json`（本机模拟器路径/端口）；
- [ ] **不含** `debug/`、`scripts/`、`docs/`、`dist/`、`开发记录.md`、任何 `*.bak`；
- [ ] 密钥复核输出 `OK，包内无密钥残留`（脚本末行）。

### 5. 上传 GitHub Release（完整包 + 资源 OTA 双资产挂同一 tag）

```bash
gh release create v<版本> \
  "dist/MaaEOV-v<版本>-full-package.zip" \
  "dist/MaaEOV-v<版本>-resource-win-x64.zip" \
  --title "MaaEOV v<版本>" --notes "见 Changelog"
# 若 release 已建、仅补资源资产：gh release upload v<版本> "dist/MaaEOV-v<版本>-resource-win-x64.zip"
```

或用 PAT 直连 uploads API（大文件更稳，见下方「大文件上传」；zip 名保持 ASCII）。

### 6. 发布后确认

- GitHub Actions 的 `verify` workflow 在 push 后应全绿（校验 + 文档同步）；
- 用一个干净目录解压完整包，按 `README.md` 首次使用说明跑一遍主要任务（建议监督跑一轮日常）。

## 红线（每次发布前逐条自问）

1. **资源 OTA 包已含完整 `agent/`**：但仍**不含 MFA 程序文件**（exe / dll / runtimes / libs / python）。若改了 **MFA 外壳功能**（如新增外部通知渠道），该类改动资源 OTA 无法下发，必须在公告 / README 要求用户下载**完整包**覆盖安装；改 `agent/*.py` 则资源 OTA 与完整包都会带新 `agent/`，无需额外动作。
2. **凭据不入包**：GitHub Token / Mirror酱 CDK / 通知凭据只存在于本机 `config/config.json` 等
   运行期配置，打包脚本会消毒——但**不要**把含凭据的配置手动拷进仓库或资源包。
3. **不混装版本**：`resource/`、`agent/`、`python/`、MFA 必须来自同一份完整包，不要手动拼装。
4. **不发半校验状态**：`verify_feature.py` 非 `ALL_OK` 禁止打包（脚本会自动拦截）。
5. **资源 OTA 包安全铁律**：必须含完整 `agent/` 且**绝不含任何 MFA 程序文件**（exe / dll / runtimes / libs / python / plugins），否则全量更新会删空用户 `agent/` 或触发「二合一」改名 / 覆盖；包名必须带 `win-x64` 以稳胜「检查更新」选择。
