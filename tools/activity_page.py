# -*- coding: utf-8 -*-
"""生成活动提醒页面：读 data/activity.json -> 活动提醒.html（双击用浏览器打开）。

每次活动更新后，改 data/activity.json，再运行本脚本刷新页面。
"""
import datetime as dt
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "data" / "activity.json"
OUT = ROOT / "活动提醒.html"


def main():
    try:
        cfg = json.loads(CFG.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        raise SystemExit("读不到 data/activity.json")

    name = html.escape(str(cfg.get("name", "当期活动")))
    start_raw = str(cfg.get("start", "")).strip()
    end_raw = str(cfg.get("end", "")).strip()
    notice = html.escape(str(cfg.get("notice", "")))
    tasks = [html.escape(str(t)) for t in cfg.get("tasks") or []]
    links = cfg.get("links") or []

    start_dt = None
    try:
        start_dt = dt.datetime.fromisoformat(start_raw) if start_raw else None
    except ValueError:
        pass

    end_dt = None
    try:
        end_dt = dt.datetime.fromisoformat(end_raw) if end_raw else None
    except ValueError:
        pass

    if end_dt:
        now = dt.datetime.now(end_dt.tzinfo) if end_dt.tzinfo else dt.datetime.now()
        delta = end_dt - now
        if delta.total_seconds() <= 0:
            status, remain, color = "已结束", "活动已结束，任务会自动跳过", "#c0392b"
        else:
            days = delta.days
            hours = delta.seconds // 3600
            status, remain, color = "进行中", f"剩余 {days} 天 {hours} 小时", "#1a7f37"
        end_text = end_dt.strftime("%Y-%m-%d %H:%M")
    else:
        status, remain, color = "未配置", "未配置结束时间（按进行中处理）", "#888"
        end_text = "—"

    if start_dt and end_dt:
        time_text = f"{start_dt.strftime('%Y-%m-%d %H:%M')} ~ {end_dt.strftime('%Y-%m-%d %H:%M')}"
    elif end_dt:
        time_text = f"结束 {end_dt.strftime('%Y-%m-%d %H:%M')}"
    else:
        time_text = "—"

    link_html = "".join(
        f'<li><a href="{html.escape(str(item.get("url", "#")), quote=True)}" target="_blank">'
        f'{html.escape(str(item.get("label", "链接")))}</a></li>'
        for item in links
        if isinstance(item, dict)
    )
    task_html = "".join(f"<li>{t}</li>" for t in tasks)

    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>活动提醒 - {name}</title>
<style>
  body {{ margin:0; font-family:"Microsoft YaHei",system-ui,sans-serif; background:#f5f6f8; color:#222; }}
  .wrap {{ max-width:640px; margin:40px auto; background:#fff; border-radius:14px; padding:28px 32px; box-shadow:0 4px 24px rgba(0,0,0,.08); }}
  h1 {{ font-size:22px; margin:0 0 6px; }}
  .status {{ display:inline-block; margin-left:8px; padding:2px 10px; border-radius:999px; font-size:13px; color:#fff; background:{color}; }}
  .end {{ color:#666; font-size:14px; margin:10px 0 18px; }}
  .remain {{ font-size:16px; font-weight:600; color:{color}; margin-bottom:18px; }}
  h2 {{ font-size:15px; color:#888; margin:18px 0 8px; font-weight:600; }}
  ul {{ margin:0; padding-left:20px; line-height:1.9; }}
  a {{ color:#2d6cdf; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{name}<span class="status">{status}</span></h1>
  <div class="end">活动时间：{time_text}</div>
  <div class="remain">{remain}</div>
  <h2>公告 / 说明</h2>
  <p>{notice or "（无）"}</p>
  <h2>相关任务</h2>
  <ul>{task_html or "<li>（无）</li>"}</ul>
  <h2>官方公告链接</h2>
  <ul>{link_html or "<li>（无）</li>"}</ul>
  <p style="color:#999;font-size:12px;margin-top:26px;">数据来自 data/activity.json，改完重新运行 tools/activity_page.py 刷新本页。</p>
</div>
</body>
</html>"""

    OUT.write_text(page, encoding="utf-8")
    print("已生成:", OUT)


if __name__ == "__main__":
    main()
