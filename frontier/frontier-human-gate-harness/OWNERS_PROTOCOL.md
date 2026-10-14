# Owner protocol — one sitting at the human product gate

Charter v1 · `frontier-human-gate-harness` · questions verbatim from
`LEXMACHINA_MASTER_PROMPT.md` § Human product gate (EN), rendered FR/DE on the card.

## FR — protocole (une session, hors ligne)

1. Ouvrez `harness_demo.html` (généré par la CLI, aucune requête réseau).
   Requête identique, **même bundle** pour les deux vues.
2. Notez d'abord la **liste classée conventionnelle (baseline)** : rang, tribunal, date,
   langue, citation, extrait, source. Rien d'autre n'y figure (pas de couleur de cluster,
   pas de proximité, pas de regroupement de contre-autorités).
3. Basculez vers la **carte** (bouton `Liste ↔ Carte`). Aucune nouvelle requête :
   la comparaison porte sur littéralement les mêmes pièces. Notez ce que la carte rend
   visible (ou masque) par rapport à la liste.
4. Ouvrez les décisions et contre-autorités qui vous intéressent (chaque ouverture est
   horodatée dans le brouillon).
5. Remplissez les **4 questions** (échelle 1–5 + commentaire libre). Une seule occurrence
   concrète suffit pour Q1 : citez l'identifiant de décision.
6. Renseignez l'identifiant de session, cliquez **Exporter** →
   `<session_id>.json` (brouillon, 22 champs, aucune donnée personnelle).
7. Finalisez le registre :

   ```bash
   python -m frontier_human_gate_harness.cli --finalize <session_id>.json \
       --fixture <bundle.json> --out results/frontier/frontier-human-gate-harness
   ```

   Une réponse manquante ⇒ **exit 2, rien n'est inventé**. Registre explicite mais incomplet
   uniquement si vous passez `--allow-incomplete` (`status:"incomplete"` +
   `missing_answers` listées).

**Décision.** Si la carte n'améliore pas la réponse + liste classée, le verdict du Main
Prompt s'applique : *« If not, stop the standalone product. »* C'est le propriétaire qui
décide ; cette équipe n'apporte que les pièces et le registre.

## DE — Protokoll (eine Sitzung, offline)

1. `harness_demo.html` öffnen (von der CLI erzeugt, keine Netzwerkanfrage).
2. Zuerst die **konventionelle Rangliste (Baseline)** notieren: Rang, Gericht, Datum,
   Sprache, Zitat, Auszug, Quelle — ohne Karteninformation.
3. Umschalten auf die **Karte** (gleiche Anfrage, gleiches Bundle, keine Neuabfrage).
   Notieren, was die Karte sichtbar macht (oder verdeckt).
4. Entscheidungen/Gegenautoritäten öffnen (jede Öffnung wird mit Zeitstempel erfasst).
5. Die **4 Fragen** beantworten (Skala 1–5 + freier Kommentar).
6. Sitzungs-ID eintragen und **Exporter** klicken → `<session_id>.json`.
7. Finalisieren (siehe Befehl oben). Fehlende Antwort ⇒ **exit 2**, nichts wird erfunden.

**Entscheidung.** Wenn Antwort + Rangliste der Karte vorzuziehen ist, gilt der Stop-Satz
des Master Prompt.

## EN — what the record must contain (verification view)

`results/frontier/frontier-human-gate-harness/session_<id>.json`:

| Group | Fields |
|---|---|
| identity | `schema_version, record_type, team_id, charter_version, session_id, session_id_origin, status, source` |
| evidence | `query, bundle_ref, bundle_sha256, query_sha256, bundle_hash_status` |
| timing | `started_at, ended_at, wall_clock_seconds, latency` |
| behaviour | `view_mode_initial, view_mode_final, actions[] (at, view_mode, event, ref), decisions_opened[], counter_authorities_opened[]` |
| answers | `answers{q1..q4: {scale 1–5, text, answered_at}}, missing_answers[]` |

Personal-data keys are forbidden anywhere in the record (schema allow-list, asserted in
`test_capture.py`); `missing_answers` must equal the computed set exactly (no silent
defaults); `bundle_sha256` is `null` unless it was actually computed, and `query_sha256`
is derived from the record's own query string (never trusted — a mismatch is refused).

## The four questions (verbatim EN)

1. Did the map expose a relevant branch, exception or decision that was less visible in the list/answer?
2. Did the map make the jurisprudential structure easier to understand?
3. Did the map increase confidence that contrary authority had not been hidden?
4. Was the combined answer + map preferable to the conventional interface?

Suggested warm-up question (frozen `rent-default` reality-check leg, verbatim FR):

> Sous quelles conditions un bailleur peut-il résilier un bail d'habitation pour retard
> dans le paiement du loyer selon le droit suisse, et quelles exceptions ou limites
> jurisprudentielles existent ?

DE rendering on the card is explicitly labelled as a team translation; alternative DE
query `Kündigung Mietvertrag Mietrecht` is the verbatim `product/static/query.html` default.
