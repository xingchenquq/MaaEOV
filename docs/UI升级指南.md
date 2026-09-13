# MaaEOV GUI 升级指南

> 适用场景：把 MaaEOV 的 GUI 底层（**MFAAvalonia + MaaFramework**）升级到新版本。
> 本文基于 **v1.2** 的升级过程整理（MFAAvalonia 1.6.5 → 2.16.1）。

---

## 一、升级内容概览

| 组件 | 升级前 | 升级后 | 说明 |
|---|---|---|---|
| GUI | MFAAvalonia 1.6.5 | **2.16.1** | 界面主程序 |
| MaaFramework | 4.5.6 | **5.12.3** | 随 GUI 一起升级 |
| MaaAgentBinary | 1.0.1 | 1.2.0 | agent 二进制 |
| **maafw（Python 包）** | 4.5.6 | **5.12.3** | **必须与框架版本对齐，否则 agent 连不上** |
| 打包形态 | self-contained 单文件 | 保持不变 | 解压即用，玩家无需安装 .NET |

> ⚠️ **升 GUI 一定会连带升 MaaFramework**（GUI 依赖框架的 API 与原生库）。
> MaaFramework 5.x 存在**破坏性变更**（见「错误 3」），所以 pipeline 必须同步迁移。
> 这是整个升级里最容易踩坑的地方。

---

## 二、完整流程

### 步骤 1：准备源码

```bash
git clone https://github.com/MaaXYZ/MFAAvalonia.git
cd MFAAvalonia
git fetch --depth 1 origin tag <目标版本>
git checkout <目标版本>
```

需要 **.NET SDK 10**（新版工程 TargetFramework 为 `net10.0`）：

```bash
dotnet --list-sdks
```

### 步骤 2：编译 self-contained 单文件

仓库已提供脚本 `scripts/build_gui_mfa.sh`，直接用它，不要手敲参数：

```bash
MFA_SRC=<MFAAvalonia 源码目录> \
MFA_OUT=<输出目录> \
MFA_VER=1.2.0 \
bash scripts/build_gui_mfa.sh
```

核心参数与理由：

| 参数 | 作用 |
|---|---|
| `--configfile <src>/MFAAvalonia/NuGet.Config` | **必须显式指定**：NuGet.Config 在子目录，不会自动读取；`Maa.*` 包依赖 maaxyz 官方源 |
| `-p:SelfContained=true -p:PublishSingleFile=true` | 产出单文件绿色包 |
| `-p:EnableCompressionInSingleFile=true` | exe 从 191MB 压到 ~95MB |
| `-p:PublishTrimmed=false` | Avalonia 依赖反射，**不能裁剪** |
| **`-p:DisableBeauty=True`** | **关键**：彻底关闭 NetBeauty，否则启动必崩（见「错误 2」） |
| `-p:AssemblyTitle/-p:Product/-p:Company=MaaEOV` | 写入文件属性；**注意不能用 `-p:AssemblyName` 改程序集名** |
| `-p:ApplicationIcon=<MaaEOV>/Assets/logo.ico` | 使用项目自己的图标 |

### 步骤 3：部署产物

产物目录结构（新版与旧版**布局不同**）：

```
MFAAvalonia.exe                ← 主程序，部署时改名为 MaaEOV.exe
av_libglesv2.dll / libSkiaSharp.dll / libHarfBuzzSharp.dll / libonigwrap.dll
miniaudio.dll / uiohook.dll / SukiUI.xml
libs/                          ← NetBeauty 风格的库目录
plugins/win-x64/
runtimes/win-x64/native/       ← ★ native 库都在这里（旧版是平铺在根目录）
MaaAgentBinary/
```

**部署要点：**

1. **先把根目录平铺的旧 dll 全部删掉**（`MaaFramework.dll`、`MaaToolkit.dll`、`MaaAgent*.dll`、
   `DirectML.dll`、`onnxruntime_maa.dll`、`opencv_world4_maa.dll` 等）。
   否则旧版 MaaFramework 可能被优先加载，和新的 exe 混用会出诡异问题。
2. 复制新产物到项目根目录。
3. 把 `MFAAvalonia.exe` **重命名为 `MaaEOV.exe`**。
   - **不要试图在编译时改 `AssemblyName`**：源码里有 26 处 `avares://MFAAvalonia.Core/...`
     资源 URI 硬依赖程序集名，改了会导致运行时资源加载失败。exe 的文件名可以随便改，
     程序集名不行。
4. 项目自有资产**不要被覆盖**：`interface.json`、`resource/`、`agent/`、`python/`、
   `config/`、`Assets/`、`README.md`、`LICENSE`、`MaaEOV.desktop`。
   （编译产物的 `README.md` / `docs/` / `cliff.toml` 是上游的，不要覆盖进来。）

> 新版**不再需要** `MFAUpdater.exe`、`MaaPiCli.exe`、`MaaNode*.node`（更新器已内置）。

### 步骤 4：升级 Python 绑定（**必做**）

内嵌 Python 的 `maafw` 包必须与框架版本**完全一致**，否则 agent 静默挂起（见「错误 4」）：

```bash
./python/python.exe -m pip install --no-cache-dir "maafw==5.12.3"
```

验证方式——**两侧 `MaaAgentServer.dll` 大小应完全一致**：

```bash
ls -la python/Lib/site-packages/maa/bin/MaaAgentServer.dll
ls -la runtimes/win-x64/native/MaaAgentServer.dll
```

### 步骤 5：迁移 pipeline（**必做**）

MaaFramework 5.1 起废弃了 `interrupt` 字段，需迁移为 `[JumpBack]` 前缀：

```bash
python scripts/migrate_pipeline_v5.py resource/base/pipeline --dry-run   # 先预览
python scripts/migrate_pipeline_v5.py resource/base/pipeline             # 正式迁移
```

> 不迁移就会「资源加载失败」（见「错误 3」）。
> 脚本会保留 JSONC 注释与缩进风格；迁移前建议先备份 pipeline 目录。

### 步骤 6：校验

```bash
python scripts/verify_feature.py      # 期望 RESULT: ALL_OK
python scripts/validate_pipeline.py   # 期望「无（所有 next/interrupt 引用均可解析）」
```

校验脚本已适配 v5 语法（会自动剥离 `[JumpBack]` / `[Anchor]` 前缀再校验目标是否存在）。

### 步骤 7：实跑验证

**重启 MaaEOV**（GUI 只在启动时加载 resource / pipeline），跑一次完整任务流程。
重点确认日志里不出现：`资源加载失败`、`启动 Agent` 卡住、任务死循环。

---

## 三、关键错误与解决

### 错误 1：编译时报 `Access to the path '...' is denied`

**现象**：`dotnet publish` 在 restore 阶段失败，而且每次报的**文件路径都不一样**
（`Microsoft.CodeAnalysis.resources.dll`、`SharpDX.Direct3D12.xml` …）。

**原因**：在受限沙箱/安全策略环境下，构建工具写入文件被拦截，且拦截时会给文件打上
**拒绝 ACL**，导致后续即使换权限也访问不了同一个文件——所以错误会在不同文件间"漂移"。

**解决**：

1. 清空被污染的 NuGet 缓存：`rm -rf ~/.nuget/packages`
2. 以**非沙箱**权限重新执行构建（并确保是**前台**执行，后台执行往往拿不到授权提示）

### 错误 2：启动即崩，`Startup hook assembly 'libloader' failed to load`（退出码 `0xE0434352`）

**现象**：exe 双击闪退，stderr 报：
```
System.ArgumentException: Startup hook assembly 'libloader' failed to load.
 ---> System.IO.FileNotFoundException: File name: 'libloader, Culture=neutral, PublicKeyToken=null'
```

**原因**：**NetBeauty** 会往 runtimeconfig 写入 `"STARTUP_HOOKS": "libloader"`，
用于把 `libs/` 目录下的程序集加载进来。但在**单文件模式**下 `libloader` 没有被打包进 exe，
启动钩子找不到它 → 崩溃。

> ❌ **错误做法**：用 `-p:BeautyOnPublishOnly=false` 去绕。
> 它会让 NetBeauty 在 **build 阶段**也运行，反而把 runtimeconfig 污染得更彻底。

**解决**：查 `nulastudio.NetBeauty.targets` 找到真正的总开关，加参数：

```
-p:DisableBeauty=True
```

禁用后 runtimeconfig 中不再有 `STARTUP_HOOKS` / `NetBeautyLibsDir` 等条目。

### 错误 3：任务报「资源加载失败！」（`IMaaResource failed to load resources`）

**现象**：GUI 提示「资源加载失败！请删除整个文件夹重新下载，或联系项目维护者。」
——**这个提示是误导的，文件并没有损坏**。

**排查**：看 `debug/maafw.log`，会看到真正原因：
```
[ERR][PipelineParser.cpp] interrupt is deprecated since v5.1, use `[JumpBack]` instead
[ERR][PipelineResMgr.cpp] parse_task failed [key=#UrbanPatrol]
[ERR][PipelineResMgr.cpp] parse_config failed [path=.../resource/base/pipeline/Tasks.json]
[ERR][PipelineResMgr.cpp] load_all_json failed
```

**原因**：MaaFramework **5.1 起废弃 `interrupt` 字段**，必须改用 `next` 里的 `[JumpBack]` 前缀。
只要有一个节点用了旧写法，**整个 pipeline 文件就解析失败**，进而整份 resource 加载失败。

**解决**：用官方迁移脚本（见「步骤 5」）。本项目已归档到 `scripts/migrate_pipeline_v5.py`。

> 取脚本时注意：`raw.githubusercontent.com` 若不通，可改走 GitHub API 的 contents 接口
> 拿 base64 内容：`https://api.github.com/repos/MaaXYZ/MaaFramework/contents/tools/migrate_pipeline_v5.py`

### 错误 4：卡在「正在启动 Agent(耗时可能较久)」

**现象**：资源、控制器都检测通过，但卡在启动 Agent，**没有任何报错**，界面一直转。
`debug/maafw.log` 末尾停在：
```
[MaaAgentClientConnect] [ipc_addr_=ipc://C:/Temp/maafw-agent-<id>.sock]
```

**这是两个问题叠加，两个都必须修：**

#### 4a. Python 绑定版本落后于框架（主因）

- MaaEOV 内嵌 Python 的 `maafw` 还停留在 4.5.6，而新版 GUI 携带 MaaFramework 5.12.3，
  **agent 协议不匹配**，连不上。
- **判据**：两侧 `MaaAgentServer.dll` 大小不一致
  （旧：python 侧 1,055,744 B vs 框架侧 1,385,984 B）。
- **解决**：把 maafw 升到与 `Maa.Framework.Runtimes` **同号**的版本（见「步骤 4」）。

#### 4b. `agent/main.py` 取 socket_id 的方式被新版命令行破坏

- MFAAvalonia 2.x 的 agent 启动命令变成了：
  ```
  python main.py <ClientId> socket_id=<ClientId> instance_id=<id> instance_name=<name>
  ```
  而 1.x 只有 `python main.py <ClientId>`。
- 旧代码用 `sys.argv[-1]` 取 socket_id，在新版下会取到 `instance_name=配置 1`
  → socket 名不匹配 → C# 端永远等不到连接。
- **解决**：`agent/main.py` 改为**优先解析 `socket_id=` 参数**，回退到第一个不含 `=` 的位置参数
  （新旧两版命令行都兼容）。已修复。

---

## 四、升级检查清单

- [ ] 拉取并 checkout 目标版本源码
- [ ] `build_gui_mfa.sh` 编译（确认带 `DisableBeauty=True`）
- [ ] 删除根目录旧的平铺 native dll
- [ ] 复制产物 + `MFAAvalonia.exe` 改名 `MaaEOV.exe`
- [ ] 确认项目自有资产（interface.json / resource / agent / python / config）未被覆盖
- [ ] **`pip install maafw==<框架同版本>`**
- [ ] **`migrate_pipeline_v5.py` 迁移 pipeline**
- [ ] `verify_feature.py` → `ALL_OK`
- [ ] 重启 GUI 实跑，确认无「资源加载失败」、无 Agent 卡住

---

## 五、日常改动 pipeline 的注意事项

1. **Tasks.json 是带注释的 JSONC，且为 LF 行尾**。
   修改时**不要用 `json.load` + `json.dump` 重写**（会丢失全部注释、重排格式、diff 爆炸）。
   应该做**带上下文的文本级精确替换**，并原样保留行尾。
2. **不要在同一条消息里对同一个文件发多条编辑**（并行写会互相覆盖，只有最后一条生效）。
   要改同文件多处，用单条脚本做原子替换。
3. **`[JumpBack]` 节点上只能挂"终止类"动作**（如 `_StopTask`），
   **不能挂"会继续执行"的收尾动作**（如 `_NavigateHomepage`）。
   因为 `[JumpBack]` 执行完会**跳回发起节点**，收尾动作等于被放进循环体，会导致死循环。
   （v1.2 修复过一次这样的问题：外部招募「任务已满」出口。）
