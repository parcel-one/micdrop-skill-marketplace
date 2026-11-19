# Datenquellen und Abfragen

Toolnamen tragen je nach Umgebung einen Server-Präfix (`mcp__<id>__searchJiraIssuesUsingJql`);
nach Funktionsnamen auswählen. `VON`/`BIS` sind die Grenzdaten des Zeitraums, `BIS+1` der Folgetag
(Jira-Datumsvergleiche sind exklusiv am Tagesende).

## Jira (Atlassian-Connector)

Immer `cloudId: d59629e7-f457-47c3-b46a-566d3d2d4c68`.

### A – Welche Tickets hat Albert angefasst?

```text
searchJiraIssuesUsingJql
  jql: issuekey in updatedBy("712020:1225c02b-4ea5-4465-b819-2d7c603272eb", "VON", "BIS") ORDER BY updated DESC
  fields: ["summary"]
  maxResults: 100
```

`updatedBy()` erfasst Feldänderungen **und** Kommentare. Das Enddatum zählt als **ganzer Tag**
(geprüft am 17.11.2026: `updatedBy(…, "2026-11-12", "2026-11-13")` lieferte ein Ticket, dessen
einzige Aktion ein Kommentar am 13.11. 15:40 war) – also `BIS`, nicht `BIS+1`. Tickets ohne Eingabe
im Zeitraum ignoriert das Skript ohnehin. Ergebnis ist klein (nur Keys und Titel). Mehr als 100
Treffer: Zeitraum teilen. Bei einem einzelnen Tag A und B in einem Aufruf zusammenlegen (Felder von B
direkt mitgeben).

### B – Zeitpunkte der Eingaben, vorhandene Worklogs

```text
searchJiraIssuesUsingJql
  jql: key in (KEY1, KEY2, …) ORDER BY updated DESC
  fields: ["summary", "status", "created", "reporter", "comment", "worklog"]
  responseContentFormat: "markdown"
  maxResults: 100
```

Die Antwort überschreitet fast immer die Tool-Grenze und wird automatisch als Datei unter
`…/<session>/tool-results/mcp-…-searchJiraIssuesUsingJql-<zeit>.txt` gespeichert – genau diese Datei
bekommt `micdrop_vorschlag.py --jira`. Kommt die Antwort ausnahmsweise inline zurück, die Eingaben
von Albert (Kommentare mit `created`, `reporter`+`created`, Worklogs mit `started`/`timeSpent`)
kompakt nach `extra.json` übertragen (Format unten) statt das JSON abzutippen.

Hinweis des Skripts „nur n von m Kommentaren geladen“: das Ticket einzeln nachladen:

```text
getJiraIssue  issueIdOrKey: KEY  fields: ["summary","status","comment"]  responseContentFormat: "markdown"
```

### C – Statuswechsel (Zeitpunkte)

```text
searchJiraIssuesUsingJql
  jql: (status CHANGED BY currentUser() DURING ("VON", "BIS+1") OR assignee CHANGED BY currentUser() DURING ("VON", "BIS+1")) ORDER BY updated DESC
  fields: ["summary"]
```

Für jedes Ticket dieser Liste, das in B **keinen** Kommentar von Albert im Zeitraum hat (max. 10,
sonst die zuletzt aktualisierten): 

```text
getJiraIssue  issueIdOrKey: KEY  fields: ["summary","status"]  expand: "changelog"
```

Aus `changelog.histories[]` nur Einträge mit `author.accountId` = Albert und `created` im Zeitraum;
Feld `status` → `kind: "Status"`, `assignee` → `"Zuweisung"`. Nach `extra.json` übertragen.
Massen-Verschiebungen (viele Tickets im Minutentakt, z. B. TECH-657…674 am 16.11.) sind
Sammel-Pflege – das Skript erkennt sie an der Dichte, trotzdem alle übertragen.

### Buchen

```text
addWorklogToJiraIssue
  issueIdOrKey: KEY
  timeSpent: "45m" | "1h 30m"
  started: "2026-11-16T08:00:00.000+0100"
  commentBody: "MicDrop: Kommentar 08:25 und 12:16"
```

Neues Ticket: `createJiraIssue` (Projekt nach team-and-routing.md, Albert zuweisen).
Status: `getTransitionsForJiraIssue` → `transitionJiraIssue`.

### Ticket für Termine

```text
jql: project = TECH AND assignee = currentUser() AND statusCategory != Done
     AND (summary ~ "Daily" OR summary ~ "Meeting" OR summary ~ "Abstimmung" OR summary ~ "Besprechung")
```

Treffer als Pille im Formular anbieten; keine Treffer: nur „nicht buchen“ und „Andere“.

## Claude-Code-Transkripte (nur auf Alberts PC)

```bash
python <skill>/scripts/claude_sessions_time.py --from VON --to BIS --json <scratch>/sessions.json
```

Liest `~/.claude/projects/*/*.jsonl`. Nur Nutzer-/Assistententext und Jira-Tool-Parameter werden
nach Ticket-Keys durchsucht, nie Tool-Ergebnisse (die listen fremde Tickets). Sitzungen aus
geplanten Aufgaben (Ticket-Radar, Wissensindex) zählen nicht als Arbeitszeit; Berichts-Sitzungen
(MicDrop, Wochenstatus) nur mit stark belegten Keys. Blöcke mit mehr als 3 nur im Assistententext
genannten Keys gelten als Übersicht und bleiben unzugeordnet.

Fehlt Python oder der Ordner: Quelle „Claude-Code: nicht verfügbar“ in der Abschlussausgabe nennen.

## Outlook-Kalender

```text
outlook_calendar_search
  query: "*"   afterDateTime: "VON T00:00:00"   beforeDateTime: "BIS+1 T00:00:00"
  order: "oldest"   limit: 25   (weiter mit offset, solange nextOffset kommt)
```

Nach `meetings.json`: `[{"start": "<start.dateTime>", "end": "<end.dateTime>", "subject": "<subject>"}]`.
Zeiten ohne Zone gelten dem Skript als UTC (Graph liefert `timeZone: "UTC"`). Auslassen:
`isCancelled`, `isAllDay`, `showAs: "free"`. Steht ein Ticket-Key im Betreff, zusätzlich `"key"` setzen.

## Teams und Mail (gesendet von Albert)

```text
chat_message_search   query: "*"  sender: "alwag@parcel.one"  afterDateTime: "VON"  beforeDateTime: "BIS"  limit: 25
outlook_email_search  folderName: "Sent Items"  afterDateTime: "VON"  beforeDateTime: "BIS+1"  limit: 25
```

(`beforeDateTime` bei Teams schließt den ganzen Tag ein.) Nach `extra.json`, nur Zeitpunkt und
Kurzlabel, ohne Inhalte:

```json
[
  {"time": "2026-11-16T10:16:37Z", "label": "Teams an Daniel: Beta-Version"},
  {"time": "2026-11-16T09:31:39Z", "label": "Mail an D. Müller: Sandbox-Zugang", "key": "TECH-648"},
  {"time": "2026-11-16T09:11:06+01:00", "key": "TECH-630", "kind": "Status", "label": "To Do -> Warte auf Antwort"}
]
```

Einträge mit `key` sind Jira-Eingaben auf dieses Ticket (zählen Zeit), Einträge ohne `key` sind reine
Zeitmarken. Mehr als 25 Teams-Nachrichten am Tag: nicht weiterblättern, die ersten reichen als Marken.

## Nicht verfügbar

- ChatGPT-Verläufe: kein Zugriff. Recherchezeit dort ist ein Eingabefeld im Formular.
- claude.ai-Chats (Web/Desktop, nicht Code): nicht lokal gespeichert, kein Connector.
- Git/GitHub: nicht Teil des MicDrop.
