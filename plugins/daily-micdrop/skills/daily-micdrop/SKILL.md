---
name: daily-micdrop
description: Feierabend-Buchung für Albert Wagner (PARCEL.ONE Technology). Albert nennt nur eine Zeitspanne („heute“, „gestern und heute“, „13.–15.11.“, „KW 46“, „Freitag“); der Skill sucht selbst zusammen, woran er gearbeitet hat (Jira-Kommentare, Statuswechsel, angelegte Tickets, Claude-Code-Sitzungen, Outlook-Termine, gesendete Teams-Nachrichten und Mails), schätzt je Ticket die Minuten vom Öffnen bis zur Eingabe, markiert Unplausibles als Rückfrage, zeigt ein Formular mit Eingabefeldern für alles ohne Zeitangabe und bucht danach die Worklogs in Jira (SHIP/TECH/F1SUP …). Immer verwenden bei „MicDrop“, „daily-micdrop“, „Zeiten buchen“, „Worklogs“, „Feierabendbericht“, „Tagesbericht“, „was habe ich heute/gestern gemacht“ – auch wenn nur ein Datum oder Zeitraum genannt wird.
---

# Daily MicDrop (Albert)

Eingabe: eine Zeitspanne. Ausgabe: gebuchte Worklogs. Dazwischen sucht der Skill die Spuren selbst
zusammen, rechnet Vorschläge aus und fragt nur dort nach, wo die Daten nicht reichen – gebündelt in
einem Formular, nicht als Kette von Rückfragen.

## Feste Werte

- Jira cloudId: `d59629e7-f457-47c3-b46a-566d3d2d4c68` (parcelone.atlassian.net)
- Albert: accountId `712020:1225c02b-4ea5-4465-b819-2d7c603272eb`, Mail `alwag@parcel.one`
- Zeitzone Europe/Berlin. Jira liefert `+0100/+0200`, Graph (Outlook/Teams) liefert UTC.
- Projekte mit eigener Arbeit: TECH (Default), SHIP, F1SUP, P1SUP; Service-Desk-Projekte nur, wenn
  Albert dort selbst kommentiert hat.
- Skripte: `scripts/claude_sessions_time.py` (Claude-Code-Transkripte) und
  `scripts/micdrop_vorschlag.py` (Vorschlagsrechnung). Beide laufen mit Python 3 ohne Zusatzpakete.
  Pfad des Skill-Ordners steht in der Skill-Meldung („Base directory for this skill“).
- Arbeitsdateien in das Scratchpad der Sitzung schreiben (`sessions.json`, `meetings.json`,
  `extra.json`, `vorschlag.json`).

## Grundhaltung

- **Spuren statt Fragen.** Erst alle Quellen lesen, dann rechnen, dann genau einmal fragen.
- **Nichts erfinden.** Eine Minute ohne Beleg ist ein Eingabefeld, kein geschätzter Wert.
- **Unplausibles wird markiert, nicht geglättet.** Die Rückfrage steht als Satz beim Ticket im
  Formular; der Vorschlag daneben ist ein Vorschlag, keine Buchung.
- **Alberts Antwort gilt.** Was er im Formular einträgt, wird ohne weitere Prüfung gebucht.
- **Keine Uhrzeit-Abfragen.** Uhrzeiten kommen aus den Spuren; wo keine da sind, gilt 09:00.

## Ablauf

### 0. Zeitspanne verstehen

Aus dem Aufruf `von`/`bis` (jeweils ein Datum, inklusiv) ableiten – nicht nachfragen:

| Albert sagt | von – bis |
|---|---|
| nichts, „heute“, „MicDrop“ | heute – heute |
| „gestern“ | gestern – gestern |
| „gestern und heute“, „seit gestern“ | gestern – heute |
| „Freitag“, „Montag“ | der letzte Wochentag mit diesem Namen (nie in der Zukunft) |
| „13.–15.11.“, „13.11. bis 15.11.“ | wie genannt; Jahr = laufendes Jahr, sonst Vorjahr |
| „diese Woche“ | Montag – heute |
| „letzte Woche“, „KW 46“ | Montag – Sonntag der Woche |

Mehr als 14 Tage: erst fragen, ob das stimmt (Jira-Abfragen werden sonst zu groß). Tage ohne jede
Spur werden am Ende als „keine Spuren“ genannt, nicht gebucht.

### 1. Spuren sammeln – alles parallel

Die Abfragen und ihre genauen Parameter stehen in [references/datenquellen.md](references/datenquellen.md).
Kurzfassung:

| Quelle | Was sie liefert | Wohin |
|---|---|---|
| Jira A: `issuekey in updatedBy(Albert, von, bis)` – `bis` zählt in Jira als ganzer Tag | alle Tickets, die Albert im Zeitraum angefasst hat (auch nur kommentiert) | Key-Liste |
| Jira B: `key in (…)` mit `comment`, `worklog`, `created`, `reporter`, `status` | Zeitpunkte seiner Kommentare, angelegte Tickets, schon gebuchte Worklogs | Datei (groß, landet automatisch in `tool-results`) |
| Jira C: `status CHANGED BY currentUser() DURING (…)` + `getJiraIssue … expand=changelog` je Ticket (max. 10) | Zeitpunkte der Statuswechsel | kompakt nach `extra.json` übertragen |
| Claude-Code-Transkripte: `claude_sessions_time.py` | aktive Minuten je Ticket, Sitzungsblöcke ohne Ticket | `sessions.json` |
| Outlook-Kalender | Termine (Dauer, Betreff) | `meetings.json` |
| Teams (gesendet von Albert), Outlook „Gesendete Elemente“ | Zeitmarken und Themen, Ticket-Keys im Betreff | `extra.json` |

Nicht lesbar und deshalb **kein Fehler**: ChatGPT-Verläufe, claude.ai-Chats (nur Claude-Code-Sitzungen
liegen lokal), Arbeit ohne Spur. Was fehlt, wird im Formular zum Eingabefeld.

Läuft der Skill ohne Dateisystem (claude.ai-Chat, keine Bash): Jira A–C, Kalender, Teams und Mail
trotzdem abfragen, Claude-Code-Quelle als „nicht verfügbar“ führen und die Rechnung aus Schritt 2 von
Hand nach denselben Regeln machen.

### 2. Vorschlag rechnen

```bash
python <skill>/scripts/micdrop_vorschlag.py --from VON --to BIS \
  --account 712020:1225c02b-4ea5-4465-b819-2d7c603272eb \
  --jira "<tool-results>/*searchJiraIssuesUsingJql*.txt" "<tool-results>/*getJiraIssue*.txt" \
  --sessions <scratch>/sessions.json --meetings <scratch>/meetings.json --extra <scratch>/extra.json \
  --json <scratch>/vorschlag.json
```

Das Skript rechnet „vom Öffnen bis zur Eingabe“:

- Jede Jira-Eingabe von Albert (Kommentar, Statuswechsel, Ticket angelegt, Zuweisung) ist ein
  Zeitpunkt. Die Zeit seit der vorherigen Spur – egal aus welcher Quelle – gehört dem Ticket dieser
  Eingabe, höchstens 120 min. Vor der ersten Spur des Tages werden höchstens 60 min angesetzt und
  als unbekannter Tagesbeginn markiert.
- Claude-Code-Blöcke (Nachrichten mit ≤ 15 min Abstand) zählen als aktive Zeit direkt auf ihr Ticket.
- Termine, Teams- und Mail-Spuren zählen auf kein Ticket, unterbrechen aber die Zeitachse.
- Ergebnis je Ticket: Minuten (auf 5 gerundet), Minuten je Tag, Beginn/Ende, Belege, Rückfragen.
- Tickets, die nur aus Claude-Code-Sitzungen stammen, haben im Ergebnis keinen Titel; den Titel aus
  der Jira-A-Liste nehmen oder kurz per `getJiraIssue` (fields `summary`) holen.
- Pfade in Git-Bash-Schreibweise (`/c/Users/…`) setzt das Skript selbst nach Windows um.

Rückfragen, die das Skript setzt und die **immer** ins Formular gehören:

| Befund | Rückfrage |
|---|---|
| > 120 min ohne andere Spur vor einer Eingabe | „11:00 Kommentar TECH-457: 155 min ohne andere Spur davor – war das alles TECH-457?“ (Vorschlag gekappt auf 120) |
| > 180 min an einem Tag für ein Ticket | „plausibel?“ |
| ≥ 4 Tickets innerhalb von 10 min | Sammel-Pflege: je 2 min vorgeschlagen, einmal fragen, ob das als „Jira-Pflege“ gebucht werden soll |
| Werktag mit < 3 h Spuren | einmal fragen, was ohne Ticket Zeit gekostet hat (Support, Abstimmungen, Recherche in ChatGPT/claude.ai) |
| Tagessumme > 10 h | „stimmt die Summe?“ |
| Worklog am selben Tag schon vorhanden | nicht erneut vorschlagen, im Formular als „bereits gebucht“ zeigen |
| Kommentare eines Tickets nur teilweise geladen | Ticket einzeln mit `getJiraIssue` nachladen, bevor gerechnet wird |

### 3. Formular zeigen – die eine Rückfrage

Vorlage und Antwortformat in [references/formular.md](references/formular.md). Regeln:

- Ein Formular für den ganzen Zeitraum, Tickets nach Vorschlag absteigend, darunter Termine und
  Blöcke ohne Ticket, zuletzt ein Freitextfeld „Fehlt etwas?“.
- Jedes Ticket bekommt Pillen mit Minuten. Gibt es einen Vorschlag, ist er vorausgewählt und als
  Vorschlag beschriftet; die Belegzeile (Uhrzeiten, Quelle) steht in der Frage. Gibt es keinen,
  ist nichts vorausgewählt – das ist das Eingabefeld, das Albert füllt. „Andere“ öffnet immer ein
  Freitextfeld für Minuten.
- Rückfragen aus Schritt 2 stehen als Satz in der Frage des Tickets, nicht in einer Extra-Runde.
- Termine: Pillen mit einem passenden offenen Ticket (Suche nach „Daily“, „Meeting“,
  „Abstimmung“ in TECH, Albert zugewiesen), „nicht buchen“ und „Andere“.
- Mehrtägig: Minuten je Ticket und Tag, wenn das Skript `nach_tag` mit mehreren Tagen liefert;
  sonst ein Feld.
- Ohne Formular-Werkzeug (`show_widget` nicht vorhanden): dieselbe Liste als Text, jede Zeile
  `KEY – Titel – Vorschlag X min (Beleg) → ___ min`, Albert antwortet in einer Nachricht.

Wenn Albert im Aufruf bereits Dauern nennt („TECH-636 15 min …“), gilt der alte Weg: diese Angaben
direkt übernehmen, Formular nur für die Tickets mit Spuren, aber ohne genannte Dauer.

### 4. Buchen

Nach der Antwort ohne weitere Bestätigung ausführen (Toolnamen in datenquellen.md):

1. Je Ticket und Tag ein Worklog: `timeSpent` aus der Antwort (`45m`, `1h 30m`), `started` mit Zone
   (`+0100`): bei einem Claude-Code-Block dessen Beginn, sonst Zeitpunkt der ersten Jira-Eingabe des
   Tages minus gebuchte Minuten; immer auf volle 15 min abgerundet, nie vor 07:00; ohne Spur 09:00.
   Zwei Positionen auf dasselbe Ticket am selben Tag (z. B. umgeleitete Analyse plus eigener
   Kommentar) zu einem Worklog zusammenfassen. Worklog-Kommentar: eine kurze Belegzeile („Kommentar 08:25 und 12:16, Claude-Code
   17 min“), keine Inhalte aus den Tickets wiederholen.
2. Minuten 0 oder „nicht buchen“: auslassen, in der Abschlussausgabe nennen.
3. Doppelbuchung: liegt am selben Tag schon ein Worklog von Albert auf dem Ticket, nicht buchen,
   sondern ausweisen.
4. Freitext „Fehlt etwas?“ mit Thema ohne Ticket: Ticket suchen oder nach
   [references/team-and-routing.md](references/team-and-routing.md) anlegen, dann buchen.
5. Status nur ändern, wenn Albert es ausdrücklich schreibt („fertig“, „in Abnahme“): Transitionen
   lesen, passende nehmen, Namen nicht erfinden.

### 5. Abschlussausgabe

```text
MicDrop gebucht (13.–16.11.2026, gesamt 9h 35m):
16.11.  TECH-557 — 1h 00m — Worklog gebucht (Beginn 08:00)
16.11.  TECH-470 — 20m — Worklog gebucht
16.11.  TECH-644 — 40m — bereits gebucht, nicht doppelt
15.11.  TECH-675 — 30m — Worklog gebucht
13.11.  keine Spuren außer TECH-648 (15m) — gebucht
Nicht gebucht: Tech Daily 16.11. (60m, „nicht buchen“), Sammel-Pflege TECH-657…674 (0m)
Quellen: Jira (31 Tickets), Claude-Code (4 Sitzungen), Kalender (2 Termine), Teams (4), Mail (2); ChatGPT nicht lesbar.
```

## Regeln, die jedes Mal gelten

- Deutsch, sachlich, Ticket-Keys und Titel im Original.
- Wochentage nie aus dem Kopf: das Skript gibt sie je Tag aus (`wochentag` in `vorschlag.json`),
  nur diese Angabe ins Formular und in die Ausgabe übernehmen.
- Jira-Antworten sind groß und landen als Datei im `tool-results`-Ordner; nie am Stück lesen,
  sondern per Skript oder Python-Einzeiler auf das Nötige eindampfen.
- Keine Inhalte aus Tickets, Mails oder Chats in Worklog-Kommentare übernehmen – nur Zeitbelege.
- Keine Mails, Teams-Nachrichten oder Jira-Kommentare schreiben. Der Skill schreibt ausschließlich
  Worklogs, bei Bedarf ein neues Ticket und auf Wunsch eine Statusänderung.
- Wochenend- und Feiertagsarbeit normal buchen, aber in der Abschlussausgabe nennen.
