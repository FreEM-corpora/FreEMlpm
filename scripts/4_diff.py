#!/usr/bin/env python3
"""
ÉTAPE 4 — Rapport de diff
==========================
Compare le fichier CoNLL source et le fichier corrigé,
et produit un rapport HTML lisible.

Usage:
    python 4_diff.py source.conll corrige.conll
    python 4_diff.py source.conll corrige.conll --output rapport_diff.html
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict


# ---------------------------------------------------------------------------
# Lecture et comparaison
# ---------------------------------------------------------------------------

def read_conll(path: str) -> list[tuple[int, list[str]]]:
    """Lit un CoNLL, retourne [(line_idx, cols)] pour les lignes non vides."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            raw = line.rstrip("\n")
            if not raw.strip():
                continue
            cols = raw.split("\t")
            rows.append((i, cols))
    return rows


def compute_diff(source_path: str, corrige_path: str) -> dict:
    """
    Compare les deux fichiers ligne par ligne.
    Retourne un rapport structuré.
    """
    print(f"Lecture de {source_path}...")
    source_rows = read_conll(source_path)
    print(f"Lecture de {corrige_path}...")
    corrige_rows = read_conll(corrige_path)

    if len(source_rows) != len(corrige_rows):
        print(f"  AVERTISSEMENT : nombre de lignes différent ({len(source_rows):,} vs {len(corrige_rows):,})")

    changes = []
    anomalies = []
    unchanged = 0

    for (s_idx, s_cols), (c_idx, c_cols) in zip(source_rows, corrige_rows):
        if s_idx != c_idx:
            anomalies.append({
                "type": "décalage de ligne",
                "source_line": s_idx + 1,
                "corrige_line": c_idx + 1,
            })

        if len(s_cols) < 8 or len(c_cols) < 8:
            if s_cols != c_cols:
                anomalies.append({
                    "type": "ligne malformée modifiée",
                    "line": s_idx + 1,
                    "source": "\t".join(s_cols),
                    "corrige": "\t".join(c_cols),
                })
            continue

        s_wikidata = s_cols[7].strip()
        c_wikidata = c_cols[7].strip()

        # Vérifier que seule la colonne WikidataID a changé
        other_changed = any(s_cols[i] != c_cols[i] for i in range(7))
        if other_changed:
            anomalies.append({
                "type": "colonne inattendue modifiée",
                "line": s_idx + 1,
                "source": "\t".join(s_cols),
                "corrige": "\t".join(c_cols),
            })
            continue

        if s_wikidata != c_wikidata:
            changes.append({
                "line": s_idx + 1,
                "token": s_cols[0],
                "lemma": s_cols[1],
                "ner1": s_cols[3],
                "ner2": s_cols[4],
                "old_id": s_wikidata,
                "new_id": c_wikidata,
            })
        else:
            unchanged += 1

    # Regrouper les changements par entité (spans contigus)
    spans = group_into_spans(changes)

    return {
        "source_file": source_path,
        "corrige_file": corrige_path,
        "generated_at": datetime.now().isoformat(),
        "stats": {
            "total_lines": len(source_rows),
            "lines_changed": len(changes),
            "lines_unchanged": unchanged,
            "spans_changed": len(spans),
            "anomalies": len(anomalies),
        },
        "spans": spans,
        "anomalies": anomalies,
    }


def group_into_spans(changes: list[dict]) -> list[dict]:
    """
    Regroupe les changements de lignes contigus en spans d'entités.
    Ex: lignes 100, 101, 102 avec le même changement → un span "ville de Paris".
    """
    if not changes:
        return []

    spans = []
    current = None

    for ch in changes:
        if current is None:
            current = {
                "line_start": ch["line"],
                "line_end": ch["line"],
                "tokens": [ch["token"]],
                "ner_type": ch["ner1"] if ch["ner1"] != "O" else ch["ner2"],
                "old_id": ch["old_id"],
                "new_id": ch["new_id"],
            }
        elif (
            ch["line"] == current["line_end"] + 1
            and ch["old_id"] == current["old_id"]
            and ch["new_id"] == current["new_id"]
        ):
            current["line_end"] = ch["line"]
            current["tokens"].append(ch["token"])
        else:
            current["entity_text"] = " ".join(current["tokens"])
            spans.append(current)
            current = {
                "line_start": ch["line"],
                "line_end": ch["line"],
                "tokens": [ch["token"]],
                "ner_type": ch["ner1"] if ch["ner1"] != "O" else ch["ner2"],
                "old_id": ch["old_id"],
                "new_id": ch["new_id"],
            }

    if current:
        current["entity_text"] = " ".join(current["tokens"])
        spans.append(current)

    return spans


# ---------------------------------------------------------------------------
# Rapport HTML
# ---------------------------------------------------------------------------

def write_html(diff: dict, output_path: str):
    stats = diff["stats"]
    spans = diff["spans"]
    anomalies = diff["anomalies"]

    # Regrouper les spans par (old_id → new_id)
    by_change = defaultdict(list)
    for sp in spans:
        key = (sp["old_id"], sp["new_id"])
        by_change[key].append(sp)

    # Trier : nouvelles assignations en premier, puis corrections d'ID
    def sort_key(item):
        (old, new), sps = item
        if old == "_":
            return (0, -len(sps))
        return (1, -len(sps))

    sorted_changes = sorted(by_change.items(), key=sort_key)

    # Générer les sections HTML
    sections_html = ""
    for (old_id, new_id), sps in sorted_changes:
        change_type = "Nouvel ID assigné" if old_id == "_" else "ID corrigé"
        arrow = f'<span class="id-old">{old_id}</span> → <span class="id-new">{new_id}</span>'
        rows = "".join(f"""
            <tr>
                <td class="mono">{sp['line_start']}{f"–{sp['line_end']}" if sp['line_end'] != sp['line_start'] else ''}</td>
                <td><strong>{sp['entity_text']}</strong></td>
                <td class="ner">{sp.get('ner_type','')}</td>
            </tr>
        """ for sp in sps)
        more = ""

        sections_html += f"""
        <div class="change-block">
            <div class="change-header">
                <span class="change-type">{change_type}</span>
                <span class="change-arrow">{arrow}</span>
                <span class="change-count">{len(sps)} entité(s)</span>
            </div>
            <table class="change-table">
                <thead><tr><th>Ligne(s)</th><th>Entité</th><th>Type NER</th></tr></thead>
                <tbody>{rows}{more}</tbody>
            </table>
        </div>
        """

    anomalies_html = ""
    if anomalies:
        rows = "".join(f"""
            <tr>
                <td class="mono">{a.get('line', a.get('source_line', '?'))}</td>
                <td class="warn">{a['type']}</td>
                <td class="mono small">{a.get('source', '')[:80]}</td>
                <td class="mono small">{a.get('corrige', '')[:80]}</td>
            </tr>
        """ for a in anomalies)
        anomalies_html = f"""
        <section>
            <h2 class="section-title warn">⚠ Anomalies ({len(anomalies)})</h2>
            <table class="change-table">
                <thead><tr><th>Ligne</th><th>Type</th><th>Source</th><th>Corrigé</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </section>
        """

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Diff CoNLL — {Path(diff['source_file']).name} → {Path(diff['corrige_file']).name}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; font-size: 14px; color: #1a1a18; background: #f5f5f3; line-height: 1.5; }}
  header {{ background: #fff; border-bottom: 0.5px solid rgba(0,0,0,0.12); padding: 20px 32px; }}
  header h1 {{ font-size: 18px; font-weight: 500; margin-bottom: 4px; }}
  header p {{ font-size: 12px; color: #6b6b67; }}
  .stats-row {{ display: flex; gap: 16px; padding: 20px 32px; flex-wrap: wrap; }}
  .stat-card {{ background: #fff; border: 0.5px solid rgba(0,0,0,0.12); border-radius: 10px; padding: 12px 20px; min-width: 140px; }}
  .stat-val {{ font-size: 28px; font-weight: 500; }}
  .stat-val.green {{ color: #27500A; }}
  .stat-val.amber {{ color: #633806; }}
  .stat-val.red {{ color: #791F1F; }}
  .stat-lbl {{ font-size: 12px; color: #6b6b67; }}
  main {{ padding: 0 32px 40px; display: flex; flex-direction: column; gap: 12px; }}
  section {{ background: #fff; border: 0.5px solid rgba(0,0,0,0.12); border-radius: 10px; padding: 16px 20px; }}
  .section-title {{ font-size: 13px; font-weight: 500; margin-bottom: 12px; color: #6b6b67; text-transform: uppercase; letter-spacing: 0.04em; }}
  .section-title.warn {{ color: #791F1F; }}
  .change-block {{ border: 0.5px solid rgba(0,0,0,0.1); border-radius: 8px; margin-bottom: 10px; overflow: hidden; }}
  .change-header {{ display: flex; align-items: center; gap: 12px; padding: 8px 12px; background: #f5f5f3; flex-wrap: wrap; }}
  .change-type {{ font-size: 11px; font-weight: 500; color: #6b6b67; }}
  .change-arrow {{ font-family: monospace; font-size: 13px; }}
  .id-old {{ color: #791F1F; }}
  .id-new {{ color: #27500A; font-weight: 500; }}
  .change-count {{ font-size: 11px; color: #9b9b97; margin-left: auto; }}
  .change-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .change-table th {{ text-align: left; padding: 6px 12px; font-size: 11px; font-weight: 500; color: #6b6b67; border-bottom: 0.5px solid rgba(0,0,0,0.1); }}
  .change-table td {{ padding: 5px 12px; border-bottom: 0.5px solid rgba(0,0,0,0.06); }}
  .change-table tr:last-child td {{ border-bottom: none; }}
  .mono {{ font-family: monospace; font-size: 12px; color: #6b6b67; }}
  .small {{ font-size: 11px; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .ner {{ font-size: 11px; color: #6b6b67; }}
  .warn {{ color: #791F1F; }}
  .more {{ font-size: 11px; color: #9b9b97; font-style: italic; text-align: center; padding: 6px; }}
  .files {{ font-size: 12px; color: #6b6b67; display: flex; flex-direction: column; gap: 2px; margin-top: 6px; }}
  .files span {{ font-family: monospace; }}
</style>
</head>
<body>
<header>
  <h1>Rapport de diff CoNLL</h1>
  <div class="files">
    <div>Source  : <span>{diff['source_file']}</span></div>
    <div>Corrigé : <span>{diff['corrige_file']}</span></div>
    <div>Généré le {datetime.fromisoformat(diff['generated_at']).strftime('%d/%m/%Y à %H:%M')}</div>
  </div>
</header>

<div class="stats-row">
  <div class="stat-card">
    <div class="stat-val">{stats['total_lines']:,}</div>
    <div class="stat-lbl">lignes totales</div>
  </div>
  <div class="stat-card">
    <div class="stat-val green">{stats['spans_changed']:,}</div>
    <div class="stat-lbl">entités modifiées</div>
  </div>
  <div class="stat-card">
    <div class="stat-val amber">{stats['lines_changed']:,}</div>
    <div class="stat-lbl">lignes modifiées</div>
  </div>
  <div class="stat-card">
    <div class="stat-val">{stats['lines_unchanged']:,}</div>
    <div class="stat-lbl">lignes inchangées</div>
  </div>
  <div class="stat-card">
    <div class="stat-val {'red' if stats['anomalies'] else 'green'}">{stats['anomalies']}</div>
    <div class="stat-lbl">anomalies</div>
  </div>
</div>

<main>
  {anomalies_html}
  <section>
    <div class="section-title">Modifications par type de changement</div>
    {sections_html if sections_html else '<p style="color:#9b9b97; font-size:13px;">Aucune modification détectée.</p>'}
  </section>
</main>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Rapport écrit : {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compare un CoNLL source et un CoNLL corrigé, produit un rapport HTML."
    )
    parser.add_argument("source", help="Fichier CoNLL source")
    parser.add_argument("corrige", help="Fichier CoNLL corrigé (produit par 3_appliquer.py)")
    parser.add_argument("--output", "-o", default="rapport_diff.html",
                        help="Fichier HTML de sortie (défaut: rapport_diff.html)")
    args = parser.parse_args()

    diff = compute_diff(args.source, args.corrige)

    print(f"\n=== RÉSUMÉ ===")
    print(f"  Lignes totales    : {diff['stats']['total_lines']:,}")
    print(f"  Entités modifiées : {diff['stats']['spans_changed']:,}")
    print(f"  Lignes modifiées  : {diff['stats']['lines_changed']:,}")
    print(f"  Anomalies         : {diff['stats']['anomalies']}")

    write_html(diff, args.output)
    print(f"\nOuvre {args.output} dans ton navigateur pour lire le rapport.")


if __name__ == "__main__":
    main()
