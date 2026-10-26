# MPE / Pipeline 编写规则笔记

> 来源：MPE 文档站（mpe.codax.site，中文路径页面）+ MaaFramework Pipeline 协议。
> 用途：以后改 `assets/resource/pipeline/*.json` 时按这里的规则来。

## 一、MaaFramework 执行语义（权威）

来自 [MaaFramework 3.1 任务流水线协议](https://maafw.com/docs/3.1-PipelineProtocol.html)：

1. 对当前节点的 `next` 列表**顺序检测**，依次尝试识别每个子节点。
2. 本轮均未命中 → 继续下一轮，直到超时或有节点命中。
3. 某子节点匹配成功 → 终止后续检测，执行该节点的 `action`。
4. 后继处理：
   - 子节点识别命中且动作成功 → 进入该子节点的 `next`。
   - **子节点识别命中但动作失败 → 进入该子节点的 `on_error`**。
   - **当前节点 `next` 全部未命中且超时 → 进入当前节点的 `on_error`**。
5. 终止条件：
   - 当前节点 `next` 为空（若存在 `[JumpBack]` 回跳点，会先回跳）；
   - `next` 未命中且超时；
   - `post_stop` 或执行了 `StopTask`。

### roi / box / target

- `roi`：识别范围（与 `roi_offset` 共同决定），只在这块区域做识别。
- `box`：识别命中的区域（识别到了哪里）。
- `target`：动作目标（点/滑哪里），默认 `true` = 用 `box`，也可指定固定点/区域/其他节点。
- 典型流程：`roi` 内识别 → 得到 `box` → 计算 `target` → 执行动作。

### 字段与版本

- 以 `.` 开头的文件夹/JSON 不会被读取；以 `$` 开头的 root field 不被解析（MPE 的 `$__mpe_code` 等元数据就是靠这个规则共存）。
- v5.0：新增 `attach`；`TouchDown/Move/Up`、`KeyDown/KeyUp`；Click/LongPress/Swipe/MultiSwipe 新增 `contact`/`pressure`；`target` 支持 `[x, y]`。
- v5.1：新增 `anchor`、`max_hit` 字段与 `Scroll` 动作。

## 二、MPE 连接规则（mpe.codax.site 文档）

来源：指南/工作流面板/连接、节点、快速上手、编译器。

- 节点有四个端点：
  - 左侧上方 `target`（接收 next 类型出口）
  - 左侧下方 `jumpback`（接收 next 类型出口，编译时标记为 jump_back）
  - 右侧上方 `next` 出口
  - 右侧下方 `on_error` 出口
- 连接标签上的数字 = 编译顺序（`next` 与 `jump_back` 共享顺序，`on_error` 独立计数）。
- `on_error` 类型的连接面板里有 **JumpBack 开关**：开启后该 on_error 连接也会带 jump_back 属性。
- **连接安全**（Pipeline 协议要求）：
  - 一个节点的 `next` 与 `on_error` **不能同时指向同一个节点**（否则是「重复路由」，MPE 直接拒绝，`maa-tools check` 也会报错）。
  - `jump_back` 编译后与 `next` 同列表，因此**不能与 `next` 同时指向同一节点**。
- 节点类型：字段节点、外部节点（跨文件引用）、Anchor 重定向节点（`[Anchor]` 前缀）、便签、分组。
- 空节点默认 `recognition: DirectHit` + `action: DoNothing`。

## 三、本项目编写规范（会话中确认的）

1. **`[JumpBack]` 默认挂在 `next` 里**。`on_error` 也支持 JumpBack（MPE 连接面板有开关），但**非必要不要挂**——能用 next 表达的就别绕到 on_error，否则流程会显得没有逻辑。
2. `[JumpBack]` 连的节点是「一段能走完的流程」入口（动作/判断节点），流程终点（无 next）后回跳到父节点继续 next 下一项。
3. 不能连：`StopTask` 终点、会无限循环的节点、与 next 后续项重复的节点。
4. **返回主界面用 JumpBack 链**：点左上角返回 → 确认设置 → 没到就继续点，而不是每步写 on_error 兜底。
5. **`on_error` 只留真实失败分支**（例如：体力识别失败 → 结束任务；商店兑换不到 → 返回演习页），不用它堆循环。
   - **写 `on_error` 时自检：是否少往前写了一个节点**——子节点识别失败会回溯到父节点，走的是**父节点**的 `on_error`。所以 `on_error` 要挂在父节点上，而不是那个失败的子节点上；每次写完 `on_error` 都回头确认一次父节点是谁。
6. 禁止重复路由：同一节点的 `next` 和 `on_error` 不要指向同一个目标（`maa-tools check` 会拦）。
7. 修改 pipeline 后自检：
   - 引用是否悬空（跨文件节点必须在同一资源包里）；
   - `maa-tools check`（CI 的 check workflow）是否通过；
   - `Resource().post_bundle(...)` 返回 `loaded=True`。

## 四、常用模式

### 依次尝试多个分支（按优先级）

```json
"父节点": {
    "next": [
        "[JumpBack]分支A",
        "[JumpBack]分支B",
        "兜底节点"
    ]
}
```

分支 A 命中并走完后回父节点 → 试分支 B → 最后兜底。

### 先做一件事再继续

```json
"券检查": {
    "next": ["[JumpBack]代理完成", "代理作战"]
}
```

先领结算（代理完成链），回到券检查再走代理作战。

### 回主界面重试

```json
"X·主界面判断": {
    "next": ["X·任务"],
    "on_error": ["X·返回"]
},
"X·返回": {
    "next": ["[JumpBack]X·主界面判断"]
}
```

判断失败 → 点返回 → JumpBack 回判断重试（判断上带 `max_hit` 限制次数）。

### 入口先判断状态

```json
"签到·入口": {
    "next": ["[JumpBack]签到·主界面判断", "签到"]
}
```

判断命中（已在主界面）→ 结束任务；失败（停在签到弹窗）→ 继续签到。

## 五、调试与校验

- MPE 右侧「Pipeline JSON」面板：编译预览 / 部分导出 / 全部导出 / 从粘贴板或文件导入。
- 流程级调试：单节点运行、可视化运行流、节点信息。
- 日志：MaaFramework 节点日志在 `debug/maafw.log`（MPE LocalBridge 日志目录也可在 `tools/show_log.py` 查看）。
- CI：`check` workflow 跑 `npx @nekosu/maa-tools check` + JSON Schema 校验，失败会在提交旁显示红 X。

## 六、MPE 编辑器与文件格式细节

来源：工作流面板、导入导出、迁移、开发者工具页面。

### 节点与字段

- 节点名 + 字段 + 端口共同决定编译结果；字段键不可编辑（协议决定）。
- 空节点导出仍生成 `recognition: "DirectHit"` + `action: "DoNothing"`。
- 协议外字段只能写在节点根级 `extras`（深层嵌套不支持；`action.param` 里的自定义字段再导出会丢，同级 `doc` 保留）。
- 节点分 Pipeline / External / Anchor / 便签 / 分组；External、Anchor 不显示连接关系。
- 节点列表会显示入边/出边数量，能快速发现孤立节点或入边异常。

### 连接

- 「邻接信息」面板给出前驱与后继，以及同类型连接的编译顺序编号；编号不对流程就会走错。
- JumpBack 连接有专门标记，需要逐条核对。
- 添加模板时若已有选中节点，会自动建一条 `next` 连接——多余跳转的常见来源。
- 路径高亮可以验证起点到终点的可达路径。

### 文件与配置

- 三种配置方案：①集成（写进 Pipeline 的 `$__mpe_config`）；②分离（`.文件名.mpe.json`）；③不导出（纯代码，导入时自动布局）。
- `$__mpe_config_{文件名}` 的 `$__mpe_code` 存 prefix / filename / version；节点坐标在 `$__mpe_code.position`。
- 分离模式配置以 `.` 开头，MaaFramework 加载时不会读取。
- 部分导出只导出选中节点与连接；导入是覆盖式的，`Ctrl+Z` 只回到导入前的图状态。
- 审阅 diff 时别把节点坐标变化当成逻辑改动（没有坐标记录的文件会自动重排）。

### 兼容与迁移

- v1 / v2 协议可混合导入，迁移期不必一次全改 v2。
- 首次导入所有节点堆在视口中心，要在未选中节点时点自动布局。
- 深层自定义字段会静默丢失（`extras` 只保根级）。
- 开发者工具：控制台 `mpedev()` 可查 `nodes` / `edges` / `config`，`selectNode` 定位节点。

## 七、本地服务、调试与 MSE 集成

来源：本地服务、设备连接、流程级调试、MSE 集成、性能白皮书。

### 本地服务（mpelb）

- 启动位置：MaaFramework 项目根目录（含 interface.json、resource、agent）；默认端口 9066，改端口后前端要同步。
- 文件根目录优先级：`--root` > 配置 `file.root` > 工作目录；显式根目录不存在会拒绝启动。
- 常用命令：`mpelb config open`、`mpelb config set-interface [path]`、`mpelb config open-log`、`mpelb info`；安装/更新/依赖修复前先停服。
- 日志：终端 / 前端日志窗口 / `logs/lb-YYYY-MM-DD.log`。
- 文件监听：开启「自动同步本地文件更改」自动重载；关闭则弹窗确认。

### 设备连接（与 ROI 直接相关）

- ADB 手动连接：ADB 路径留空用 PATH；serial 形如 `127.0.0.1:5555`。
- **截图分辨率模式与 PI 的显示分辨率是两套**：PI 的 `display_short_side` 不会接管实际控制器，必须手动让 MPE 的截图模式与模板/ROI 坐标系一致（本项目是 720 短边）。
- 截图/输入方式只在建立连接时生效；改了要点「应用并重连」。
- 同一时间只能连一个设备。

### 流程级调试

- 不支持断点/单步，只能「从指定节点重新运行」；推荐顺序：仅识别 → 单节点运行 → 完整运行。
- 资源加载顺序：多个资源按顺序加载，后加载的同名节点/同路径图片覆盖先加载的。
- PI 模式：项目有 interface.json 时选「Project Interface」，用项目定义的控制器/资源/选项；改 PI 后按提示重新解析。
- Pipeline Override：临时 JSON 覆盖节点参数/连接，不改源文件（调试用）。
- Agent：用了自定义识别/动作时要启用「调试配置 → 代理」；自启 Agent 时填相同标识符/TCP 端口；勾了「必需」的 Agent 连不上会阻止运行。
- 等待画面静止（`pre/post/repeat_wait_freezes`）：target 要包含纹理/文字细节，避开纯色和渐变。

### MSE 集成

- VS Code 扩展 `nekosu.maa-support`（Maa Pipeline Support），MPE 以 iframe 嵌入。
- MPE iframe 不连 LocalBridge：设备/截图/OCR/运行用 MSE 面板。
- 保存到 MSE（Ctrl+S）只更新 TextDocument，落盘还要在 VS Code 保存；外部改动后要「从 MSE 同步」。
- 「检测到 MPE 配置」黄色警告：在工作区根 `maatools.config.mts` 里 `check.override: {'mpe-config': 'ignore'}`（本项目已配置）。

### iframe 嵌入模式（MSE 用的就是它）

- 激活：iframe `src` 加 `?embed=true&origin=vscode-maa`；嵌入模式**不连 LocalBridge**，文件/设备/调试由宿主（MSE）代理。
- 通信：`postMessage`，信封 `{protocol: "mpe-embed", version: "1.4.0", type, requestId, payload}`，只处理 `protocol` 为 `mpe-embed` 的消息。
- 保存链路：`mpe:saveRequest`（MPE 侧 Ctrl+S）→ 宿主 `mpe:save` → MPE `mpe:saveData` → 宿主写回 → `mpe:saveResult`。所以「保存到 MSE」只更新 TextDocument，落盘要在 VS Code 再保存。
- 权限能力：`readOnly`、`allowCopy`、`allowUndoRedo`、`allowAutoLayout`、`allowSearch`、`allowCustomTemplate`、`hostNodeNavigation`。
- External 节点导航：宿主声明 `hostNodeNavigation` 才委托宿主，否则禁用入口；Anchor 在 iframe 里只读展示、不跳转。

### 性能与架构（了解即可）

- 1.9.3 起针对 300 节点/900 边做了优化：订阅拆分、连线路由缓存、磁吸坐标桶、虚拟渲染、撤销补丁、按需加载。
- 2.0 方向：PI 编辑器、MfwTaskRunner、Desktop 重构、MPE Harness。
