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

def read_conll(path: str) -> tuple[list[tuple[int, list[str]]], dict[int, list[str]]]:
    """
    Lit un CoNLL.
    Retourne :
      - rows : [(line_idx, cols)] pour les lignes non vides
      - index : {line_idx: cols} pour accès rapide par numéro de ligne
    """
    rows = []
    index = {}
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            raw = line.rstrip("\n")
            if not raw.strip():
                continue
            cols = raw.split("\t")
            rows.append((i, cols))
            index[i] = cols
    return rows, index


def compute_diff(source_path: str, corrige_path: str) -> dict:
    """
    Compare les deux fichiers ligne par ligne.
    Retourne un rapport structuré avec le bloc CoNLL complet pour chaque span.
    """
    print(f"Lecture de {source_path}...")
    source_rows, source_index = read_conll(source_path)
    print(f"Lecture de {corrige_path}...")
    corrige_rows, corrige_index = read_conll(corrige_path)

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
                "line_idx": s_idx,
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

    spans = group_into_spans(changes, source_index, corrige_index)

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


def group_into_spans(
    changes: list[dict],
    source_index: dict[int, list[str]],
    corrige_index: dict[int, list[str]]
) -> list[dict]:
    """
    Regroupe les changements contigus en spans.
    Pour chaque span, récupère aussi toutes les lignes CoNLL du bloc
    (lignes modifiées ET non modifiées) pour affichage complet.
    """
    if not changes:
        return []

    COLS = ["token", "lemme", "POS", "NER1", "NER2", "NER3", "NER4", "WikidataID"]
    spans = []
    current = None

    for ch in changes:
        if current is None:
            current = {
                "line_start": ch["line"],
                "line_end": ch["line"],
                "line_idx_start": ch["line_idx"],
                "line_idx_end": ch["line_idx"],
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
            current["line_idx_end"] = ch["line_idx"]
            current["tokens"].append(ch["token"])
            current["lines_source"].append(ch["raw_source"])
            current["lines_corrige"].append(ch["raw_corrige"])
        else:
            current["entity_text"] = " ".join(current["tokens"])
            current["block_source"], current["block_corrige"] = fetch_full_block(
                current["line_idx_start"], current["line_idx_end"],
                source_index, corrige_index, COLS
            )
            spans.append(current)
            current = {
                "line_start": ch["line"],
                "line_end": ch["line"],
                "line_idx_start": ch["line_idx"],
                "line_idx_end": ch["line_idx"],
                "tokens": [ch["token"]],
                "ner_type": ch["ner1"] if ch["ner1"] != "O" else ch["ner2"],
                "old_id": ch["old_id"],
                "new_id": ch["new_id"],
                "lines_source": [ch["raw_source"]],
                "lines_corrige": [ch["raw_corrige"]],
            }

    if current:
        current["entity_text"] = " ".join(current["tokens"])
        current["block_source"], current["block_corrige"] = fetch_full_block(
            current["line_idx_start"], current["line_idx_end"],
            source_index, corrige_index, COLS
        )
        spans.append(current)

    return spans


def fetch_full_block(
    idx_start: int, idx_end: int,
    source_index: dict, corrige_index: dict,
    col_names: list[str]
) -> tuple[list[dict], list[dict]]:
    """
    Récupère toutes les lignes du span (idx_start → idx_end) dans les deux index.
    Retourne deux listes de dicts {col: valeur} pour affichage tabulaire.
    """
    block_src = []
    block_cor = []
    for idx in range(idx_start, idx_end + 1):
        s = source_index.get(idx, [])
        c = corrige_index.get(idx, [])
        if s:
            block_src.append({col_names[i]: s[i] if i < len(s) else "" for i in range(len(col_names))})
        if c:
            block_cor.append({col_names[i]: c[i] if i < len(c) else "" for i in range(len(col_names))})
    return block_src, block_cor


# ---------------------------------------------------------------------------
# Rapport HTML
# ---------------------------------------------------------------------------

def esc(s: str) -> str:
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


COLS = ["token", "lemme", "POS", "NER1", "NER2", "NER3", "NER4", "WikidataID"]


def render_block_table(rows: list[dict], old_id: str, new_id: str, side: str) -> str:
    """Génère un tableau CoNLL complet, en surlignant la colonne WikidataID."""
    is_source = side == "source"
    header = "".join(f"<th>{esc(c)}</th>" for c in COLS)
    body = ""
    for row in rows:
        cells = ""
        for col in COLS:
            val = row.get(col, "")
            if col == "WikidataID":
                if is_source and val == old_id and old_id != "_":
                    cells += f'<td class="cell-old">{esc(val)}</td>'
                elif is_source and val == "_":
                    cells += f'<td class="cell-empty">{esc(val)}</td>'
                elif not is_source:
                    cells += f'<td class="cell-new">{esc(val)}</td>'
                else:
                    cells += f"<td>{esc(val)}</td>"
            else:
                cells += f"<td>{esc(val)}</td>"
        body += f"<tr>{cells}</tr>"
    return f'<table class="block-table"><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>'


def render_span(sp: dict) -> str:
    line_range = str(sp['line_start']) if sp['line_start'] == sp['line_end'] else f"{sp['line_start']}–{sp['line_end']}"

    # Diff condensé (lignes modifiées uniquement)
    diff_lines = "".join(
        f'<div class="diff-line diff-del"><span class="diff-marker">−</span><span class="diff-code">{esc(l)}</span></div>'
        for l in sp["lines_source"]
    ) + "".join(
        f'<div class="diff-line diff-add"><span class="diff-marker">+</span><span class="diff-code">{esc(l)}</span></div>'
        for l in sp["lines_corrige"]
    )

    # Bloc complet tabulaire
    src_table = render_block_table(sp.get("block_source", []), sp["old_id"], sp["new_id"], "source")
    cor_table = render_block_table(sp.get("block_corrige", []), sp["old_id"], sp["new_id"], "corrige")

    return f"""<div class="span-block">
      <div class="span-header">
        <span class="span-entity">{esc(sp['entity_text'])}</span>
        <span class="span-ner">{esc(sp.get('ner_type',''))}</span>
        <span class="span-ids"><span class="id-old">{esc(sp['old_id'])}</span> → <span class="id-new">{esc(sp['new_id'])}</span></span>
        <span class="span-line">ligne {line_range}</span>
      </div>
      <div class="diff-block">{diff_lines}</div>
      <div class="full-block">
        <div class="full-side">
          <div class="full-label">Original</div>
          {src_table}
        </div>
        <div class="full-side">
          <div class="full-label">Corrigé</div>
          {cor_table}
        </div>
      </div>
    </div>"""


def write_html(diff: dict, output_path: str, page_size: int = 100):
    stats = diff["stats"]
    spans = diff["spans"]
    anomalies = diff["anomalies"]

    # Regrouper par (old_id → new_id)
    by_change = defaultdict(list)
    for sp in spans:
        by_change[(sp["old_id"], sp["new_id"])].append(sp)

    def sort_key(item):
        (old, new), sps = item
        return (0 if old == "_" else 1, -len(sps))

    # Aplatir tous les spans dans l'ordre des sections
    all_sections = []  # [(section_label, [spans])]
    for (old_id, new_id), sps in sorted(by_change.items(), key=sort_key):
        label = f"{'Nouvel ID' if old_id == '_' else 'ID corrigé'} : {old_id} → {new_id} ({len(sps)} entité(s))"
        all_sections.append((label, old_id, new_id, sps))

    # Sérialiser tous les spans en JSON pour la pagination côté JS
    import json as _json
    spans_json = _json.dumps([{
        "entity_text": sp["entity_text"],
        "ner_type": sp.get("ner_type", ""),
        "old_id": sp["old_id"],
        "new_id": sp["new_id"],
        "line_start": sp["line_start"],
        "line_end": sp["line_end"],
        "lines_source": sp["lines_source"],
        "lines_corrige": sp["lines_corrige"],
        "block_source": sp.get("block_source", []),
        "block_corrige": sp.get("block_corrige", []),
    } for sp in spans], ensure_ascii=False)

    anomalies_rows = "".join(f"""<tr>
      <td class="mono">{a.get('line', a.get('source_line', '?'))}</td>
      <td class="warn-text">{esc(a['type'])}</td>
      <td class="mono small">{esc(a.get('source',''))[:120]}</td>
      <td class="mono small">{esc(a.get('corrige',''))[:120]}</td>
    </tr>""" for a in anomalies)

    anomalies_html = ""
    if anomalies:
        anomalies_html = f"""<section class="anom-section">
      <div class="section-header warn-header">
        <span class="change-type">⚠ Anomalies</span>
        <span class="change-count">{len(anomalies)}</span>
      </div>
      <table class="anom-table">
        <thead><tr><th>Ligne</th><th>Type</th><th>Source</th><th>Corrigé</th></tr></thead>
        <tbody>{anomalies_rows}</tbody>
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

  /* Pagination */
  .pagination {{ display: flex; align-items: center; gap: 8px; padding: 10px 0; flex-wrap: wrap; }}
  .page-btn {{ padding: 5px 12px; border: 0.5px solid rgba(0,0,0,0.2); border-radius: 6px; background: #fff; cursor: pointer; font-size: 12px; }}
  .page-btn:hover {{ background: #e6f1fb; }}
  .page-btn.active {{ background: #185FA5; color: #fff; border-color: #185FA5; }}
  .page-btn:disabled {{ opacity: 0.4; cursor: default; }}
  .page-info {{ font-size: 12px; color: #6b6b67; margin-left: auto; }}

  /* Sections */
  section {{ background: #fff; border: 0.5px solid rgba(0,0,0,0.12); border-radius: 10px; overflow: hidden; }}
  .section-header {{ display: flex; align-items: center; gap: 10px; padding: 9px 14px; background: #f5f5f3; border-bottom: 0.5px solid rgba(0,0,0,0.1); }}
  .warn-header {{ background: #FCEBEB; }}
  .change-type {{ font-size: 11px; font-weight: 500; color: #6b6b67; text-transform: uppercase; letter-spacing: 0.04em; }}
  .change-count {{ font-size: 11px; color: #9b9b97; margin-left: auto; }}
  .id-old {{ color: #791F1F; font-family: monospace; font-weight: 600; }}
  .id-new {{ color: #27500A; font-family: monospace; font-weight: 600; }}

  /* Span */
  .span-block {{ border-bottom: 0.5px solid rgba(0,0,0,0.07); }}
  .span-block:last-child {{ border-bottom: none; }}
  .span-header {{ display: flex; align-items: baseline; gap: 10px; padding: 7px 14px; background: #fafaf9; border-bottom: 0.5px solid rgba(0,0,0,0.06); flex-wrap: wrap; }}
  .span-entity {{ font-weight: 500; }}
  .span-ner {{ font-size: 11px; color: #9b9b97; }}
  .span-ids {{ font-size: 12px; }}
  .span-line {{ font-size: 11px; color: #9b9b97; margin-left: auto; font-family: monospace; }}

  /* Diff condensé */
  .diff-block {{ font-family: monospace; font-size: 12px; border-bottom: 0.5px solid rgba(0,0,0,0.06); }}
  .diff-line {{ display: flex; gap: 8px; padding: 2px 14px; }}
  .diff-del {{ background: #FFF0F0; color: #791F1F; }}
  .diff-add {{ background: #F0FFF4; color: #1A5C1A; }}
  .diff-marker {{ font-weight: 700; width: 12px; flex-shrink: 0; user-select: none; }}
  .diff-code {{ white-space: pre; overflow-x: auto; }}

  /* Bloc complet */
  .full-block {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0; border-top: 0.5px solid rgba(0,0,0,0.06); }}
  .full-side {{ padding: 8px 14px; overflow-x: auto; }}
  .full-side:first-child {{ border-right: 0.5px solid rgba(0,0,0,0.08); }}
  .full-label {{ font-size: 10px; font-weight: 500; color: #9b9b97; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 5px; }}
  .block-table {{ border-collapse: collapse; font-size: 11px; font-family: monospace; width: 100%; }}
  .block-table th {{ text-align: left; padding: 2px 8px; border-bottom: 0.5px solid rgba(0,0,0,0.1); color: #6b6b67; font-size: 10px; font-weight: 500; white-space: nowrap; }}
  .block-table td {{ padding: 2px 8px; border-bottom: 0.5px solid rgba(0,0,0,0.05); white-space: nowrap; }}
  .block-table tr:last-child td {{ border-bottom: none; }}
  .cell-old {{ background: #FFF0F0; color: #791F1F; font-weight: 600; }}
  .cell-new {{ background: #F0FFF4; color: #1A5C1A; font-weight: 600; }}
  .cell-empty {{ color: #9b9b97; }}

  /* Anomalies */
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
  <div id="pagination-top" class="pagination"></div>
  <div id="spans-container"></div>
  <div id="pagination-bottom" class="pagination"></div>
</main>

<script>
const COLS = {_json.dumps(COLS, ensure_ascii=False)};
const PAGE_SIZE = {page_size};
const allSpans = {spans_json};
let currentPage = 0;
const totalPages = Math.ceil(allSpans.length / PAGE_SIZE);

function esc(s) {{
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

function renderBlockTable(rows, oldId, newId, side) {{
  const isSource = side === 'source';
  const header = COLS.map(c => `<th>${{esc(c)}}</th>`).join('');
  const body = rows.map(row => {{
    const cells = COLS.map(col => {{
      const val = row[col] || '';
      if (col === 'WikidataID') {{
        if (isSource && val === oldId && oldId !== '_') return `<td class="cell-old">${{esc(val)}}</td>`;
        if (isSource && val === '_') return `<td class="cell-empty">${{esc(val)}}</td>`;
        if (!isSource) return `<td class="cell-new">${{esc(val)}}</td>`;
      }}
      return `<td>${{esc(val)}}</td>`;
    }}).join('');
    return `<tr>${{cells}}</tr>`;
  }}).join('');
  return `<table class="block-table"><thead><tr>${{header}}</tr></thead><tbody>${{body}}</tbody></table>`;
}}

function renderSpan(sp) {{
  const lineRange = sp.line_start === sp.line_end ? sp.line_start : `${{sp.line_start}}–${{sp.line_end}}`;
  const diffLines =
    sp.lines_source.map(l => `<div class="diff-line diff-del"><span class="diff-marker">−</span><span class="diff-code">${{esc(l)}}</span></div>`).join('') +
    sp.lines_corrige.map(l => `<div class="diff-line diff-add"><span class="diff-marker">+</span><span class="diff-code">${{esc(l)}}</span></div>`).join('');
  const srcTable = renderBlockTable(sp.block_source, sp.old_id, sp.new_id, 'source');
  const corTable = renderBlockTable(sp.block_corrige, sp.old_id, sp.new_id, 'corrige');
  return `<div class="span-block">
    <div class="span-header">
      <span class="span-entity">${{esc(sp.entity_text)}}</span>
      <span class="span-ner">${{esc(sp.ner_type)}}</span>
      <span class="span-ids"><span class="id-old">${{esc(sp.old_id)}}</span> → <span class="id-new">${{esc(sp.new_id)}}</span></span>
      <span class="span-line">ligne ${{lineRange}}</span>
    </div>
    <div class="diff-block">${{diffLines}}</div>
    <div class="full-block">
      <div class="full-side"><div class="full-label">Original</div>${{srcTable}}</div>
      <div class="full-side"><div class="full-label">Corrigé</div>${{corTable}}</div>
    </div>
  </div>`;
}}

function renderPage(page) {{
  currentPage = page;
  const start = page * PAGE_SIZE;
  const pageSpans = allSpans.slice(start, start + PAGE_SIZE);

  // Regrouper par (old_id → new_id) en conservant l'ordre
  const sections = {{}};
  const sectionOrder = [];
  pageSpans.forEach(sp => {{
    const key = sp.old_id + '→' + sp.new_id;
    if (!sections[key]) {{ sections[key] = []; sectionOrder.push(key); }}
    sections[key].push(sp);
  }});

  let html = '';
  sectionOrder.forEach(key => {{
    const sps = sections[key];
    const [oldId, newId] = key.split('→');
    const changeType = oldId === '_' ? 'Nouvel ID assigné' : 'ID corrigé';
    html += `<section>
      <div class="section-header">
        <span class="change-type">${{changeType}}</span>
        <span style="font-family:monospace;font-size:13px;"><span class="id-old">${{esc(oldId)}}</span> → <span class="id-new">${{esc(newId)}}</span></span>
        <span class="change-count">${{sps.length}} entité(s) sur cette page</span>
      </div>
      ${{sps.map(renderSpan).join('')}}
    </section>`;
  }});

  document.getElementById('spans-container').innerHTML = html || '<section style="padding:20px;color:#9b9b97;">Aucune modification.</section>';
  renderPagination();
  window.scrollTo(0, 0);
}}

function renderPagination() {{
  const info = `<span class="page-info">Page ${{currentPage + 1}} / ${{totalPages}} — ${{allSpans.length}} entité(s) au total</span>`;
  ['pagination-top','pagination-bottom'].forEach(id => {{
    const el = document.getElementById(id);
    let html = `<button class="page-btn" onclick="renderPage(${{currentPage-1}})" ${{currentPage===0?'disabled':''}}>← Précédent</button>`;
    // Pages numérotées (max 10 visibles)
    const maxBtns = 10;
    let pStart = Math.max(0, currentPage - Math.floor(maxBtns/2));
    let pEnd = Math.min(totalPages, pStart + maxBtns);
    if (pEnd - pStart < maxBtns) pStart = Math.max(0, pEnd - maxBtns);
    for (let p = pStart; p < pEnd; p++) {{
      html += `<button class="page-btn ${{p===currentPage?'active':''}}" onclick="renderPage(${{p}})">${{p+1}}</button>`;
    }}
    html += `<button class="page-btn" onclick="renderPage(${{currentPage+1}})" ${{currentPage>=totalPages-1?'disabled':''}}>Suivant →</button>`;
    html += info;
    el.innerHTML = html;
  }});
}}

// Init
renderPage(0);
</script>
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
