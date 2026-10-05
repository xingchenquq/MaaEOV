# MaaEOV 完整包发布 SOP

> 当前发布策略（2026-09 起）：**只发完整包**，不做增量（resource）OTA 更新。
> 原因：完整包含 MFA / agent / python / maa 包等二进制（均在 `.gitignore`，CI 拿不到），
> 只能**本机构建**后手动上传；且资源包与完整包混装曾导致版本错配问题。
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

### 4. 包内容自查

```bash
python -c "import zipfile; print('\n'.join(sorted(zipfile.ZipFile(r'dist/<包名>.zip').namelist())))"
```

确认清单：

- [ ] `agent/`、`python/`、`resource/`、`interface.json`、MFA 二进制齐全且**同版本**；
- [ ] **不含** `config/instances/`、`config/maa_pi_config.json`（本机模拟器路径/端口）；
- [ ] **不含** `debug/`、`scripts/`、`docs/`、`dist/`、`开发记录.md`、任何 `*.bak`；
- [ ] 密钥复核输出 `OK，包内无密钥残留`（脚本末行）。

### 5. 上传 GitHub Release

```bash
gh release create v<版本> "dist/MaaEOV-v<版本>-full-package.zip" \
  --title "MaaEOV v<版本>" --notes "见 Changelog"
```

或用 PAT 直连 uploads API（历史方式，zip 名保持 ASCII，中文名会被 gh 吞掉）。

### 6. 发布后确认

- GitHub Actions 的 `verify` workflow 在 push 后应全绿（校验 + 文档同步）；
- 用一个干净目录解压完整包，按 `README.md` 首次使用说明跑一遍主要任务（建议监督跑一轮日常）。

## 红线（每次发布前逐条自问）

1. **`agent/` 有改动 → 必须发完整包**：资源 OTA 包不含 `agent/`，仅发资源包用户侧不会生效。
2. **凭据不入包**：GitHub Token / Mirror酱 CDK / 通知凭据只存在于本机 `config/config.json` 等
   运行期配置，打包脚本会消毒——但**不要**把含凭据的配置手动拷进仓库或资源包。
3. **不混装版本**：`resource/`、`agent/`、`python/`、MFA 必须来自同一份完整包，不要手动拼装。
4. **不发半校验状态**：`verify_feature.py` 非 `ALL_OK` 禁止打包（脚本会自动拦截）。
