from __future__ import annotations

import sys
from typing import Any, Dict

from .manager import Manager


def _clear_screen() -> None:
    # ANSI 清屏 + 光标归位
    print("\033[2J\033[H", end="")


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    # 简单文本表格渲染（无依赖）
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(cell))
    def fmt_row(cols: list[str]) -> str:
        return " | ".join(col.ljust(widths[i]) for i, col in enumerate(cols))
    sep = "-+-".join("-" * w for w in widths)
    lines = [fmt_row(headers), sep]
    for r in rows:
        lines.append(fmt_row(r))
    return "\n".join(lines)


def _render_status(data: Dict[str, Any]) -> str:
    q = data.get("queue", {})
    bots = data.get("bots", [])
    completed_ids = data.get("completed_ids", [])

    # Pending - VIP
    vip_rows = [[str(o.id), getattr(o, "type", "VIP"), getattr(o, "status", "PENDING")] for o in q.get("vip", [])]
    vip = _format_table(["ID", "Type", "Status"], vip_rows) if vip_rows else "<empty>"

    # Pending - Normal
    normal_rows = [[str(o.id), getattr(o, "type", "NORMAL"), getattr(o, "status", "PENDING")] for o in q.get("normal", [])]
    normal = _format_table(["ID", "Type", "Status"], normal_rows) if normal_rows else "<empty>"

    # Bots
    bot_rows = [[str(b.get("bot_id")), b.get("state", ""), str(b.get("current_order_id"))] for b in bots]
    bots_tbl = _format_table(["BotID", "State", "CurrentOrder"], bot_rows) if bot_rows else "<none>"

    # Completed (IDs only)
    compl_tbl = ", ".join(str(i) for i in completed_ids) if completed_ids else "<none>"

    parts = [
        "== Pending / VIP ==\n" + vip,
        "\n\n== Pending / Normal ==\n" + normal,
        "\n\n== Bots ==\n" + bots_tbl,
        f"\n\n== Complete (last {len(completed_ids)}) ==\n" + compl_tbl,
    ]
    return "\n".join(parts)


def print_result(res: Dict[str, Any]) -> None:
    if not isinstance(res, dict):
        print(res)
        return
    if res.get("ok") is False:
        print(f"ERR: {res.get('error')}")
        if "usage" in res:
            print(res["usage"]) 
    else:
        data = res.get("data")
        if isinstance(data, str):
            print(data)
        elif isinstance(data, dict) and data.get("clear"):
            _clear_screen()
        elif isinstance(data, dict) and data.get("queue") is not None:
            print(_render_status(data))
        else:
            print(res)


def repl() -> None:
    mgr = Manager()
    print("Type 'help' to see commands. Type 'exit' to quit.")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        res = mgr.handle_cmd(line)
        if isinstance(res, dict):
            data = res.get("data")
            if isinstance(data, dict) and data.get("exit"):
                break
        print_result(res)
    try:
        mgr.shutdown()
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        repl()
        return 0
    # one-shot mode: join argv to a single command
    mgr = Manager()
    cmd = " ".join(argv)
    res = mgr.handle_cmd(cmd)
    print_result(res)
    mgr.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
