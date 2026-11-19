# micdrop-skill-marketplace

Claude-Code-Plugin-Marketplace von PARCEL.ONE Technology. Enthält derzeit ein Plugin:

| Plugin | Version | Zweck |
|---|---|---|
| `daily-micdrop` | 2.0.0 | Feierabend-Buchung: Zeitspanne nennen, der Skill sammelt die Arbeitsspuren selbst, schätzt Minuten je Ticket und bucht Worklogs in Jira |

## Installation in Claude Code

```text
/plugin marketplace add parcel-one/micdrop-skill-marketplace
/plugin install daily-micdrop@micdrop-skill-marketplace
```

Danach steht `/daily-micdrop` zur Verfügung, zum Beispiel:

```text
/daily-micdrop heute
/daily-micdrop gestern und heute
/daily-micdrop 13.–15.11.
```

Alternative ohne Claude Code: den Ordner `plugins/daily-micdrop/skills/daily-micdrop` als Zip in
claude.ai hochladen (Einstellungen → Fähigkeiten → Skills).

## Voraussetzungen

- Atlassian-Connector (Jira) mit Schreibrecht auf Worklogs.
- Microsoft-365-Connector (Outlook-Kalender, Teams, Mail) – optional, liefert Zeitmarken.
- Python 3 auf dem eigenen Rechner für die beiden Skripte (nur in Claude Code; ohne Dateisystem
  rechnet der Skill nach denselben Regeln von Hand).

## Aufbau

```text
.claude-plugin/marketplace.json          Marketplace-Manifest
plugins/daily-micdrop/
  .claude-plugin/plugin.json             Plugin-Manifest
  skills/daily-micdrop/
    SKILL.md                             Ablauf, Regeln, Rückfragen
    references/datenquellen.md           Jira-JQL, Kalender-, Teams- und Mail-Abfragen
    references/formular.md               Formular mit Eingabefeldern, Antwortformat
    references/team-and-routing.md       Projektwahl TECH/SHIP, Teamrollen
    scripts/claude_sessions_time.py      aktive Minuten je Ticket aus Claude-Code-Transkripten
    scripts/micdrop_vorschlag.py         Vorschlagsrechnung „vom Öffnen bis Eingabe“, Plausibilität
```

## Anpassung für andere Mitarbeiter

`SKILL.md` und `references/datenquellen.md` enthalten unter „Feste Werte“ die Jira-cloudId und die
Atlassian-accountId des Nutzers. Für einen anderen Mitarbeiter die accountId (Tool
`atlassianUserInfo`) und die Mailadresse austauschen; die Routingregeln in
`team-and-routing.md` gelten für das ganze Team.

## Versionierung

Änderungen am Skill: Version in `plugins/daily-micdrop/.claude-plugin/plugin.json` und in
`.claude-plugin/marketplace.json` anheben, dann committen. Claude Code zieht Updates mit
`/plugin marketplace update micdrop-skill-marketplace`.
