# MAA-HazeWorld 项目总结

> 用途：整体迁移 / 交接。当前版本 **0.2.7**（tag `v0.2.7`）。

---

## 1. 项目概况

| 项 | 值 |
|---|---|
| 游戏 | 《苍雾世界》，包名 `com.feimo.hazeworld.main` |
| 框架 | MaaFramework **v5.14.3**，ProjectInterface **V2** |
| 界面客户端 | MPE（MaaPipelineEditor）、MFAAvalonia |
| 控制器 | `Adb`「安卓端」，`display_short_side: 720` |
| 资源 | `官服` → `./resource` |
| agent | `python` + `./agent/main.py`（相对 `assets/`） |
| 仓库 | https://github.com/sleeeeeorz/MAA-HazeWorld |
| 许可证 | MIT |

---

## 2. 目录结构（迁移重点）

| 路径 | 作用 | 迁移 |
|---|---|---|
| `assets/interface.json` | PI v2 入口，任务/选项定义 | **要** |
| `assets/resource/pipeline/` | 10 个流水线文件 | **要** |
| `assets/resource/image/` | 模板图（约 40 张） | **要** |
| `assets/resource/model/ocr/` | OCR 模型（det/rec/keys） | **要** |
| `assets/agent/` | Python agent（**必须在 assets 内**） | **要** |
| `tools/` | install / configure / show_log / fix_mpe_ocr | **要** |
| `data/` | 运行时状态（weekly_state、gacha_log） | 按需（想要历史就带） |
| `debug/` | 运行日志与失败截图 | 可删 |
| `deps/` | 本地依赖，162 MB，gitignore | 不用带（CI 会下） |
| `backup/` | 改动备份，0.2 MB | 可删 |
| `.github/` | CI（出 4 个包） | 要 |
| 根配置 | `package.json`、`maatools.config.mts`、`requirements.txt`、`version.txt`、`auto_release.bat` | 要 |

流水线文件：

```
00_回主界面.json    6 个任务的"回主界面"前置
游戏初始化.json     启动链（更新 / 维护公告 / 停服）
演习.json           商店兑换 + 领结算/撤离
指挥室.json
活动.json           扫荡 + 体力检查
活动抽卡.json       抽卡循环 + 统计
通行证.json
商城.json
每X任务.json        每日/每周/每月任务分段
关闭游戏.json
```

---

## 3. 三种运行方式

| 方式 | 用的路径 | 说明 |
|---|---|---|
| **MPE** | `D:\MAA\MAA-HazeWorld`（读 `assets/`） | 调试用，改完即生效 |
| **MFAAvalonia** | 打包目录（如 `MAA-HazeWorld-win-x86_64-v0.2.7`） | 读自己目录里的 `resource/`，与源码无关 |
| **AUTO-MAS** | 导入时把 `assets/` 平铺成视图 | 所以 agent 必须放在 `assets/agent/` |

打包：

```bat
python tools/install.py v0.2.7 win x86_64
```

需要 `deps/` 里有 MaaFramework 与 MFAAvalonia（CI 自动下载，本地要手动备）。

---

## 4. 任务与流程

### 游戏初始化（入口 → `拉起游戏`）

```
拉起游戏（StartApp）
 ├─ 游戏更新（OCR「游戏需要下载」）
 │    └→ 新建节点32（「正在下载资源」）→ 维护公告（「维护公告」）
 │          └→ 新建节点35（点确认）→ 游戏停服ing → 关闭游戏
 └─ 游戏初始化（首页活动UI）→ TOUCH TO START → 点击签到 → 获得资源 → 返回主界面 → 设置
```

**停服/维护时自动关游戏，任务不报错。**

### 其余任务（入口 → `X·入口`）

```
X·入口 → X·主界面判断（识别设置齿轮）
            ├─ 命中 → 原任务
            └─ 未命 → X·返回（点左上角返回）→ 再判断（max_hit 8）
```

意义：前一个任务把游戏带偏（比如停留在商城）时，后一个任务会自己退回主界面，不再连挂。

### 演习（C 流程）

```
演习·入口 → 回主界面 → 演习（合并）
   ├─ 商店检查（每周）：命中 → 演习_副本1 → 兑换商店 → 选券 → MAX → 确认购买
   │      → 关闭弹窗 → 返回主界面（循环退）→ 重进演习 → 代理完成/代理作战
   └─ 未命中 → 演习 → 券检查（OCR 右上角）
            ├─ 有券（^[1-9]\d*/）→ 代理完成 → 等待确认界面 → 确认（演习）
            └─ 无券 / 读不到        → 撤离（演习）
                                          └→ 复点左上角返回 → 识别设置齿轮 → 结束
```

- **券为 0 不开代理作战，直接撤离；**
- 有券只领「代理完成」结算 → 确认 → 撤离，**不再开新代理**（C 流程）。

### 活动

```
活动·入口 → 回主界面 → 体力识别（OCR 顶部体力条 [650,21,116,27]）
   ├─ ≥42 → 活动 → 闪耀之始 → 划到顶部 → 关卡 → 扫荡 → MAX → 开始扫荡 → 确认
   │        → 返回主页 → 确认返回 → 活动-抽卡（开关控制）
   └─ <42 → 体力不足（打日志）→ 结束任务
```

### 活动抽卡

```
活动-抽卡 → 抽卡点（点抽卡入口，可翻页）
   → 初判（OCR 抽卡币 [1111,8,103,29]）
        ├─ 1~50   → 抽卡_单次 → 关详情 → 计数 → 回主界面
        └─ 其他   → 初判2
              ├─ 0  → 回主界面（跳过）
              └─ 其他 → 抽卡（循环）
                   抽卡 → 关详情 → 计数 → 余额判断
                         ├─ 读到 0 → 回主界面
                         └─ 非 0   → 再抽卡（max_hit 20）
```

每抽一次最多扣 50，余额必然归 0，次数自然等于 `ceil(币/50)`。

---

## 5. agent 自定义项

`assets/agent/my_weekly.py`：

| 名称 | 类型 | 用途 |
|---|---|---|
| `weekly_pending` | 识别 | 本周没完成 → 命中（商店周判断） |
| `weekly_pending_after` | 识别 | 前置状态本周已完成 + 目标状态未完成 |
| `mark_weekly_done` | 动作 | 把某状态记为"本周已完成" |
| `log_message` | 动作 | 打一行自定义日志 |
| `log_coin` | 动作 | 输出当前节点 OCR 结果（抽卡币）并写文件 |
| `count_draw` | 动作 | 抽卡计数 +1 |
| `report_draw` | 动作 | 汇总本次抽卡次数 |

模板自带、当前未使用：`find_smallest_number`、`click_target`。

**agent 路径推算**：父目录名是 `assets` 就再上一层作为项目根，否则取父目录（兼容源码 / 打包 / AUTO-MAS 视图三种形态）。

---

## 6. 数据与日志

| 文件 | 内容 |
|---|---|
| `data/weekly_state.json` | `{"演习商店": {"week": "2026-W43", "at": "..."}}` |
| `data/gacha_log.txt` | 抽卡明细：进界面币数 / 第 N 次 / 剩余 / 汇总 |
| `debug/maafw.log` | MaaFramework 节点日志（定位失败用） |
| `debug/on_error/*.png` | 失败时刻截图（按节点名命名） |

一键看日志：`tools/show_log.bat`（输出最后失败节点、节点流转、错误、对应截图）。

---

## 7. 版本演进（本次会话）

| 版本 | 内容 |
|---|---|
| 0.2.4 / 0.2.5 | 演习商店合并、每周判断、任务分段开关 |
| 0.2.5.1 | 支持四位版本号；CI 出 4 个包（win/linux × x64/arm64） |
| 0.2.5.2 | CI 的 `maatools` 忽略 `mpe-config`，check 转绿 |
| 0.2.6 | 活动抽卡重做（先读币数、每 50 一次、0 跳过）；agent 迁入 `assets/agent` 适配 AUTO-MAS |
| 0.2.7 | 回主界面前置、启动链接回、体力检查、演习 C 流程、抽卡统计写文件、超时 5s、清理废弃节点 |

---

## 8. 迁移到 D 盘工作区

### 要复制

```
assets\            （interface + resource + agent，全部）
tools\
data\              （想保留每周状态和抽卡历史就带上）
.github\
requirements.txt  package.json  package-lock.json  pnpm-lock.yaml
maatools.config.mts  version.txt  auto_release.bat  README.md  LICENSE
.editorconfig  .gitattributes  .gitignore  .prettierrc  .prettierignore
```

### 不用复制

```
deps\      162 MB，gitignore，CI 会重新下
backup\    改动备份，可删
debug\     运行日志
```

### 迁移后必须改的绝对路径

1. **`tools/fix_mpe_ocr.bat`** —— 里面写死了
   - `D:\MAA\MPE Desktop`
   - `D:\MAA\MAA-HazeWorld\assets\resource\model`
   迁移后改成新路径。

2. **MPE 的 OCR 模型链接**（系统级，不在仓库里）：

   ```bat
   mklink /J "D:\MAA\MPE Desktop\model" "<新项目路径>\assets\resource\model"
   ```

   不建这个链接，MPE 的「原生 OCR」会报 `Failed to load det or rec`。

3. **MFAAvalonia 的配置** —— 它指向某个打包目录，与源码路径无关；换目录后重新指向新包即可。

4. **git remote** —— 不变，仍是 `sleeeeeorz/MAA-HazeWorld`。

### 迁移后自检

1. `python tools/show_log.py` 能跑；
2. 用 maafw 加载：

```python
from maa.resource import Resource
r = Resource(); r.post_bundle(r"<新路径>\assets\resource").wait()
print(r.loaded, len(r.node_list))     # 期望 True / 158
```

3. 8 个任务入口都存在（`interface.json` 的 `task[].entry`）；
4. agent 握手：`AgentClient.create_tcp()` + 启动 `assets/agent/main.py`，应注册 7 个自定义项。

---

## 9. 已知问题与注意点

| 项 | 说明 |
|---|---|
| MPE 原生 OCR | 依赖 `MPE Desktop\model` 目录链接，MPE 升级会丢，重跑 `fix_mpe_ocr.bat` |
| MPE 前端 OCR | Tesseract.js 需联网下模型，本机不识字，**统一用原生** |
| 回主界面 | 只认 `设置.png`（右上角齿轮），UI 改版会失效 |
| 撤离 | 只认 `左上角返回.png`，没有该箭头的界面退不出去（最多 6 次） |
| 体力阈值 | 写死 42（作战准备消耗），关卡变要改正则 |
| 抽卡币 ROI | `[1111,8,103,29]`，界面改版需重调 |
| 演习券 ROI | `[1085,15,165,45]` |
| 体力 ROI | `[650,21,116,27]` |
| 抽卡循环 | 假设"每抽最多扣 50、余额会被扣到 0" |
| MFA 不转发 agent stdout | 抽卡数据看 `data/gacha_log.txt`，不看面板 |
| `check` workflow | 已忽略 `mpe-config` 元数据，保持 `maatools.config.mts` 那行别删 |

---

## 10. 发版

```bat
auto_release.bat
```

- 输入 `X.Y.Z` 或 `X.Y.Z.W`；直接回车 = 第三段 +1；
- 会自动 `git add/commit/tag/push`；
- tag 必须是 `v*`，CI 才会出包；
- 产出 4 个 zip（win/linux × x86_64/aarch64）。

手动等价操作：

```bat
git add .
git commit -m "说明"
git tag v0.2.8
git push origin main
git push origin v0.2.8
```
