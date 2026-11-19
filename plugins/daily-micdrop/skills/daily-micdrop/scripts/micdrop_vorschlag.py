#!/usr/bin/env python3
"""MicDrop-Vorschlag: Minuten je Ticket aus Jira-Spuren, Claude-Code-Sitzungen und Terminen schaetzen.

Aufruf (alle Pfade beliebig, Globs erlaubt):
  python micdrop_vorschlag.py --from 2026-11-13 --to 2026-11-16 --account 712020:... \
      --jira "<tool-results>/*searchJiraIssuesUsingJql*.txt" "<tool-results>/*getJiraIssue*.txt" \
      [--sessions sessions.json] [--meetings meetings.json] [--extra extra.json] [--json vorschlag.json]

Eingaben:
  --jira      gespeicherte Antworten des Atlassian-Connectors (Suche oder Einzelvorgang, JSON mit issues.nodes[]).
              Genutzt werden: created/reporter, comment.comments[], worklog.worklogs[], changelog.histories[].
  --sessions  Ausgabe von claude_sessions_time.py (--json).
  --meetings  JSON-Liste [{"start": ISO, "end": ISO, "subject": "..."}]; Zeiten ohne Zone gelten als UTC.
  --extra     JSON-Liste [{"time": ISO, "label": "Teams an Manuel: ..."}] (gesendete Teams-Nachrichten, Mails).

Schaetzlogik ("vom Eroeffnen bis Eingabe"):
  * Jede Jira-Eingabe von Albert (Kommentar, Statuswechsel, Ticket angelegt, Zuweisung) ist ein Zeitpunkt.
  * Die Zeit seit der vorherigen Spur (andere Jira-Eingabe, Ende einer Claude-Sitzung, Ende eines Termins,
    Teams/Mail) wird dem Ticket der Eingabe zugerechnet - bis zur Kappung CAP_MIN. Davor liegt bei der
    ersten Eingabe des Tages fruehestens DAY_START Uhr.
  * Claude-Code-Bloecke zaehlen als aktive Zeit direkt auf ihr Ticket.
  * Luecken > LONG_GAP vor einer Eingabe, mehr als MAX_TICKET_DAY je Ticket und Tag, Tagessummen ueber
    MAX_DAY oder unter MIN_DAY_WEEKDAY (Werktag) sowie Sammel-Pflege (BURST_N Tickets in BURST_WIN Minuten)
    sind Plausibilitaetsfragen - sie werden markiert, nicht still geschluckt.
  * Vorhandene Worklogs von Albert im Zeitraum werden je Ticket und Tag ausgewiesen (Doppelbuchung).
"""
import argparse
import glob
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

CAP_MIN = 120
LONG_GAP = 120
MAX_TICKET_DAY = 180
MAX_DAY = 600
MIN_DAY_WEEKDAY = 180
BURST_N, BURST_WIN = 4, 10
DAY_START = 7
FIRST_OF_DAY_MAX = 60
ROUND_TO = 15  # Vorschlaege auf volle Viertelstunden aufrunden
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

try:
    from zoneinfo import ZoneInfo
    BERLIN = ZoneInfo("Europe/Berlin")
except Exception:  # Windows ohne tzdata
    BERLIN = None


def berlin(dt):
    if BERLIN is not None:
        return dt.astimezone(BERLIN)
    y = dt.year

    def last_sunday(m):
        d = date(y, m + 1, 1) - timedelta(days=1)
        return d - timedelta(days=(d.weekday() + 1) % 7)

    u = dt.astimezone(timezone.utc)
    s = datetime.combine(last_sunday(3), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=1)
    e = datetime.combine(last_sunday(10), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=1)
    return u.astimezone(timezone(timedelta(hours=2 if s <= u < e else 1)))


def parse_dt(s, default_tz=timezone.utc):
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    s = re.sub(r"(\.\d{6})\d+", r"\1", s)           # 7 Nachkommastellen (Graph) -> 6
    s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)  # +0100 -> +01:00
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_tz)
    return berlin(dt)


def winpath(p):
    """'/c/Users/...' (Git-Bash) -> 'C:/Users/...' fuer Windows-Python; andere Pfade unveraendert."""
    m = re.match(r"^/([a-zA-Z])/(.*)$", p or "")
    return f"{m.group(1).upper()}:/{m.group(2)}" if m else p


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def hm(dt):
    return dt.strftime("%H:%M")


def dm(dt):
    return dt.strftime("%d.%m.")


def round_up(m):
    return int(-(-m // ROUND_TO) * ROUND_TO) if m > 0 else 0


class Collector:
    def __init__(self, d_from, d_to, account):
        self.d_from, self.d_to, self.me = d_from, d_to, account
        self.tickets = {}                 # key -> {summary, status}
        self.points = []                  # Jira-Eingaben: dict(t, key, kind, text)
        self.ranges = []                  # dict(t, end, key|None, kind, label, minutes)
        self.marks = []                   # sonstige Spuren: dict(t, label)
        self.worklogs = defaultdict(list) # key -> [{day, minutes, started}]
        self.notes = []

    def in_range(self, dt):
        return dt is not None and self.d_from <= dt.date() <= self.d_to

    # ---------- Jira ----------
    def add_jira_file(self, path):
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self.notes.append(f"{path}: kein JSON, uebersprungen")
            return
        nodes = []
        if isinstance(data, dict):
            nodes = ((data.get("issues") or {}).get("nodes")) or data.get("issues") or []
            if isinstance(nodes, dict):
                nodes = [nodes]
            if not nodes and data.get("key"):
                nodes = [data]
        for n in nodes:
            self.add_issue(n)

    def add_issue(self, n):
        key = n.get("key")
        if not key:
            return
        f = n.get("fields") or {}
        t = self.tickets.setdefault(key, {"summary": "", "status": ""})
        if f.get("summary"):
            t["summary"] = f["summary"]
        if isinstance(f.get("status"), dict):
            t["status"] = f["status"].get("name", "")
        created = parse_dt(f.get("created"))
        if (f.get("reporter") or {}).get("accountId") == self.me and self.in_range(created):
            self.points.append({"t": created, "key": key, "kind": "angelegt", "text": t["summary"][:60]})
        cm = f.get("comment") or {}
        comments = cm.get("comments") or []
        if cm.get("total") and cm["total"] > len(comments):
            self.notes.append(f"{key}: nur {len(comments)} von {cm['total']} Kommentaren geladen - Vorgang einzeln nachladen")
        for c in comments:
            if (c.get("author") or {}).get("accountId") != self.me:
                continue
            ct = parse_dt(c.get("created"))
            if self.in_range(ct):
                self.points.append({"t": ct, "key": key, "kind": "Kommentar", "text": strip_html(c.get("body"))[:70]})
        wl = f.get("worklog") or {}
        for w in wl.get("worklogs") or []:
            if (w.get("author") or {}).get("accountId") != self.me:
                continue
            st = parse_dt(w.get("started")) or parse_dt(w.get("created"))
            if self.in_range(st):
                self.worklogs[key].append({"day": st.date().isoformat(), "minutes": int((w.get("timeSpentSeconds") or 0) // 60),
                                           "started": st.isoformat(), "comment": strip_html(str(w.get("comment") or ""))[:60]})
        for h in (n.get("changelog") or {}).get("histories") or []:
            if (h.get("author") or {}).get("accountId") != self.me:
                continue
            ht = parse_dt(h.get("created"))
            if not self.in_range(ht):
                continue
            for it in h.get("items") or []:
                field = (it.get("field") or "").lower()
                if field == "status":
                    self.points.append({"t": ht, "key": key, "kind": "Status", "text": f"{it.get('fromString')} -> {it.get('toString')}"})
                elif field == "assignee":
                    self.points.append({"t": ht, "key": key, "kind": "Zuweisung", "text": f"-> {it.get('toString')}"})
                elif field in ("comment",):
                    continue  # Kommentare kommen aus fields.comment
                else:
                    self.points.append({"t": ht, "key": key, "kind": "Feld", "text": f"{it.get('field')}: {str(it.get('toString'))[:40]}"})

    # ---------- Claude Code ----------
    def add_sessions(self, path):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        for t in d.get("tickets") or []:
            for b in t.get("blocks") or []:
                if b.get("minutes", 0) < 2:
                    continue  # Streifschuss, kein Arbeitsblock
                s, e = parse_dt(b["start"]), parse_dt(b["end"])
                if self.in_range(s):
                    self.ranges.append({"t": s, "end": e, "key": t["key"], "kind": "Claude-Code", "minutes": b["minutes"],
                                        "label": b.get("title", "")[:50]})
                    self.tickets.setdefault(t["key"], {"summary": "", "status": ""})
        for b in d.get("other_blocks") or []:
            if b.get("kind") == "automatisch":
                continue
            s, e = parse_dt(b["start"]), parse_dt(b["end"])
            if self.in_range(s):
                self.ranges.append({"t": s, "end": e, "key": None, "kind": f"Claude-Code {b.get('kind')}", "minutes": b["minutes"],
                                    "label": b.get("title", "")[:50]})

    # ---------- Termine / sonstige Spuren ----------
    def add_meetings(self, path):
        with open(path, encoding="utf-8") as f:
            for m in json.load(f):
                s, e = parse_dt(m.get("start")), parse_dt(m.get("end"))
                if s and e and self.in_range(s):
                    self.ranges.append({"t": s, "end": e, "key": m.get("key"), "kind": "Termin", "label": m.get("subject", "")[:60],
                                        "minutes": int((e - s).total_seconds() // 60)})

    def add_extra(self, path):
        """Kompakte Spuren, die Claude selbst notiert hat.
        Mit "key": eine Jira-Eingabe auf dieses Ticket (kind z. B. "Status", "Kommentar", "angelegt").
        Ohne "key": sonstige Spur (Teams, Mail), die nur die Zeitachse markiert."""
        with open(path, encoding="utf-8") as f:
            for x in json.load(f):
                t = parse_dt(x.get("time"))
                if not self.in_range(t):
                    continue
                if x.get("key"):
                    self.tickets.setdefault(x["key"], {"summary": x.get("summary", ""), "status": ""})
                    self.points.append({"t": t, "key": x["key"], "kind": x.get("kind", "Eingabe"), "text": x.get("label", "")[:70]})
                else:
                    self.marks.append({"t": t, "label": x.get("label", "")[:70], "key": None})

    # ---------- Rechnung ----------
    def compute(self):
        points = sorted(self.points, key=lambda p: p["t"])
        # Sammel-Pflege erkennen
        burst_ids = set()
        for i, p in enumerate(points):
            win = [q for q in points if 0 <= (q["t"] - p["t"]).total_seconds() <= BURST_WIN * 60]
            if len({q["key"] for q in win}) >= BURST_N:
                burst_ids.update(id(q) for q in win)

        # alle Spuren als Marken (Zeitpunkt oder Ende eines Bereichs)
        mark_times = [(p["t"], p["t"]) for p in points]
        mark_times += [(r["t"], r["end"]) for r in self.ranges]
        mark_times += [(m["t"], m["t"]) for m in self.marks]

        per_ticket = defaultdict(lambda: {"minutes": 0.0, "evidence": [], "flags": set(), "first": None, "last": None, "days": defaultdict(float)})
        day_flags = defaultdict(set)

        def touch(key, t0, t1):
            pt = per_ticket[key]
            pt["first"] = min(pt["first"], t0) if pt["first"] else t0
            pt["last"] = max(pt["last"], t1) if pt["last"] else t1

        for p in points:
            key, t = p["key"], p["t"]
            day_start = t.replace(hour=DAY_START, minute=0, second=0, microsecond=0)
            prev = None
            for (a, b) in mark_times:
                if b < t and b.date() == t.date() and (prev is None or b > prev):
                    prev = b
            pt = per_ticket[key]
            if id(p) in burst_ids:
                mins = 0
                pt["flags"].add("Sammel-Pflege: mehrere Tickets innerhalb weniger Minuten - nicht gerechnet; zusammen als eine Position buchen oder auslassen")
                note = "Sammel-Pflege"
            elif prev is None:
                gap = (t - day_start).total_seconds() / 60
                mins = max(0, min(gap, FIRST_OF_DAY_MAX))
                note = f"erste Spur des Tages, Beginn unbekannt (max. {FIRST_OF_DAY_MAX} min angesetzt)"
                pt["flags"].add(note)
            else:
                gap = (t - prev).total_seconds() / 60
                if gap > LONG_GAP:
                    mins = CAP_MIN
                    pt["flags"].add(f"{dm(t)} {hm(t)}: {int(gap)} min ohne andere Spur davor - war das alles {key}? (gekappt auf {CAP_MIN} min)")
                    note = f"Luecke {int(gap)} min, gekappt"
                else:
                    mins = gap
                    note = f"{int(gap)} min seit {hm(prev)}"
            pt["minutes"] += mins
            pt["days"][t.date().isoformat()] += mins
            pt["evidence"].append(f"{dm(t)} {hm(t)} {p['kind']}: {p['text']} [{note}]")
            touch(key, t - timedelta(minutes=mins), t)

        for r in self.ranges:
            if r["key"] and r["kind"].startswith("Claude-Code"):
                pt = per_ticket[r["key"]]
                pt["minutes"] += r["minutes"]
                pt["days"][r["t"].date().isoformat()] += r["minutes"]
                pt["evidence"].append(f"{dm(r['t'])} {hm(r['t'])}-{hm(r['end'])} Claude-Code ({r['label']}): {r['minutes']} min")
                touch(r["key"], r["t"], r["end"])

        # Plausibilitaet je Ticket/Tag und je Tag
        day_totals = defaultdict(float)
        for key, pt in per_ticket.items():
            for d, m in pt["days"].items():
                day_totals[d] += m
                if m > MAX_TICKET_DAY:
                    pt["flags"].add(f"{d}: {int(m)} min an einem Tag fuer ein Ticket - plausibel?")
        meetings = [r for r in self.ranges if r["kind"] == "Termin"]
        for r in meetings:
            day_totals[r["t"].date().isoformat()] += r["minutes"]
        for d, m in day_totals.items():
            wd = date.fromisoformat(d).weekday()
            if m > MAX_DAY:
                day_flags[d].add(f"Tagessumme {int(m)} min ueber {MAX_DAY} min")
            if wd < 5 and 0 < m < MIN_DAY_WEEKDAY:
                day_flags[d].add(f"Werktag mit nur {int(m)} min Spuren - fehlt etwas ohne Ticket (Support, Abstimmungen, Recherche in ChatGPT/claude.ai)?")

        tickets_out = []
        for key, pt in sorted(per_ticket.items(), key=lambda kv: -kv[1]["minutes"]):
            booked = self.worklogs.get(key, [])
            if round_up(pt["minutes"]) == 0 and not booked and not pt["flags"]:
                continue
            for d in pt["days"]:
                for w in booked:
                    if w["day"] == d:
                        pt["flags"].add(f"{d}: bereits {w['minutes']} min gebucht - nicht doppelt buchen")
            tickets_out.append({
                "key": key, "summary": self.tickets.get(key, {}).get("summary", ""), "status": self.tickets.get(key, {}).get("status", ""),
                "vorschlag_min": round_up(pt["minutes"]),
                "nach_tag": {d: round_up(m) for d, m in sorted(pt["days"].items())},
                "beginn": pt["first"].isoformat() if pt["first"] else None,
                "ende": pt["last"].isoformat() if pt["last"] else None,
                "belege": pt["evidence"], "fragen": sorted(pt["flags"]), "bereits_gebucht": booked,
            })
        # Tickets mit Worklog, aber ohne Spur im Zeitraum
        for key, wl in self.worklogs.items():
            if key not in per_ticket:
                tickets_out.append({"key": key, "summary": self.tickets.get(key, {}).get("summary", ""), "status": "",
                                    "vorschlag_min": 0, "nach_tag": {}, "beginn": None, "ende": None, "belege": [],
                                    "fragen": ["nur Worklog vorhanden, keine neue Spur"], "bereits_gebucht": wl})
        other = [{"start": r["t"].isoformat(), "end": r["end"].isoformat(), "minutes": r["minutes"], "kind": r["kind"], "label": r["label"]}
                 for r in sorted(self.ranges, key=lambda r: r["t"]) if not (r["key"] and r["kind"].startswith("Claude-Code"))]
        return {
            "range": {"from": self.d_from.isoformat(), "to": self.d_to.isoformat()},
            "tage": [{"datum": d, "wochentag": WOCHENTAGE[date.fromisoformat(d).weekday()], "spuren_min": round_up(m),
                      "fragen": sorted(day_flags[d])} for d, m in sorted(day_totals.items())],
            "tickets": tickets_out,
            "ohne_ticket": other,
            "spuren_sonstige": [{"time": m["t"].isoformat(), "label": m["label"]} for m in sorted(self.marks, key=lambda m: m["t"])],
            "hinweise": self.notes,
        }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="d_from", required=True)
    ap.add_argument("--to", dest="d_to", required=True)
    ap.add_argument("--account", required=True, help="Atlassian accountId von Albert")
    ap.add_argument("--jira", nargs="*", default=[], help="gespeicherte Jira-Antworten (Dateien oder Globs)")
    ap.add_argument("--sessions")
    ap.add_argument("--meetings")
    ap.add_argument("--extra")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()

    c = Collector(date.fromisoformat(a.d_from), date.fromisoformat(a.d_to), a.account)
    files = []
    for pat in a.jira:
        pat = winpath(pat)
        files += glob.glob(pat) or [pat]
    for p in files:
        c.add_jira_file(p)
    if a.sessions:
        c.add_sessions(winpath(a.sessions))
    if a.meetings:
        c.add_meetings(winpath(a.meetings))
    if a.extra:
        c.add_extra(winpath(a.extra))
    out = c.compute()
    if a.json_out:
        with open(winpath(a.json_out), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"MicDrop-Vorschlag {a.d_from}..{a.d_to}  (Jira-Dateien: {len(files)}, Spuren: {len(c.points)} Eingaben, "
          f"{len(c.ranges)} Bloecke/Termine, {len(c.marks)} sonstige)")
    for d in out["tage"]:
        print(f"\n== {d['wochentag']} {d['datum']}  Spuren gesamt ca. {d['spuren_min']} min ==")
        for fl in d["fragen"]:
            print(f"   ? {fl}")
    print("\n== Tickets ==")
    for t in out["tickets"]:
        print(f"{t['key']:<11}{t['vorschlag_min']:>5} min  {t['summary'][:55]}")
        for e in t["belege"]:
            print(f"     - {e}")
        for q in t["fragen"]:
            print(f"     ? {q}")
        for w in t["bereits_gebucht"]:
            print(f"     = gebucht {w['day']}: {w['minutes']} min")
    print("\n== Ohne Ticket (Termine, Bloecke) ==")
    for o in out["ohne_ticket"]:
        print(f"{o['start'][5:16]}..{o['end'][11:16]}  {o['minutes']:>4} min  [{o['kind']}] {o['label']}")
    for h in out["hinweise"]:
        print("! " + h)


if __name__ == "__main__":
    main()
