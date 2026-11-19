#!/usr/bin/env python3
"""Zeit je Jira-Ticket aus lokalen Claude-Code-Transkripten (~/.claude/projects/**/*.jsonl) schaetzen.

Aufruf:
  python claude_sessions_time.py --from 2026-11-13 --to 2026-11-16 [--gap 15] [--json sessions.json]

Prinzip:
  * Jede Nachricht (user/assistant) ist ein Zeitstempel. Nachrichten mit <= GAP Minuten Abstand bilden
    einen Arbeitsblock; die Blockdauer ist die aktive Zeit (Mindestwert --min-block).
  * Ticket-Keys werden gewichtet: Nennung durch den Nutzer oder als Jira-Tool-Parameter (issueIdOrKey)
    = stark; Nennung nur im Assistententext = schwach. Ein Block geht an seine starken Keys; ohne starke
    Keys an 1-3 schwache; nennt er mehr, ist es eine Uebersicht (Ticket-Radar, Wochenstatus) und wird
    nicht zugeordnet.
  * In Berichts-Sitzungen (MicDrop, Wochenstatus, Tagesbericht) zaehlen nur Keys, die der Nutzer selbst
    schreibt - dort liest Claude per Tool viele fremde Tickets.
  * Automatische Laeufe (scheduled tasks) sind keine Arbeitszeit und werden getrennt ausgewiesen.
  * tool_result-Inhalte (Jira-Antworten) werden nie nach Keys durchsucht.
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

KEY_RE_DEFAULT = r"\b(?:TECH|SHIP|F1SUP|P1SUP|AWIWESUP|BBCSUP|CBCSUP|OWOPSUP|SAL)-\d+\b"
REPORT_TITLE_RE = re.compile(r"micdrop|wochenstatus|ticket-?radar|tagesbericht|t[aä]glichkeitsbericht|feierabend", re.I)
STRONG_TOOL_KEYS = ("issueIdOrKey", "issueKey")
MAX_WEAK_KEYS = 3


def winpath(p):
    m = re.match(r"^/([a-zA-Z])/(.*)$", p or "")
    return f"{m.group(1).upper()}:/{m.group(2)}" if m else p


def berlin_offset(dt_utc):
    y = dt_utc.year

    def last_sunday(month):
        d = date(y, month + 1, 1) - timedelta(days=1)
        return d - timedelta(days=(d.weekday() + 1) % 7)

    start = datetime.combine(last_sunday(3), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=1)
    end = datetime.combine(last_sunday(10), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=1)
    return timedelta(hours=2) if start <= dt_utc < end else timedelta(hours=1)


def to_berlin(dt_utc):
    try:
        from zoneinfo import ZoneInfo
        return dt_utc.astimezone(ZoneInfo("Europe/Berlin"))
    except Exception:
        return dt_utc.astimezone(timezone(berlin_offset(dt_utc)))


def parse_ts(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def split_content(rec):
    """-> (user_text, assistant_text, strong_tool_text, is_tool_result)"""
    msg = rec.get("message") or {}
    c = msg.get("content")
    rtype = rec.get("type")
    if isinstance(c, str):
        return (c if rtype == "user" else "", c if rtype == "assistant" else "", "", False)
    if not isinstance(c, list):
        return ("", "", "", False)
    if c and all(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
        return ("", "", "", True)
    u, a, s = [], [], []
    for b in c:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if t == "text":
            (u if rtype == "user" else a).append(b.get("text") or "")
        elif t == "tool_use":
            inp = b.get("input")
            if isinstance(inp, dict):
                for k in STRONG_TOOL_KEYS:
                    v = inp.get(k)
                    if isinstance(v, str):
                        s.append(v)
                for k in ("summary", "commentBody", "description"):
                    v = inp.get(k)
                    if isinstance(v, str):
                        a.append(v)
    return ("\n".join(u), "\n".join(a), "\n".join(s), False)


def session_title(path, first_prompt, title_records):
    d = os.path.join(os.path.dirname(path), os.path.splitext(os.path.basename(path))[0])
    ct = os.path.join(d, "custom-title.json")
    if os.path.exists(ct):
        try:
            with open(ct, encoding="utf-8") as f:
                t = json.load(f).get("customTitle")
                if t:
                    return t
        except Exception:
            pass
    if title_records:
        return title_records[-1]
    fp = (first_prompt or "").strip().splitlines()
    return fp[0][:80] if fp else os.path.basename(path)


def cluster(times, gap):
    blocks = []
    for t in sorted(times):
        if blocks and (t - blocks[-1][1]) <= gap:
            blocks[-1][1] = t
        else:
            blocks.append([t, t])
    return [(a, b) for a, b in blocks]


def fmt(dt):
    return dt.strftime("%d.%m. %H:%M")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="d_from", required=True)
    ap.add_argument("--to", dest="d_to", required=True)
    ap.add_argument("--gap", type=int, default=15, help="Minuten Stille, die einen Arbeitsblock beenden")
    ap.add_argument("--min-block", type=int, default=2, help="Mindestminuten je Block")
    ap.add_argument("--projects-dir", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--keys", default=KEY_RE_DEFAULT)
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()

    key_re = re.compile(a.keys)
    gap = timedelta(minutes=a.gap)
    d_from = datetime.fromisoformat(a.d_from).date()
    d_to = datetime.fromisoformat(a.d_to).date()
    lo = datetime.combine(d_from, datetime.min.time(), tzinfo=timezone.utc) - timedelta(hours=3)
    hi = datetime.combine(d_to, datetime.max.time(), tzinfo=timezone.utc) + timedelta(hours=3)

    sessions = {}
    for path in glob.glob(os.path.join(winpath(a.projects_dir), "*", "*.jsonl")):
        try:
            if datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc) < lo:
                continue
        except OSError:
            continue
        events, titles, first_prompt, cwd, automated = [], [], None, None, False
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                rtype = rec.get("type")
                if rtype == "custom-title":
                    t = rec.get("customTitle") or rec.get("title")
                    if t:
                        titles.append(t)
                    continue
                if rtype not in ("user", "assistant"):
                    continue
                if rtype == "user" and (rec.get("turnOrigin") == "scheduled" or rec.get("promptSource") == "system"):
                    automated = True
                ts = parse_ts(rec.get("timestamp", ""))
                if not ts or ts < lo or ts > hi:
                    continue
                cwd = cwd or rec.get("cwd")
                u, asst, strong_txt, is_result = split_content(rec)
                if u.strip() and first_prompt is None and not u.lstrip().startswith("<"):
                    first_prompt = u
                user_keys = set(m.group(0) for m in key_re.finditer(u))
                tool_keys = set(m.group(0) for m in key_re.finditer(strong_txt))
                weak = set(m.group(0) for m in key_re.finditer(asst))
                events.append((ts, user_keys, tool_keys, weak))
        if not events:
            continue
        sid = os.path.splitext(os.path.basename(path))[0]
        title = session_title(path, first_prompt, titles)
        report = bool(REPORT_TITLE_RE.search(title or "") or REPORT_TITLE_RE.search(first_prompt or ""))
        local = []
        for ts, uk, tk, wk in events:
            lt = to_berlin(ts)
            if d_from <= lt.date() <= d_to:
                strong = uk if report else (uk | tk)
                local.append((lt, strong, wk - strong))
        if not local:
            continue
        sessions[sid] = {"cwd": cwd, "title": title, "events": local, "automated": automated, "report": report}

    per_ticket = defaultdict(lambda: {"minutes": 0.0, "blocks": [], "first": None, "last": None})
    other_blocks, session_rows = [], []
    for sid, s in sessions.items():
        times = [e[0] for e in s["events"]]
        blocks = cluster(times, gap)
        total = 0.0
        all_keys = set()
        for b0, b1 in blocks:
            mins = max((b1 - b0).total_seconds() / 60.0, a.min_block)
            total += mins
            strong, weak = set(), set()
            for t, st, wk in s["events"]:
                if b0 <= t <= b1:
                    strong |= st
                    weak |= wk
            weak -= strong
            if s["automated"]:
                kind, keys = "automatisch", set()
            elif strong:
                kind, keys = "stark", strong
            elif weak and len(weak) <= MAX_WEAK_KEYS and not s["report"]:
                kind, keys = "schwach", weak
            elif weak or s["report"]:
                kind, keys = f"Uebersicht ({len(weak)} Keys)", set()
            else:
                kind, keys = "ohne Ticket", set()
            all_keys |= keys
            if keys:
                share = mins / len(keys)
                for k in keys:
                    pt = per_ticket[k]
                    pt["minutes"] += share
                    pt["blocks"].append({"session": sid, "title": s["title"], "start": b0.isoformat(),
                                         "end": b1.isoformat(), "minutes": round(share), "evidence": kind,
                                         "shared_with": sorted(keys - {k})})
                    pt["first"] = min(pt["first"], b0) if pt["first"] else b0
                    pt["last"] = max(pt["last"], b1) if pt["last"] else b1
            else:
                other_blocks.append({"session": sid, "title": s["title"], "kind": kind, "start": b0.isoformat(),
                                     "end": b1.isoformat(), "minutes": round(mins),
                                     "keys_seen": sorted(weak)[:12]})
        session_rows.append({"session": sid, "title": s["title"], "cwd": s["cwd"], "automated": s["automated"],
                             "report": s["report"], "start": min(times).isoformat(), "end": max(times).isoformat(),
                             "active_minutes": round(total), "blocks": len(blocks), "keys": sorted(all_keys)})

    out = {
        "range": {"from": a.d_from, "to": a.d_to, "gap_minutes": a.gap},
        "tickets": [
            {"key": k, "minutes": round(v["minutes"]), "first": v["first"].isoformat(), "last": v["last"].isoformat(),
             "blocks": sorted(v["blocks"], key=lambda b: b["start"])}
            for k, v in sorted(per_ticket.items(), key=lambda kv: -kv[1]["minutes"])
        ],
        "sessions": sorted(session_rows, key=lambda r: r["start"]),
        "other_blocks": sorted(other_blocks, key=lambda r: r["start"]),
    }
    if a.json_out:
        with open(winpath(a.json_out), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Zeitraum {a.d_from}..{a.d_to} | Block-Luecke {a.gap} min | Sitzungen: {len(session_rows)}")
    print("\n== Tickets (aktive Minuten in Claude-Code-Sitzungen) ==")
    for t in out["tickets"]:
        ev = "stark" if any(b["evidence"] == "stark" for b in t["blocks"]) else "schwach"
        f0, f1 = datetime.fromisoformat(t["first"]), datetime.fromisoformat(t["last"])
        print(f"{t['key']:<11}{t['minutes']:>5} min  {fmt(f0)} .. {fmt(f1)}  Bloecke: {len(t['blocks'])}  Beleg: {ev}")
    print("\n== Sitzungen ==")
    for r in out["sessions"]:
        tag = "AUTO " if r["automated"] else ("BERICHT " if r["report"] else "")
        print(f"{fmt(datetime.fromisoformat(r['start']))}..{r['end'][11:16]}  {r['active_minutes']:>4} min  {tag}{r['title'][:50]:<50} {','.join(r['keys'])[:40]}")
    print("\n== Bloecke ohne Ticketzuordnung ==")
    for u in out["other_blocks"]:
        print(f"{fmt(datetime.fromisoformat(u['start']))}..{u['end'][11:16]}  {u['minutes']:>4} min  [{u['kind']}] {u['title'][:55]}")


if __name__ == "__main__":
    main()
