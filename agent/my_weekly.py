"""按周门控：让某个流程「每周只跑一次、且只在指定星期几跑」。

目前用于演习商店：每周一兑换演习卷，当周兑换过就不再兑换。

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

ROOT = Path(__file__).resolve().parents[1]
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


def should_run(
    state_key: str, weekday: int = 0, today: dt.date | None = None
) -> tuple[bool, str]:
    """今天该不该跑：既要星期对得上，又要这周还没跑过。"""
    today = today or dt.date.today()

    if today.weekday() != weekday:
        return (
            False,
            f"今天是周{WEEKDAY_NAMES[today.weekday()]}，只在周{WEEKDAY_NAMES[weekday]}兑换",
        )

    last = (_load_state().get(state_key) or {}).get("week")
    current = week_key(today)
    if last == current:
        return False, f"{state_key}：本周 {current} 已兑换过"

    return True, f"{state_key}：本周 {current} 还没兑换"


@AgentServer.custom_recognition("weekly_pending")
class WeeklyPending(CustomRecognition):
    """命中表示"该跑了"；不命中表示今天不跑或这周已经跑过。"""

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        param = _parse_param(argv.custom_recognition_param)
        state_key = str(param.get("state_key", "default"))
        weekday = int(param.get("weekday", 0))

        ok, reason = should_run(state_key, weekday)
        print(f"[weekly] {'继续' if ok else '跳过'}：{reason}")

        if not ok:
            return CustomRecognition.AnalyzeResult(box=None, detail=reason)

        # box 非 None 即视为命中；这里不需要真实坐标
        return CustomRecognition.AnalyzeResult(box=(0, 0, 0, 0), detail=reason)


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
