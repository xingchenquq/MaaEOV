# scripts/ 脚本索引

本目录分两类脚本：**常备工具**（开发/发版流程中反复使用，可直接运行）与**一次性脚本**
（历史上某次变更/适配的批处理产物，保留作记录与参考，**不要在当前目录结构上盲跑**——
它们写死的节点名、文件名、坐标对应的可能是旧版状态）。

| 分类 | 说明 |
|---|---|
| 常备 | 放在 `scripts/` 根目录，CI 或发版流程直接引用 |
| 一次性 | 下表标 `[一次性]`，多为某条开发记录（见根目录 `开发记录.md`）的配套产物 |

## 常备工具

| 脚本 | 用途 | 运行时机 |
|---|---|---|
| `verify_feature.py` | **主校验**（CI push/PR 强制）：JSONC 解析、跨文件同名节点、死链、模板切图、custom_action 注册、任务 entry/option 引用、pipeline_override 目标、扫荡链 timeout、ROI 越界。`RESULT: ALL_OK` = 通过 | 每次改 pipeline / agent / interface 后；提交前必跑 |
| `gen_flow_doc.py` | 从 pipeline 再生 `docs/任务流程与UI重测清单.md`（CI 校验文档同步，勿手改该文档） | 每次改 pipeline 后 |
| `pack_resource.py` | 打增量资源包 `MaaEOV-resource.zip`（interface.json + resource/，不含 agent/）。**当前策略仅发完整包**，此脚本仅配合 `.github/workflows/release_resource.yml` 手动触发产出旧版增量包 | 仅临时需要增量包时 |
| `check_versions.py` | 读 exe/dll 的 Windows 文件版本（MaaEOV.exe 等），核对本机二进制与 interface.json 版本一致性 | 排查「GUI 与资源版本错配」时 |
| `grid_view.py` | 给截图叠加坐标网格（50px 细线 / 100px 标数），用于量坐标、选 ROI / 切图框 | UI 改版重新定位坐标时 |
| `build_gui_mfa.sh` | MFAAvalonia GUI（MaaEOV.exe）构建脚本 | 升级 GUI 宿主时（产出物不入库） |

## 一次性脚本（`[一次性]`，历史记录，参考勿盲跑）

### v1.14.3 · Tasks.json 拆分（`4010cba` / `4fa9b99`）

| 脚本 | 用途 |
|---|---|
| `split_pipeline.py` | 把 Tasks.json 按功能入口拆分为多文件（花括号深度扫描 + BFS 可达性分区，产出预览到 `temp/pipeline_split/`，不触碰线上目录） |
| `apply_pipeline_split.py` | 把拆分预览产物正式写入 `resource/base/pipeline/` |

### v1.2 · MaaFramework v5.1 协议迁移（`c66f7ad`）

| 脚本 | 用途 |
|---|---|
| `migrate_pipeline_v5.py` | 把旧版 `is_sub` / `interrupt` 转换为 v5.1 的 `[JumpBack]` 前缀格式（保留注释与缩进；用法见其 docstring） |

### v1.11 ~ v1.12 · 认知海域（SoC）开发期批处理

| 脚本 | 用途 |
|---|---|
| `crop_templates.py` | SoC 原始截图切模板图 + 切图框回画核对 |
| `crop_soc_templates.py` | SoC 模板切图（第二批） |
| `recrop_soc_buff_templates.py` | 5 张全局 Buff 模板重裁为「未激发」标签区 |
| `recrop_ibb.py` | 局内 Buff 相关模板按实测 ROI 重裁 |
| `fix_soc_templates.py` | SoC 4 个 OCR 节点改 TemplateMatch |
| `fix_soc_ocr_variants.py` | SoC OCR expected 加简繁兼容 |
| `fix_soc_dive_flow.py` | 补「开始下潜」+ 修下潜方式二选一 |
| `fix_soc_entry_nav.py` | 修 SoC 入口导航 |
| `add_soc_focus.py` | 给 SoC pipeline 每节点补 focus 进度文案 |
| `post_upgrade_tidy.py` | SoC doc / interface 过期说明清理 |
| `soc_trace.py` | SoC「卡在哪一步」诊断器（只读，可参考用于其它任务的诊断思路） |

### 其他一次性工具

| 脚本 | 用途 | 备注 |
|---|---|---|
| `check_roi.py` | 把改动 ROI 画回原截图目视核对 | JOBS 列表按次硬编码，用前先改；含本机路径 |
| `parse_mmor.py` | 解析 MuMu 模拟器 MMOR 录制轨迹（press_rel 点位/手势边界） | 含本机绝对路径 |
| `loadres.py` | `maa` 包 `Resource().post_bundle()` 资源加载冒烟测试 | 含本机绝对路径；排查「资源加载失败」可参考写法 |
| `loadres2.py` | 同上，ASCII 路径副本对照测试 | 含本机绝对路径 |

## 相关入口（仓库根目录）

| 文件 | 用途 |
|---|---|
| `package_full.py` | **完整包打包**（发版唯一通道）：前置自动跑 `verify_feature.py`，排除本机配置/开发产物，密钥消毒后产出 `dist/MaaEOV-<版本>-full-package.zip`。发布流程见 `docs/release.md` |
