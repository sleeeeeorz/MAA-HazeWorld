"""按周门控：让某个流程「每周只跑一次、且只在指定星期几跑」。

目前用于演习商店：每周兑换一次演习卷（商店周一刷新），当周兑换过就不再兑换。

状态存在项目根目录的 data/weekly_state.json，形如：
    {"演习商店": {"week": "2026-W43", "at": "2026-10-20T21:59:00"}}

pipeline 里这样用：
    "商店检查（演习）": {
        "recognition": {
            "type": "Custom",
            "param": {
                "custom_recognition": "weekly_pending",
                "custom_recognition_param": { "state_key": "演习商店", "weekday": 0 }
            }
        },
        "action": {
            "type": "Custom",
            "param": {
                "custom_action": "mark_weekly_done",
                "custom_action_param": { "state_key": "演习商店" }
            }
        },
        "next": ["演习_副本1"]
    }
weekday：0=周一 … 6=周日。
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition

_AGENT_DIR = Path(__file__).resolve().parent
ROOT = (
    _AGENT_DIR.parent.parent
    if _AGENT_DIR.parent.name == "assets"
    else _AGENT_DIR.parent
)
STATE_FILE = ROOT / "data" / "weekly_state.json"
WEEKDAY_NAMES = "一二三四五六日"


def _parse_param(raw: Any) -> dict:
    """客户端传进来的 param 可能是 dict，也可能是 JSON 字符串。"""
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(str(raw))
    except json.JSONDecodeError:
        print(f"[weekly] 无法解析参数：{raw!r}")
        return {}


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def week_key(day: dt.date | None = None) -> str:
    """ISO 周标识，例如 2026-W43。"""
    day = day or dt.date.today()
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


# 同一个判定只打一次日志：这个识别每轮轮询都会被调用，全打会刷屏
_LAST_LOG: dict[str, tuple[bool, str]] = {}


def _log_once(state_key: str, ok: bool, reason: str) -> None:
    """判定结果没变化就不再打印。"""
    if _LAST_LOG.get(state_key) == (ok, reason):
        return
    _LAST_LOG[state_key] = (ok, reason)
    print(f"[weekly] {'继续' if ok else '跳过'}：{reason}")


def week_done(state_key: str, today: dt.date | None = None) -> bool:
    """这个 state_key 本周是否已经完成过。"""
    today = today or dt.date.today()
    last = (_load_state().get(state_key) or {}).get("week")
    return last == week_key(today)


def should_run(
    state_key: str, weekday: int | None = None, today: dt.date | None = None
) -> tuple[bool, str]:
    """这一周该不该跑：只看这周有没有跑过。

    商店每周一刷新，但"兑换一次"不限星期几——周一没空、周二补上也算这一周。
    weekday 传具体 0~6 时才额外限制只在那一天跑，默认不限制。
    """
    today = today or dt.date.today()

    if weekday is not None and today.weekday() != weekday:
        return (
            False,
            f"今天是周{WEEKDAY_NAMES[today.weekday()]}，设定为只在周{WEEKDAY_NAMES[weekday]}兑换",
        )

    last = (_load_state().get(state_key) or {}).get("week")
    current = week_key(today)
    if last == current:
        return False, f"本周已兑换（{current}），跳过本次"

    return True, f"本周未兑换（{current}），开始兑换"


@AgentServer.custom_recognition("weekly_pending_after")
class WeeklyPendingAfter(CustomRecognition):
    """两个条件同时满足才命中：

    1. require_state_key 本周**已经**完成（比如"演习商店"已经兑换过）
    2. state_key 本周**还没有**完成（比如"补充演习卷"本周没补过）

    用于"某个流程跑过之后，另一个流程才允许每周触发一次"这种场景。
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        param = _parse_param(argv.custom_recognition_param)
        state_key = str(param.get("state_key", "default"))
        require = str(param.get("require_state_key", ""))

        log_key = f"{state_key}|{require}"
        if require and not week_done(require):
            reason = f"{require} 本周还没完成，跳过 {state_key}"
            _log_once(log_key, False, reason)
            return CustomRecognition.AnalyzeResult(box=None, detail=reason)

        ok, reason = should_run(state_key, None)
        _log_once(log_key, ok, reason)
        if not ok:
            return CustomRecognition.AnalyzeResult(box=None, detail=reason)

        return CustomRecognition.AnalyzeResult(box=(0, 0, 0, 0), detail=reason)


@AgentServer.custom_recognition("weekly_pending")
class WeeklyPending(CustomRecognition):
    """命中表示"这周还没跑，该跑了"；不命中表示这周已经跑过。"""

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        param = _parse_param(argv.custom_recognition_param)
        state_key = str(param.get("state_key", "default"))
        weekday = param.get("weekday")
        weekday = int(weekday) if weekday is not None else None

        ok, reason = should_run(state_key, weekday)
        _log_once(state_key, ok, reason)

        if not ok:
            return CustomRecognition.AnalyzeResult(box=None, detail=reason)

        # box 非 None 即视为命中；这里不需要真实坐标
        return CustomRecognition.AnalyzeResult(box=(0, 0, 0, 0), detail=reason)


@AgentServer.custom_action("log_message")
class LogMessage(CustomAction):
    """把 custom_action_param.msg 打到日志里，供流水线在关键节点留痕。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        param = _parse_param(argv.custom_action_param)
        msg = str(param.get("msg", ""))
        if msg:
            print(f"[haze] {msg}")
        return True


GACHA_LOG_FILE = ROOT / "data" / "gacha_log.txt"


def _gacha_log(line: str) -> None:
    """把抽卡数据追加到 data/gacha_log.txt（客户端不转发 stdout 也能查）。"""
    try:
        GACHA_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with GACHA_LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {line}\n")
    except OSError:
        pass


# 抽卡计数：按 task_id 分组，任务一换自动归零
_DRAW_STATE: dict[str, object] = {"task_id": None, "count": 0, "coin": ""}


def _draw_counter(task_id):
    if _DRAW_STATE["task_id"] != task_id:
        _DRAW_STATE["task_id"] = task_id
        _DRAW_STATE["count"] = 0
    return _DRAW_STATE


@AgentServer.custom_action("log_coin")
class LogCoin(CustomAction):
    """把本节点的 OCR 结果打出来（用于日志显示抽卡币数量）。

    OCR 节点自身命中后才会执行动作，所以没命中时不会刷日志。
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        param = _parse_param(argv.custom_action_param)
        label = str(param.get("label", "抽卡币"))

        texts = []
        detail = argv.reco_detail
        if detail:
            for item in (getattr(detail, "all_results", None) or [])[:3]:
                text = getattr(item, "text", None)
                if text:
                    texts.append(text)

        value = " / ".join(texts) if texts else "?"
        print(f"[gacha] {label} = {value}")
        st = _draw_counter(argv.task_detail.task_id)
        st["coin"] = value
        _gacha_log(f"{label} = {value}")
        return True


@AgentServer.custom_action("count_draw")
class CountDraw(CustomAction):
    """每抽一次卡 +1，并打一行"第几次"。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        st = _draw_counter(argv.task_detail.task_id)
        st["count"] = int(st["count"]) + 1
        print(f"[gacha] 第 {st['count']} 次抽卡")
        _gacha_log(f"第 {st['count']} 次抽卡（余额 {st['coin'] or '?'}）")
        return True


@AgentServer.custom_action("report_draw")
class ReportDraw(CustomAction):
    """任务收尾时汇总本次一共抽了多少次。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        st = _draw_counter(argv.task_detail.task_id)
        count = int(st["count"])
        coin = st["coin"] or "?"
        print(f"[gacha] 本次活动抽卡共 {count} 次，最后余额 {coin}")
        _gacha_log(f"抽卡结束：共 {count} 次，最后余额 {coin}")
        st["count"] = 0
        st["coin"] = ""
        return True


@AgentServer.custom_action("mark_weekly_done")
class MarkWeeklyDone(CustomAction):
    """把"这一周已经跑过"记下来，供下次判断。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        param = _parse_param(argv.custom_action_param)
        state_key = str(param.get("state_key", "default"))

        state = _load_state()
        entry = state.setdefault(state_key, {})
        entry["week"] = week_key()
        entry["at"] = dt.datetime.now().isoformat(timespec="seconds")
        _save_state(state)

        print(f"[weekly] 已记录 {state_key} -> {entry['week']}")
        return True


ACTIVITY_FILE = ROOT / "data" / "activity.json"


@AgentServer.custom_recognition("activity_active")
class ActivityActive(CustomRecognition):
    """活动是否还在进行：按 data/activity.json 的 end 判断。

    命中 = 活动进行中（继续跑活动任务）；不命中 = 已结束（跳过）。
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        try:
            cfg = json.loads(ACTIVITY_FILE.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return CustomRecognition.AnalyzeResult(
                box=(0, 0, 0, 0), detail="未找到活动配置，按进行中处理"
            )

        end = str(cfg.get("end", "")).strip()
        if not end:
            return CustomRecognition.AnalyzeResult(
                box=(0, 0, 0, 0), detail="活动未配置结束时间，按进行中处理"
            )

        try:
            end_dt = dt.datetime.fromisoformat(end)
        except ValueError:
            return CustomRecognition.AnalyzeResult(
                box=(0, 0, 0, 0), detail=f"结束时间格式错误：{end}，按进行中处理"
            )

        now = dt.datetime.now(end_dt.tzinfo) if end_dt.tzinfo else dt.datetime.now()
        if now <= end_dt:
            return CustomRecognition.AnalyzeResult(
                box=(0, 0, 0, 0), detail=f"活动进行中，截止 {end}"
            )

        print(f"[activity] 活动已结束（{end}），跳过活动任务")
        return CustomRecognition.AnalyzeResult(box=None, detail=f"活动已结束：{end}")
