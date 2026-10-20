# scripts/ 脚本索引

本目录按**是否入库**和**能否直接运行**分三层，一眼可辨：

| 位置 | 性质 | 说明 |
|---|---|---|
| `scripts/` 根 | **常备工具**（入库） | 开发 / 发版流程反复使用，可直接运行；CI 直接引用 |
| `scripts/legacy/` | **历史一次性脚本**（入库） | 某次变更 / 适配的批处理产物，保留作记录与参考。**不要在当前目录结构上盲跑**——它们写死的节点名、文件名、坐标对应的是旧版状态 |
| `scripts/local/` | **本机专用**（不入库） | 含本机绝对路径 / 个人模拟器录制，由 `.gitignore` 的 `/scripts/local/` 整目录排除 |

> 一次性脚本多为某条开发记录（见根目录 `开发记录.md`）的配套产物；每条记录里能查到当时的根因与验证方式。

## 常备工具（`scripts/`）

| 脚本 | 用途 | 运行时机 |
|---|---|---|
| `verify_feature.py` | **主校验**（CI push/PR 强制）：JSONC 解析、跨文件同名节点、死链、模板切图、custom_action 注册、任务 entry/option 引用、pipeline_override 目标、扫荡链 timeout、ROI 越界。`RESULT: ALL_OK` = 通过 | 每次改 pipeline / agent / interface 后；提交前必跑 |
| `gen_flow_doc.py` | 从 pipeline 再生 `docs/任务流程与UI重测清单.md`（CI 校验文档同步，勿手改该文档） | 每次改 pipeline 后 |
| `package_full.py` | **完整包打包**（发版唯一通道）：前置自动跑 `verify_feature.py` → 按排除规则收集 → 密钥消毒 → 包内复核，产出 `dist/MaaEOV-<版本>-full-package.zip`。发布流程见 `docs/release.md` | 每次发版 |
| `build_resource_zip.py` | **资源 OTA 包**：`interface.json` + `resource/` + `agent/`，构建后做 `LEAK_MARKERS` 程序文件泄漏阻断，产出 `dist/MaaEOV-<版本>-resource-win-x64.zip` | 发版需增量更新时 |
| `migrate_layout.py` | **目录整理工具**（默认只读）：`report` 盘点 / `images` 散图归位 / `archive` 归档一次性脚本 / `purge` 清理过期产物。方案见 `docs/重构与目录整理方案-2026-10-20.md` | 目录维护时 |
| `pack_resource.py` | 打增量资源包 `MaaEOV-resource.zip`（interface.json + resource/，不含 agent/）。**当前策略仅发完整包**，此脚本仅配合 `.github/workflows/release_resource.yml` 手动触发产出旧版增量包 | 仅临时需要增量包时 |
| `build_gui_mfa.sh` | MFAAvalonia GUI（MaaEOV.exe）构建脚本 | 升级 GUI 宿主时（产出物不入库） |

## `legacy/` · 历史一次性脚本（入库，参考勿盲跑）

### v1.14.3 · Tasks.json 拆分（`4010cba` / `4fa9b99`）

| 脚本 | 用途 |
|---|---|
| `legacy/split_pipeline.py` | 把 Tasks.json 按功能入口拆分为多文件（花括号深度扫描 + BFS 可达性分区，产出预览到 `temp/pipeline_split/`，不触碰线上目录） |
| `legacy/apply_pipeline_split.py` | 把拆分预览产物正式写入 `resource/base/pipeline/` |

### v1.2 · MaaFramework v5.1 协议迁移（`c66f7ad`）

| 脚本 | 用途 |
|---|---|
| `legacy/migrate_pipeline_v5.py` | 把旧版 `is_sub` / `interrupt` 转换为 v5.1 的 `[JumpBack]` 前缀格式（保留注释与缩进；用法见其 docstring） |

### v1.11 ~ v1.12 · 认知海域（SoC）开发期批处理

| 脚本 | 用途 |
|---|---|
| `legacy/crop_soc_templates.py` | SoC 模板切图（第二批） |
| `legacy/recrop_soc_buff_templates.py` | 5 张全局 Buff 模板重裁为「未激发」标签区 |
| `legacy/recrop_ibb.py` | 局内 Buff 相关模板按实测 ROI 重裁 |
| `legacy/add_soc_focus.py` | 给 SoC pipeline 每节点补 focus 进度文案 |
| `legacy/soc_trace.py` | SoC「卡在哪一步」诊断器（只读，可参考用于其它任务的诊断思路） |

### 其他

| 脚本 | 用途 |
|---|---|
| `legacy/` 内其余脚本 | 见 `开发记录.md` 对应版本的"配套产物"说明 |

## `local/` · 本机专用（不入库）

| 脚本 | 用途 | 备注 |
|---|---|---|
| `local/check_roi.py` | 把改动 ROI 画回原截图目视核对 | JOBS 列表按次硬编码，用前先改 |
| `local/check_versions.py` | 读 exe/dll 的 Windows 文件版本，核对本机二进制与 `interface.json` 版本一致性 | 排查「GUI 与资源版本错配」时用 |
| `local/grid_view.py` | 给截图叠加坐标网格（50px 细线 / 100px 标数） | UI 改版重新定位坐标时用 |
| `local/crop_templates.py` | SoC 原始截图切模板图 + 切图框回画核对 | 含本机路径 |
| `local/fix_soc_templates.py` | SoC 4 个 OCR 节点改 TemplateMatch | 含本机路径 |
| `local/fix_soc_ocr_variants.py` | SoC OCR expected 加简繁兼容 | 含本机路径 |
| `local/fix_soc_dive_flow.py` | 补「开始下潜」+ 修下潜方式二选一 | 含本机路径 |
| `local/fix_soc_entry_nav.py` | 修 SoC 入口导航 | 含本机路径 |
| `local/fix_template_paths.py` | 批量修正模板路径 | 含本机路径 |
| `local/post_upgrade_tidy.py` | SoC doc / interface 过期说明清理 | 含本机路径 |
| `local/parse_mmor.py` | 解析 MuMu 模拟器 MMOR 录制轨迹（press_rel 点位 / 手势边界） | 含本机绝对路径 |
| `local/loadres.py` | `maa` 包 `Resource().post_bundle()` 资源加载冒烟测试 | 排查「资源加载失败」可参考写法 |
| `local/loadres2.py` | 同上，ASCII 路径副本对照测试 | 含本机绝对路径 |

## 相关入口

| 位置 | 用途 |
|---|---|
| `../interface.json` | 任务 / 选项 / pipeline_override 装配（版本号与 `custom_title` 两处生效） |
| `../resource/base/pipeline/` | pipeline 节点定义（20 个 JSONC 文件，跨文件节点名全局唯一） |
| `../resource/base/image/` | 模板切图，按功能域分 14 个子目录（根目录不放散图） |
| `../agent/` | CustomAction / CustomRecognition 实现（`main.py` 只 import 用到的模块） |
| `../docs/release.md` | 完整包发布 SOP |
