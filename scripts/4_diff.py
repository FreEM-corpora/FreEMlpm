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
                "raw_source": "\t".join(s_cols),
                "raw_corrige": "\t".join(c_cols),
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
                "lines_source": [ch["raw_source"]],
                "lines_corrige": [ch["raw_corrige"]],
            }
        elif (
            ch["line"] == current["line_end"] + 1
            and ch["old_id"] == current["old_id"]
            and ch["new_id"] == current["new_id"]
        ):
            current["line_end"] = ch["line"]
            current["tokens"].append(ch["token"])
            current["lines_source"].append(ch["raw_source"])
            current["lines_corrige"].append(ch["raw_corrige"])
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
                "lines_source": [ch["raw_source"]],
                "lines_corrige": [ch["raw_corrige"]],
            }

    if current:
        current["entity_text"] = " ".join(current["tokens"])
        spans.append(current)

    return spans


# ---------------------------------------------------------------------------
# Rapport HTML
# ---------------------------------------------------------------------------

def esc(s: str) -> str:
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


def render_span(sp: dict) -> str:
    line_range = str(sp['line_start']) if sp['line_start'] == sp['line_end'] else f"{sp['line_start']}–{sp['line_end']}"
    source_lines = "".join(
        f'<div class="diff-line diff-del"><span class="diff-marker">−</span><span class="diff-code">{esc(l)}</span></div>'
        for l in sp["lines_source"]
    )
    corrige_lines = "".join(
        f'<div class="diff-line diff-add"><span class="diff-marker">+</span><span class="diff-code">{esc(l)}</span></div>'
        for l in sp["lines_corrige"]
    )
    return f"""<div class="span-block">
      <div class="span-header">
        <span class="span-entity">{esc(sp['entity_text'])}</span>
        <span class="span-ner">{esc(sp.get('ner_type',''))}</span>
        <span class="span-ids"><span class="id-old">{esc(sp['old_id'])}</span> → <span class="id-new">{esc(sp['new_id'])}</span></span>
        <span class="span-line">ligne {line_range}</span>
      </div>
      <div class="diff-block">{source_lines}{corrige_lines}</div>
    </div>"""


def write_html(diff: dict, output_path: str):
    stats = diff["stats"]
    spans = diff["spans"]
    anomalies = diff["anomalies"]

    by_change = defaultdict(list)
    for sp in spans:
        by_change[(sp["old_id"], sp["new_id"])].append(sp)

    def sort_key(item):
        (old, new), sps = item
        return (0 if old == "_" else 1, -len(sps))

    sections_html = ""
    for (old_id, new_id), sps in sorted(by_change.items(), key=sort_key):
        change_type = "Nouvel ID assigné" if old_id == "_" else "ID corrigé"
        spans_html = "".join(render_span(sp) for sp in sps)
        sections_html += f"""<section>
      <div class="section-header">
        <span class="change-type">{change_type}</span>
        <span class="change-arrow"><span class="id-old">{esc(old_id)}</span> → <span class="id-new">{esc(new_id)}</span></span>
        <span class="change-count">{len(sps)} entité(s)</span>
      </div>
      {spans_html}
    </section>"""

    anomalies_html = ""
    if anomalies:
        rows = "".join(f"""<tr>
          <td class="mono">{a.get('line', a.get('source_line', '?'))}</td>
          <td class="warn-text">{esc(a['type'])}</td>
          <td class="mono small">{esc(a.get('source',''))[:100]}</td>
          <td class="mono small">{esc(a.get('corrige',''))[:100]}</td>
        </tr>""" for a in anomalies)
        anomalies_html = f"""<section class="anom-section">
      <div class="section-header warn-header">
        <span class="change-type">⚠ Anomalies</span>
        <span class="change-count">{len(anomalies)}</span>
      </div>
      <table class="anom-table">
        <thead><tr><th>Ligne</th><th>Type</th><th>Source</th><th>Corrigé</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>"""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Diff CoNLL — {esc(Path(diff['source_file']).name)}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; font-size: 13px; color: #1a1a18; background: #f5f5f3; line-height: 1.5; }}
  header {{ background: #fff; border-bottom: 0.5px solid rgba(0,0,0,0.12); padding: 18px 28px; }}
  header h1 {{ font-size: 16px; font-weight: 500; margin-bottom: 6px; }}
  .files {{ font-size: 12px; color: #6b6b67; display: flex; flex-direction: column; gap: 2px; }}
  .files span {{ font-family: monospace; color: #1a1a18; }}
  .stats-row {{ display: flex; gap: 12px; padding: 14px 28px; flex-wrap: wrap; }}
  .stat-card {{ background: #fff; border: 0.5px solid rgba(0,0,0,0.12); border-radius: 8px; padding: 10px 18px; }}
  .stat-val {{ font-size: 22px; font-weight: 500; }}
  .stat-val.green {{ color: #27500A; }} .stat-val.amber {{ color: #633806; }} .stat-val.red {{ color: #791F1F; }}
  .stat-lbl {{ font-size: 11px; color: #6b6b67; }}
  main {{ padding: 0 28px 48px; display: flex; flex-direction: column; gap: 10px; }}
  section {{ background: #fff; border: 0.5px solid rgba(0,0,0,0.12); border-radius: 10px; overflow: hidden; }}
  .section-header {{ display: flex; align-items: center; gap: 10px; padding: 9px 14px; background: #f5f5f3; border-bottom: 0.5px solid rgba(0,0,0,0.1); }}
  .warn-header {{ background: #FCEBEB; }}
  .change-type {{ font-size: 11px; font-weight: 500; color: #6b6b67; text-transform: uppercase; letter-spacing: 0.04em; }}
  .change-arrow {{ font-family: monospace; font-size: 13px; }}
  .change-count {{ font-size: 11px; color: #9b9b97; margin-left: auto; }}
  .id-old {{ color: #791F1F; font-family: monospace; font-weight: 600; }}
  .id-new {{ color: #27500A; font-family: monospace; font-weight: 600; }}
  .span-block {{ border-bottom: 0.5px solid rgba(0,0,0,0.07); }}
  .span-block:last-child {{ border-bottom: none; }}
  .span-header {{ display: flex; align-items: baseline; gap: 10px; padding: 6px 14px; background: #fafaf9; border-bottom: 0.5px solid rgba(0,0,0,0.06); flex-wrap: wrap; }}
  .span-entity {{ font-weight: 500; }}
  .span-ner {{ font-size: 11px; color: #9b9b97; }}
  .span-ids {{ font-size: 12px; }}
  .span-line {{ font-size: 11px; color: #9b9b97; margin-left: auto; font-family: monospace; }}
  .diff-block {{ font-family: monospace; font-size: 12px; }}
  .diff-line {{ display: flex; gap: 8px; padding: 2px 14px; }}
  .diff-del {{ background: #FFF0F0; color: #791F1F; }}
  .diff-add {{ background: #F0FFF4; color: #1A5C1A; }}
  .diff-marker {{ font-weight: 700; width: 12px; flex-shrink: 0; user-select: none; }}
  .diff-code {{ white-space: pre; overflow-x: auto; }}
  .anom-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  .anom-table th {{ text-align: left; padding: 6px 12px; font-size: 11px; color: #6b6b67; border-bottom: 0.5px solid rgba(0,0,0,0.1); }}
  .anom-table td {{ padding: 5px 12px; border-bottom: 0.5px solid rgba(0,0,0,0.06); vertical-align: top; }}
  .mono {{ font-family: monospace; color: #6b6b67; }}
  .small {{ max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .warn-text {{ color: #791F1F; font-weight: 500; }}
</style>
</head>
<body>
<header>
  <h1>Rapport de diff CoNLL</h1>
  <div class="files">
    <div>Source  : <span>{esc(diff['source_file'])}</span></div>
    <div>Corrigé : <span>{esc(diff['corrige_file'])}</span></div>
    <div style="margin-top:4px;font-size:11px;">Généré le {datetime.fromisoformat(diff['generated_at']).strftime('%d/%m/%Y à %H:%M')}</div>
  </div>
</header>
<div class="stats-row">
  <div class="stat-card"><div class="stat-val">{stats['total_lines']:,}</div><div class="stat-lbl">lignes totales</div></div>
  <div class="stat-card"><div class="stat-val green">{stats['spans_changed']:,}</div><div class="stat-lbl">entités modifiées</div></div>
  <div class="stat-card"><div class="stat-val amber">{stats['lines_changed']:,}</div><div class="stat-lbl">lignes modifiées</div></div>
  <div class="stat-card"><div class="stat-val">{stats['lines_unchanged']:,}</div><div class="stat-lbl">lignes inchangées</div></div>
  <div class="stat-card"><div class="stat-val {'red' if stats['anomalies'] else 'green'}">{stats['anomalies']}</div><div class="stat-lbl">anomalies</div></div>
</div>
<main>
  {anomalies_html}
  {sections_html or '<section style="padding:20px;color:#9b9b97;">Aucune modification détectée.</section>'}
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
