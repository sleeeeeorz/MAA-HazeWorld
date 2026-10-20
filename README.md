# MAA-HazeWorld

**《苍雾世界》日常自动化脚本**，基于 MaaFramework 的图像识别 + 模拟点击实现。

脚本不修改游戏文件、不读写游戏数据；任务逻辑全部是可读的 JSON 流水线，用 MaaPipelineEditor 拖节点就能改。

## 功能

- √ **游戏启动**：拉起游戏、过启动页、回到主界面。设置项：启动等待时长、启动时是否顺手签到
- √ **每日演习**：打演习。设置项：兑换演习商店（每周一自动判断，当周只兑一次，兑过就跳过）
- √ **指挥室**：远征派遣、收取
- √ **当期活动**：扫荡活动关卡。设置项：扫荡后顺便抽卡
- √ **通行证**：领取通行证任务奖励
- √ **商城**：领取免费礼包
- √ **每日任务**：每日 / 每周 / 每月三栏。设置项：三栏可分别开关；6 档可领取奖励（100 / 90 / 150 / 150 / 300 / 450 点）各自独立开关
- √ **关闭游戏**：关闭游戏进程

> 可领取的档位按点数解锁，点数不够时界面上不会出现，属正常现象。长期达不到的档位建议直接在设置里关掉，能少等一轮超时。

## 环境要求

- Windows 10 / 11 x64
- 支持 ADB 的安卓模拟器（MuMu、雷电、逍遥等），推荐 1280×720 横屏
- 《苍雾世界》，包名 `com.feimo.hazeworld.main`

## 安装与使用

1. 到 [Releases](https://github.com/sleeeeeorz/MAA-HazeWorld/releases/latest) 下载 `MAA-HazeWorld-win-x86_64-*.zip`
2. 解压到任意目录（路径别带中文和空格，避免识别异常）
3. 启动模拟器，确认游戏能正常进入
4. 运行解压目录里的主程序，在「设置 → 连接设置」填模拟器 ADB 地址（MuMu 常见 `127.0.0.1:16384`，雷电 `5555`）
5. 刷新截图确认能看到游戏画面，左侧勾选任务，然后开始

分辨率不是 720p 也能用：脚本会把截图缩放到短边 720 再识别，模板图也是按 720 做的。

## 常见问题

**Agent 启动或连接失败：启动准备超时（3m0s）**

每周商店的判断用到了 Agent 子进程（`agent/`）。上一轮异常中断会残留注册，导致下一次连接被判失败。在客户端里重新加载一次项目，或重启客户端即可。

**某个节点一直识别不到**

① 打开 `config/maa_option.json` 里的 `save_draw`，看识别框画在哪；② 确认当前画面真的在预期界面；③ 模板图必须按 720 缩放后的画面裁剪；④ 换一处更有辨识度的区域重新裁。

**OCR 认不出字**

OCR 模型在 `assets/resource/model/ocr/`，`det.onnx`、`rec.onnx`、`keys.txt` 缺任何一个整个资源包都会加载失败。另外 `expected` 文案要和实际识别结果一致，标点、繁简、全半角都算不一样。

**抽卡任务只抽一次就退出**

`关闭抽卡结果` 这个节点默认是回主界面结束。想连续抽，把它改成回 `抽卡` 节点。

## 目录结构

```
MAA-HazeWorld/
├── assets/
│   ├── interface.json          # 项目声明：控制器、资源包、任务、设置项
│   ├── config/                 # 客户端配置缓存
│   └── resource/
│       ├── image/              # 模板图（按 720 裁剪）
│       ├── model/ocr/          # OCR 模型
│       └── pipeline/           # 任务流水线
├── agent/                      # 自定义识别 / 动作（每周商店判断）
├── tools/                      # 打包与校验脚本
├── docs/                       # 开发文档
└── .github/workflows/          # 自动打包发布
```

## 开发

安装依赖并自检：

```
python -m pip install -r tools/requirements.txt
python tools/check.py
```

注意包名是 `maafw`，不是 `maa`。

相关资料：

- 流水线字段：[任务流水线协议](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/3.1-%E4%BB%BB%E5%8A%A1%E6%B5%81%E6%B0%B4%E7%BA%BF%E5%8D%8F%E8%AE%AE.md)
- 项目声明：[ProjectInterface V2](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/3.3-ProjectInterfaceV2%E5%8D%8F%E8%AE%AE.md)
- 自定义逻辑：`agent/my_weekly.py`，按 ISO 周判断本周是否已兑换

改完流水线后，在 MPE 里重新加载项目再测。

## 免责声明

本项目仅供学习 MaaFramework 与自动化测试技术使用。

- 请遵守《苍雾世界》用户协议，游戏内公告明确禁止使用第三方工具，封号风险自负
- 脚本只做截图识别与模拟点击，不修改客户端、内存或游戏数据
- 因使用本脚本产生的任何后果由使用者自行承担

## 致谢

- [MaaFramework](https://github.com/MaaXYZ/MaaFramework)：底层框架
- [MaaPracticeBoilerplate](https://github.com/MaaXYZ/MaaPracticeBoilerplate)：项目骨架与 CI
- [MFAAvalonia](https://github.com/SweetSmellFox/MFAAvalonia)：客户端
- 以及所有提交 issue 和 PR 的朋友

如果这个项目帮到了你，点个 Star 支持一下。
