"""一键查看最近一次运行的失败点。

用法：
    python tools/show_log.py           # 看最近一次
    python tools/show_log.py -n 30     # 多看几条节点流转
    python tools/show_log.py --open    # 看完直接打开最接近的那张失败截图

日志来源（按优先级）：
    1. MaaPipelineEditor 的 maafw.log（MPE 里跑任务时写这里）
    2. 工程自己的 debug/maafw.log（agent 进程写的）

MaaFramework 的节点日志不会显示在 MPE 的「运行日志」面板上，
面板只收 Agent 子进程的 stdout，所以失败时面板往往是空的。
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LB_LOGS = Path.home() / "AppData" / "Roaming" / "MaaPipelineEditor" / "LocalBridge" / "logs"

ANSI = re.compile(r"\x1b\[[0-9;]*m")

# 引擎噪音：画面轮询、显卡探测、连接生命周期，跟"卡在哪"无关
NOISE = re.compile(
    r"MuMuPlayerExtras|GpuOptionWin32|perfer_gpu|Transceiver\.cpp|LibraryHolder"
    r"|MaaAgentServer\.cpp|AgentServer\.cpp\]\[L\d+\].*(request_msg_loop|join|shut_down)"
    r"|MaaAgentClient|AgentClient\.cpp\]\[L1[56]"
)

TIME = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\.\d+\]")
TIMEOUT = re.compile(r"Task timeout \[pretask\.name=([^\]]+)\]")
HIT = re.compile(r"reco hit \[result\.name=([^\]]+)\]")
DONE = re.compile(r'node done \[result=.*?"name":"([^"]+)"')
SHOT_NAME = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})-(\d{2})\.(\d{2})\.(\d{2})\.(\d{3})")


def log_candidates() -> list[Path]:
    paths = []
    if LB_LOGS.is_dir():
        paths.extend(sorted(LB_LOGS.glob("maafw*.log"), key=lambda p: p.stat().st_mtime, reverse=True))
    paths.append(ROOT / "debug" / "maafw.log")
    return [p for p in paths if p.is_file()]


def tail_lines(path: Path, max_bytes: int = 900_000) -> list[str]:
    size = path.stat().st_size
    with path.open("rb") as f:
        if size > max_bytes:
            f.seek(size - max_bytes)
            f.readline()
        raw = f.read()
    return [ln for ln in ANSI.sub("", raw.decode("utf-8", errors="replace")).splitlines() if ln.strip()]


def short(line: str, width: int = 160) -> str:
    return line if len(line) <= width else line[:width] + "…"


def collect_shots(limit: int = 5) -> list[tuple[dt.datetime, Path]]:
    """收集失败截图：MPE 的 on_error 优先，其次工程 debug/on_error。"""
    dirs = [LB_LOGS / "on_error", ROOT / "debug" / "on_error"]
    shots: list[tuple[dt.datetime, Path]] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if not f.is_file() or f.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                continue
            m = SHOT_NAME.match(f.name)
            if m:
                y, mo, da, h, mi, s, ms = (int(x) for x in m.groups())
                when = dt.datetime(y, mo, da, h, mi, s, ms * 1000)
            else:
                when = dt.datetime.fromtimestamp(f.stat().st_mtime)
            shots.append((when, f))
    shots.sort(key=lambda t: t[0], reverse=True)
    return shots[:limit]


def open_file(path: Path) -> None:
    try:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as exc:
        print(f"  （打开失败：{exc}）")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--lines", type=int, default=15, help="显示多少条节点流转")
    ap.add_argument("--open", action="store_true", help="打开最接近失败时刻的截图")
    args = ap.parse_args()

    logs = log_candidates()
    if not logs:
        print("找不到 maafw 日志。先在 MPE 里跑一次任务再看。")
        return 1

    log = logs[0]
    stamp = dt.datetime.fromtimestamp(log.stat().st_mtime)
    print(f"日志文件: {log}")
    print(f"           最后写入 {stamp:%Y-%m-%d %H:%M:%S}\n")

    lines = [ln for ln in tail_lines(log) if not NOISE.search(ln)]

    # 1. 失败点
    timeouts = [(TIME.search(ln).group(1), TIMEOUT.search(ln).group(1)) for ln in lines if TIME.search(ln) and TIMEOUT.search(ln)]
    last_fail_at = None
    print("=== 最后一次卡住的节点 ===")
    if timeouts:
        for when, name in timeouts[-3:]:
            print(f"  {when[11:]}  等 next 超时 → 节点「{name}」")
        last_fail_at = dt.datetime.strptime(timeouts[-1][0], "%Y-%m-%d %H:%M:%S")
        print("\n  （这个节点的 next 列表没有任何节点命中，流程到此中断）")
    else:
        print("  没找到 Task timeout，可能不是超时失败，看下面的错误行。")

    # 2. 节点流转
    print(f"\n=== 最近 {args.lines} 条节点流转 ===")
    flow = []
    for ln in lines:
        t = TIME.search(ln)
        if not t:
            continue
        ts = t.group(1)[11:]
        if (m := HIT.search(ln)):
            flow.append(f"{ts}  命中  {m.group(1)}")
        elif (m := DONE.search(ln)):
            flow.append(f"{ts}  完成  {m.group(1)}")
    for row in flow[-args.lines:]:
        print("  " + row)
    if not flow:
        print("  （没有节点流转记录）")

    # 3. 错误与警告
    print("\n=== 错误 / 警告 ===")
    bad = [ln for ln in lines if "[ERR]" in ln or "[WRN]" in ln]
    for ln in bad[-8:]:
        print("  " + short(ln))

    # 4. 失败截图
    shots = collect_shots()
    print("\n=== 失败截图（MaaFramework 自动存的）===")
    best = None
    if shots:
        if last_fail_at:
            best = min(shots, key=lambda t: abs((t[0] - last_fail_at).total_seconds()))
        else:
            best = shots[0]
        for when, f in shots:
            mark = "  ← 最接近失败时刻" if f == best[1] else ""
            print(f"  {when:%H:%M:%S}  {f.stat().st_size / 1024:>7.0f} KB  {f.name}{mark}")
        print(f"\n  目录: {best[1].parent}")
    else:
        print("  没找到截图（save_on_error 没开，或这次不是失败结束）")

    print("\n提示：MPE 的「运行日志」面板只显示 Agent 子进程输出，节点日志永远在这里看。")

    if args.open and best:
        print(f"\n打开: {best[1].name}")
        open_file(best[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
