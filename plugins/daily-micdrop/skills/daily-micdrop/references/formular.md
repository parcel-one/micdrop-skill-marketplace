# Formular (Rückfrage in einem Schritt)

Werkzeug: `show_widget` (Modul „elicitation“ des Visualisierungs-Servers). Vorher einmal
`read_me` mit `modules: ["elicitation"]` laden, falls in dieser Sitzung noch nicht geschehen.
Das Formular enthält **nur** das Formular; Erklärungen stehen im Chattext davor (zwei Sätze:
Zeitraum, Quellen, was fehlt).

## Aufbau

```html
<form class="elicit">
  <div class="elicit-header">
    <svg viewBox="0 0 20 20" fill="currentColor"><path d="M11.586 2a1.5 1.5 0 0 1 1.06.44l2.914 2.914a1.5 1.5 0 0 1 .44 1.06V16.5a1.5 1.5 0 0 1-1.5 1.5h-9a1.5 1.5 0 0 1-1.492-1.347L4 16.5v-13A1.5 1.5 0 0 1 5.5 2zM5.5 3a.5.5 0 0 0-.5.5v13a.5.5 0 0 0 .5.5h9a.5.5 0 0 0 .5-.5V7h-2.5A1.5 1.5 0 0 1 11 5.5V3zm7.04 10.304a.5.5 0 0 1 .92.392c-.295.69-.871 1.304-1.66 1.304-.487 0-.892-.234-1.2-.574-.309.34-.713.574-1.2.574-.486 0-.892-.233-1.2-.574-.31.34-.714.574-1.2.574a.5.5 0 0 1 0-1c.212 0 .52-.18.74-.696l.034-.067a.5.5 0 0 1 .886.067c.221.516.528.696.74.696.213 0 .52-.18.74-.696l.035-.067a.5.5 0 0 1 .885.067c.22.516.527.696.74.696s.519-.18.74-.696m0-4a.5.5 0 0 1 .92.392c-.295.69-.871 1.304-1.66 1.304-.487 0-.892-.234-1.2-.574-.309.34-.713.574-1.2.574-.486 0-.892-.233-1.2-.574-.31.34-.714.574-1.2.574a.5.5 0 0 1 0-1c.212 0 .52-.18.74-.696l.034-.067a.5.5 0 0 1 .886.067c.221.516.528.696.74.696.213 0 .52-.18.74-.696l.035-.067a.5.5 0 0 1 .885.067c.22.516.527.696.74.696s.519-.18.74-.696M12 5.5a.5.5 0 0 0 .5.5h2.293L12 3.207z"/></svg>
    <span>MicDrop-Details</span>
  </div>
  <div class="elicit-body">

    <!-- Ticket MIT Vorschlag: Vorschlag vorausgewählt -->
    <div class="elicit-group">
      <label class="elicit-question">TECH-557 · Keine Info Mail an Kunden über Neues Ticket — 16.11.: Kommentar 08:25 und 12:16, Claude-Code 2 min. Vorschlag 60 min. Wie viele Minuten?</label>
      <div class="elicit-pills" data-name="TECH-557" data-multi="false">
        <button type="button" class="elicit-pill" data-value="60" aria-pressed="true">60 (Vorschlag)</button>
        <button type="button" class="elicit-pill" data-value="15">15</button>
        <button type="button" class="elicit-pill" data-value="30">30</button>
        <button type="button" class="elicit-pill" data-value="90">90</button>
        <button type="button" class="elicit-pill" data-value="120">120</button>
        <button type="button" class="elicit-pill" data-value="0">nicht buchen</button>
        <button type="button" class="elicit-pill" data-value="Andere" data-other>Andere</button>
      </div>
      <input type="text" class="elicit-other" data-for="TECH-557" placeholder="Minuten" hidden>
    </div>

    <!-- Ticket mit Rückfrage: die Frage steht im Label, der gekappte Vorschlag ist NICHT vorausgewählt -->
    <div class="elicit-group">
      <label class="elicit-question">TECH-457 · Automatischer Mindestwert … — 16.11. 11:00 Kommentar; davor 155 min ohne andere Spur. War das alles TECH-457? Vorschlag höchstens 120 min.</label>
      <div class="elicit-pills" data-name="TECH-457" data-multi="false">
        <button type="button" class="elicit-pill" data-value="120">120 (Vorschlag, gekappt)</button>
        <button type="button" class="elicit-pill" data-value="155">155 (ganze Lücke)</button>
        <button type="button" class="elicit-pill" data-value="30">30</button>
        <button type="button" class="elicit-pill" data-value="60">60</button>
        <button type="button" class="elicit-pill" data-value="0">nicht buchen</button>
        <button type="button" class="elicit-pill" data-value="Andere" data-other>Andere</button>
      </div>
      <input type="text" class="elicit-other" data-for="TECH-457" placeholder="Minuten" hidden>
    </div>

    <!-- Ticket OHNE Zeitangabe: nichts vorausgewählt = Eingabefeld -->
    <div class="elicit-group">
      <label class="elicit-question">TECH-648 · API-Key für den KD 40636 — 13.11. 15:40 Kommentar, sonst keine Spur. Wie viele Minuten?</label>
      <div class="elicit-pills" data-name="TECH-648" data-multi="false">
        <button type="button" class="elicit-pill" data-value="15">15</button>
        <button type="button" class="elicit-pill" data-value="30">30</button>
        <button type="button" class="elicit-pill" data-value="60">60</button>
        <button type="button" class="elicit-pill" data-value="0">nicht buchen</button>
        <button type="button" class="elicit-pill" data-value="Andere" data-other>Andere</button>
      </div>
      <input type="text" class="elicit-other" data-for="TECH-648" placeholder="Minuten" hidden>
    </div>

    <!-- Sammel-Pflege: eine Gruppe für alle -->
    <div class="elicit-group">
      <label class="elicit-question">Sammel-Pflege 16.11. 10:11–10:20: 18 Tickets (TECH-657 … TECH-674) auf „Warten auf Zeitslot“ gesetzt. Zusammen buchen?</label>
      <div class="elicit-pills" data-name="Sammelpflege_16_11" data-multi="false">
        <button type="button" class="elicit-pill" data-value="nicht buchen" aria-pressed="true">nicht buchen</button>
        <button type="button" class="elicit-pill" data-value="15 auf TECH-657">15 min auf TECH-657</button>
        <button type="button" class="elicit-pill" data-value="Andere" data-other>Andere</button>
      </div>
      <input type="text" class="elicit-other" data-for="Sammelpflege_16_11" placeholder="Minuten und Ticket" hidden>
    </div>

    <!-- Termin -->
    <div class="elicit-group">
      <label class="elicit-question">Tech Daily 16.11. 09:30–10:30 (60 min) — auf welches Ticket?</label>
      <div class="elicit-pills" data-name="Termin_Tech_Daily_16_11" data-multi="false">
        <button type="button" class="elicit-pill" data-value="nicht buchen" aria-pressed="true">nicht buchen</button>
        <button type="button" class="elicit-pill" data-value="TECH-123">TECH-123 Daily</button>
        <button type="button" class="elicit-pill" data-value="Andere" data-other>Andere</button>
      </div>
      <input type="text" class="elicit-other" data-for="Termin_Tech_Daily_16_11" placeholder="Ticket-Key" hidden>
    </div>

    <!-- Tagesfrage (nur wenn das Skript sie setzt) -->
    <div class="elicit-group">
      <label class="elicit-question">13.11. hat nur 20 min Spuren. Gab es etwas ohne Ticket – Support, Abstimmungen, Recherche in ChatGPT oder claude.ai? (Thema und Minuten)</label>
      <textarea class="elicit-textarea" data-name="Ergaenzung_13_11" placeholder="z. B. Recherche Heidler-Schnittstelle 90 min, TECH-424"></textarea>
    </div>

    <div class="elicit-group">
      <label class="elicit-question">Fehlt noch etwas?</label>
      <textarea class="elicit-textarea" data-name="Ergaenzung" placeholder="Ticket oder Thema + Minuten"></textarea>
    </div>

  </div>
  <div class="elicit-footer">
    <button type="button" class="elicit-skip">Abbrechen</button>
    <button type="button" class="elicit-submit">Buchen</button>
  </div>
</form>
```

Regeln für das Befüllen:

- `data-name` = Ticket-Key (Bindestrich bleibt); für Termine, Sammel-Pflege und Tagesfragen ein
  sprechender Name mit Unterstrichen.
- Pillenwerte sind nackte Minuten (`"60"`), damit die Antwort eindeutig ist. Vorschlag immer als
  erste Pille; nur vorausgewählt (`aria-pressed="true"`), wenn keine Rückfrage am Ticket hängt.
- Mehrtägig und Ticket an mehreren Tagen: je Tag eine Gruppe, `data-name="TECH-557_16_11"`.
- Höchstens 20 Ticket-Gruppen. Mehr: die kleinsten (unter 10 min Vorschlag) als eine Textzeile
  im Chat vorab zusammenfassen und nur bei Widerspruch einzeln anbieten.
- Keine Ticket-Inhalte in die Labels, nur Key, Titel, Uhrzeiten, Quelle.

## Antwort lesen

Die Antwort kommt als eine Zeile:

```text
MicDrop-Details — TECH-557: 60 · TECH-457: Andere (45) · TECH-648: 15 · Sammelpflege 16 11: nicht buchen · Termin Tech Daily 16 11: TECH-123 · Ergaenzung: TECH-424 Recherche 90
```

- Zahl → Minuten; `0` oder „nicht buchen“ → auslassen.
- „Andere (…)“ → Zahl aus der Klammer; steht dort ein Ticket-Key (bei Terminen) → auf dieses Ticket.
- Freitext: Key + Minuten herauslesen; ohne Key → Ticket suchen/anlegen (team-and-routing.md).
- `(Skipped the form …)` → nichts buchen, Vorschlagsliste als Text ausgeben und auf Antwort warten.

## Ohne Formular-Werkzeug

Dieselben Gruppen als Text, eine Zeile je Ticket:

```text
MicDrop 13.–16.11. — bitte Minuten eintragen (Vorschlag in Klammern, leer = keine Spur):
TECH-557  Keine Info Mail an Kunden … (60, Kommentar 08:25 + 12:16)      → ___
TECH-457  Automatischer Mindestwert … (max 120, 155 min Lücke – alles TECH-457?) → ___
TECH-648  API-Key für den KD 40636 (–, Kommentar 13.11. 15:40)            → ___
Tech Daily 16.11. 60 min → Ticket oder „nicht buchen“
Fehlt etwas? Ticket/Thema + Minuten
```

Albert antwortet in einer Nachricht; Zeilen ohne Eintrag werden nicht gebucht.
