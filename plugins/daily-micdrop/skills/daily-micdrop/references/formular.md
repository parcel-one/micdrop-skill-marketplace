# Formular (Rückfrage in einem Schritt, mit laufender Tagessumme)

Werkzeug: `show_widget` (HTML-Widget). Vorher einmal `read_me` mit `modules: ["interactive"]`
laden, falls in dieser Sitzung noch nicht geschehen. Das Widget enthält **nur** das Formular;
die zwei Sätze Erklärung (Zeitraum, Quellen, was fehlt) stehen im Chattext davor.

Warum ein eigenes Formular und nicht die Elicitation-Vorlage: Albert will beim Eintragen
sofort sehen, wie viel Zeit für den Tag schon zusammenkommt. Das verlangt eine Summe, die bei
jeder Eingabe neu rechnet – also eigenes JavaScript.

## Was das Formular zeigt

- Je Tag ein Abschnitt mit Tabelle: Ticket (Key + Kurztitel), Beleg (Uhrzeiten, Quelle,
  Rückfrage), Minuten-Eingabefeld.
- Vorschlag = vorausgefüllter Wert, immer auf volle Viertelstunden aufgerundet (das Skript
  liefert ihn so). Die Felder zählen in 15-min-Schritten (`step="15"`); andere Werte lassen sich
  trotzdem tippen und werden so gebucht. Hängt eine Rückfrage am Ticket, bleibt das Feld **leer**
  und der Platzhalter zeigt den gekappten Vorschlag („max. 120“). Keine Spur = leer.
- Termine und Blöcke ohne Ticket bekommen ein Ticket-Feld; leer heißt „nicht buchen“.
- Unter jeder Tagestabelle: **Summe** aller Zeilen mit Ticket (live), daneben der Abstand zur
  Sollzeit („bis 8 h fehlen 2 h 20 min“) und die nicht gebuchte Zeit (Termine ohne Ticket).
- „+ Zeile“ fügt eine freie Zeile (Ticket oder Thema + Minuten) hinzu.
- „Buchen“ schickt alles in einer Nachricht an Claude, „Abbrechen“ bricht ab.

Sollzeit: `data-soll` in Minuten am Wurzelelement, Standard 480. Liefert eine Quelle die
tatsächliche Arbeitszeit des Tages (z. B. TimeTac), diesen Wert eintragen und im Chattext sagen.

## Vorlage

Platzhalter in Großbuchstaben ersetzen; je Tag einen `section.md-day`, je Ticket eine Zeile.
Keine Ticket-Inhalte in die Zeilen, nur Key, Kurztitel, Uhrzeiten, Quelle, Rückfrage.

```html
<h2 class="sr-only">MicDrop-Formular: Minuten je Ticket eintragen, die Tagessumme rechnet sofort mit</h2>
<div id="micdrop" data-soll="480">

  <section class="md-day" data-day="2026-11-16">
    <h3>Montag, 16.11.2026</h3>
    <table style="width:100%; border-collapse:collapse; font-size:14px; table-layout:fixed;">
      <colgroup><col style="width:34%"><col><col style="width:120px"></colgroup>
      <thead>
        <tr style="color:var(--text-secondary); font-size:12px;">
          <th style="text-align:left; padding:6px 4px; border-bottom:0.5px solid var(--border);">Ticket</th>
          <th style="text-align:left; padding:6px 4px; border-bottom:0.5px solid var(--border);">Beleg</th>
          <th style="text-align:right; padding:6px 4px; border-bottom:0.5px solid var(--border);">Minuten</th>
        </tr>
      </thead>
      <tbody>
        <!-- Ticket mit Vorschlag: value vorbelegt -->
        <tr data-key="TECH-557">
          <td style="padding:8px 4px; vertical-align:top;"><span style="font-weight:500">TECH-557</span><br><span style="color:var(--text-secondary); font-size:13px;">Keine Info Mail an Kunden über Neues Ticket</span></td>
          <td style="padding:8px 4px; vertical-align:top; color:var(--text-secondary); font-size:13px;">Kommentar 08:25 und 12:16 · Vorschlag 60</td>
          <td style="padding:8px 4px; text-align:right;"><input type="number" class="md-min" min="0" step="15" value="60" style="width:90px; text-align:right;" aria-label="Minuten TECH-557"></td>
        </tr>
        <!-- Ticket mit Rückfrage: value leer, Rückfrage als Satz, Platzhalter zeigt die Kappung -->
        <tr data-key="TECH-457">
          <td style="padding:8px 4px; vertical-align:top;"><span style="font-weight:500">TECH-457</span><br><span style="color:var(--text-secondary); font-size:13px;">Automatischer Mindestwert von 0,1 € an Landmark</span></td>
          <td style="padding:8px 4px; vertical-align:top; color:var(--text-secondary); font-size:13px;">Kommentar 11:00 · davor 155 min ohne andere Spur. <span style="color:var(--text-warning)">War das alles TECH-457?</span></td>
          <td style="padding:8px 4px; text-align:right;"><input type="number" class="md-min" min="0" step="15" placeholder="max. 120" style="width:90px; text-align:right;" aria-label="Minuten TECH-457"></td>
        </tr>
        <!-- Termin: Ticket-Feld, leer = nicht buchen -->
        <tr data-key="Termin Tech Daily 09:30–10:30" data-kind="termin">
          <td style="padding:8px 4px; vertical-align:top;"><input type="text" class="md-ticket" placeholder="Ticket oder leer" style="width:95%;" aria-label="Ticket für Tech Daily"><br><span style="color:var(--text-secondary); font-size:13px;">Tech Daily 09:30–10:30</span></td>
          <td style="padding:8px 4px; vertical-align:top; color:var(--text-secondary); font-size:13px;">Kalender · leer = nicht buchen</td>
          <td style="padding:8px 4px; text-align:right;"><input type="number" class="md-min" min="0" step="15" value="60" style="width:90px; text-align:right;" aria-label="Minuten Tech Daily"></td>
        </tr>
      </tbody>
      <tfoot>
        <tr>
          <td colspan="2" style="padding:10px 4px; border-top:0.5px solid var(--border);"><button type="button" class="md-add">+ Zeile</button></td>
          <td style="padding:10px 4px; border-top:0.5px solid var(--border); text-align:right; white-space:nowrap;">
            <span class="md-sum" style="font-size:16px; font-weight:500;"></span><br>
            <span class="md-rest" style="color:var(--text-muted); font-size:12px;"></span><br>
            <span class="md-unbooked" style="color:var(--text-muted); font-size:12px;"></span>
          </td>
        </tr>
      </tfoot>
    </table>
  </section>

  <!-- weitere Tage als weitere section.md-day -->

  <div style="display:flex; gap:12px; justify-content:flex-end; align-items:center; margin-top:1rem;">
    <span id="md-total" style="color:var(--text-secondary); font-size:13px; margin-right:auto;"></span>
    <button type="button" id="md-cancel">Abbrechen</button>
    <button type="button" id="md-submit">Buchen ↗</button>
  </div>
  <p id="md-error" style="color:var(--text-danger); font-size:13px; display:none; margin:8px 0 0;"></p>
</div>
<script>
(function () {
  var root = document.getElementById('micdrop');
  var soll = Number(root.dataset.soll) || 480;
  function fmt(m) { m = Math.round(m); return m >= 60 ? Math.floor(m / 60) + ' h ' + ('0' + (m % 60)).slice(-2) + ' min' : m + ' min'; }
  function rowKey(tr) { var t = tr.querySelector('.md-ticket'); return t ? t.value.trim() : (tr.dataset.key || ''); }
  function rowMin(tr) { var i = tr.querySelector('.md-min'); var v = i ? Number(i.value) : 0; return v > 0 ? v : 0; }
  function recalc() {
    var total = 0;
    root.querySelectorAll('.md-day').forEach(function (day) {
      var booked = 0, unbooked = 0;
      day.querySelectorAll('tbody tr').forEach(function (tr) {
        var m = rowMin(tr);
        if (rowKey(tr)) booked += m; else unbooked += m;
      });
      total += booked;
      day.querySelector('.md-sum').textContent = 'Summe ' + fmt(booked);
      var rest = day.querySelector('.md-rest');
      rest.textContent = booked < soll ? 'bis ' + fmt(soll) + ' fehlen ' + fmt(soll - booked)
                       : booked > soll ? fmt(booked - soll) + ' über ' + fmt(soll) : 'entspricht ' + fmt(soll);
      day.querySelector('.md-unbooked').textContent = unbooked ? 'nicht gebucht: ' + fmt(unbooked) : '';
    });
    var days = root.querySelectorAll('.md-day').length;
    document.getElementById('md-total').textContent = days > 1 ? 'Gesamt ' + fmt(total) : '';
  }
  root.addEventListener('input', function (e) {
    if (e.target.classList.contains('md-min') || e.target.classList.contains('md-ticket')) e.target.style.borderColor = '';
    recalc();
  });
  root.querySelectorAll('.md-add').forEach(function (b) {
    b.addEventListener('click', function () {
      var tbody = b.closest('table').querySelector('tbody');
      var tr = document.createElement('tr');
      tr.dataset.kind = 'frei';
      tr.innerHTML = '<td style="padding:8px 4px;"><input type="text" class="md-ticket" placeholder="Ticket-Key oder Thema" style="width:95%;" aria-label="Ticket oder Thema"></td>'
        + '<td style="padding:8px 4px; color:var(--text-secondary); font-size:13px;">ohne Spur</td>'
        + '<td style="padding:8px 4px; text-align:right;"><input type="number" class="md-min" min="0" step="15" placeholder="Minuten" style="width:90px; text-align:right;" aria-label="Minuten"></td>';
      tbody.appendChild(tr);
      tr.querySelector('.md-ticket').focus();
    });
  });
  document.getElementById('md-cancel').addEventListener('click', function () { sendPrompt('MicDrop abbrechen, nichts buchen.'); });
  document.getElementById('md-submit').addEventListener('click', function () {
    var err = document.getElementById('md-error'), bad = false, parts = [];
    root.querySelectorAll('.md-day').forEach(function (day) {
      var items = [];
      day.querySelectorAll('tbody tr').forEach(function (tr) {
        var inp = tr.querySelector('.md-min'), v = inp ? inp.value.trim() : '';
        var tick = tr.querySelector('.md-ticket'), key = rowKey(tr);
        if (v !== '' && !/^\d+$/.test(v)) { bad = true; inp.style.borderColor = 'var(--border-danger)'; return; }
        if (tr.dataset.kind === 'frei' && v && !key) { bad = true; tick.style.borderColor = 'var(--border-danger)'; return; }
        if (tr.dataset.kind === 'termin' && !key) { items.push(tr.dataset.key + ': nicht buchen'); return; }
        if (!key) return;
        if (tr.dataset.kind === 'termin') { items.push(tr.dataset.key + ' auf ' + key + ': ' + (v || '0')); return; }
        items.push(key + ': ' + (v === '' ? 'offen' : v));
      });
      parts.push(day.dataset.day + ' → ' + items.join(', ') + ' | ' + day.querySelector('.md-sum').textContent);
    });
    if (bad) { err.textContent = 'Nur ganze Minuten eintragen; freie Zeilen brauchen ein Ticket oder Thema.'; err.style.display = 'block'; return; }
    err.style.display = 'none';
    sendPrompt('MicDrop buchen: ' + parts.join(' || '));
  });
  recalc();
})();
</script>
```

Regeln für das Befüllen:

- `data-day` im ISO-Format, Überschrift als Wochentag und Datum.
- `data-key` = Ticket-Key; für Termine und Blöcke ohne Ticket ein sprechender Text
  (`Termin Tech Daily 09:30–10:30`, `Claude-Code 15:27–15:32 ohne Ticket`) mit `data-kind="termin"`.
- Vorschlag nur als `value`, wenn keine Rückfrage am Ticket hängt; sonst `placeholder="max. N"`.
- Mehrtägig: je Tag ein Abschnitt; ein Ticket mit Spuren an mehreren Tagen steht in jedem Tag.
- Höchstens 20 Zeilen je Tag; mehr: die kleinsten (unter 10 min) vorab im Chat zusammenfassen.
- Script-Block unverändert übernehmen; nur die Tabellen ändern sich.

## Antwort lesen

„Buchen“ schickt eine Nachricht in dieser Form:

```text
MicDrop buchen: 2026-11-16 → TECH-557: 60, TECH-457: offen, Termin Tech Daily 09:30–10:30 auf TECH-123: 60, Recherche Heidler: 90 | Summe 3 h 30 min || 2026-11-15 → TECH-675: 20 | Summe 20 min
```

- `KEY: Zahl` → Minuten buchen; `0` → auslassen.
- `KEY: offen` → nicht buchen, in der Abschlussausgabe als „offen gelassen“ nennen.
- `Termin … auf KEY: Zahl` → auf dieses Ticket; `Termin …: nicht buchen` → auslassen.
- Zeile ohne Ticket-Key (freier Text) → Ticket suchen oder nach team-and-routing.md anlegen.
- `MicDrop abbrechen` → nichts buchen, Vorschlagsliste als Text ausgeben.

Die Summe in der Nachricht ist Alberts Entscheidungsgrundlage gewesen; sie wird nicht
nachgerechnet, sondern die Einzelwerte werden gebucht.

## Ohne Formular-Werkzeug

Dieselben Zeilen als Text, Vorschlag in Klammern, dazu die Sollzeit. Albert antwortet in einer
Nachricht; danach die Tagessummen ausrechnen und vor dem Buchen nennen, damit er noch
ergänzen kann:

```text
MicDrop 16.11. — bitte Minuten eintragen (Vorschlag in Klammern, Soll 8 h):
TECH-557  Keine Info Mail an Kunden … (60, Kommentar 08:25 + 12:16)                 → ___
TECH-457  Automatischer Mindestwert … (max 120, 155 min Lücke – alles TECH-457?)     → ___
Tech Daily 09:30–10:30 (60) → Ticket oder „nicht buchen“
Fehlt etwas? Ticket/Thema + Minuten
```
