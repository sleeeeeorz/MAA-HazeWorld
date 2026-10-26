# -*- coding: utf-8 -*-
"""MAA-HazeWorld 项目自检。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
PIPE_DIR = ASSETS / "resource" / "pipeline"
OK = 0
FAIL = 0


def report(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"[PASS] {name} {detail}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {detail}")


def strip_jsonc(text):
    out = []
    in_str = False
    esc = False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < len(text) and text[i + 1] == "/":
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def load_nodes():
    nodes = {}
    for f in sorted(PIPE_DIR.glob("*.json")):
        data = json.loads(strip_jsonc(f.read_text(encoding="utf-8")))
        for name, node in data.items():
            if isinstance(node, dict) and not name.startswith("$__"):
                nodes[name] = node
    return nodes


def iter_refs(node):
    for field in ("next", "on_error"):
        for item in node.get(field) or []:
            target = item if isinstance(item, str) else (item.get("name") if isinstance(item, dict) else None)
            if not target:
                continue
            if target.startswith("[JumpBack]"):
                target = target[len("[JumpBack]"):]
            target = target.split("#")[0]
            if target:
                yield field, target


def main():
    data = json.loads(strip_jsonc((ASSETS / "interface.json").read_text(encoding="utf-8")))
    tasks = data.get("task", [])
    report("interface.json 解析", len(tasks) > 0, f"{len(tasks)} 个任务: {[t.get('name') for t in tasks]}")

    nodes = load_nodes()
    report("节点数", len(nodes) > 100, f"{len(nodes)} 个节点")

    missing = [t.get("entry") for t in tasks if t.get("entry") not in nodes]
    report("任务入口均在节点表中", not missing, f"{len(tasks)} 个入口" + (f"，缺失 {missing}" if missing else "，全部命中"))

    refs = 0
    bad = []
    for name, node in nodes.items():
        for field, target in iter_refs(node):
            refs += 1
            if target not in nodes:
                bad.append(f"{name}.{field} -> {target}")
    report("pipeline 引用", not bad, f"{refs} 条引用" + (f"，悬空 {len(bad)}: {bad[:5]}" if bad else "，无悬空"))

    try:
        from maa.resource import Resource

        res = Resource()
        res.post_bundle(str(ASSETS / "resource")).wait()
        report("资源加载 loaded", bool(res.loaded), f"loaded={res.loaded}")
    except ImportError:
        print("[SKIP] 资源加载检查（未找到 maa 模块，需在 MFA 的 Python 环境下运行）")
    except Exception as exc:  # noqa: BLE001
        report("资源加载 loaded", False, f"异常: {exc}")

    print(f"\nSUMMARY {OK}/{OK + FAIL} 通过")
    raise SystemExit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
