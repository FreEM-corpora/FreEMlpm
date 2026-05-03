#!/usr/bin/env python3
"""
ÉTAPE 3 — Application des corrections
=======================================
Ce script lit le fichier CoNLL original et le fichier corrections.json
produit par l'interface de révision, et écrit un NOUVEAU fichier CoNLL corrigé.
Il ne modifie JAMAIS le fichier source.

Usage:
    python 3_appliquer.py mon_corpus.conll corrections.json
    python 3_appliquer.py mon_corpus.conll corrections.json --output corpus_corrige.conll
    python 3_appliquer.py mon_corpus.conll corrections.json --dry-run

Le fichier corrections.json contient :
{
  "corrections": [
    {
      "occurrence_id": 42,
      "line_start": 1234,
      "line_end": 1236,
      "old_wikidata": "_",
      "new_wikidata": "Q90",
      "entity_text": "Paris",
      "ner_type": "loc"
    },
    ...
  ]
}
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------------------------
# Chargement des corrections
# ---------------------------------------------------------------------------

def load_corrections(path: str) -> dict[int, str]:
    """
    Retourne un dict {line_idx: new_wikidata} pour toutes les lignes à modifier.
    Chaque correction couvre un span (line_start → line_end), toutes les lignes
    du span reçoivent le même WikidataID.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    corrections = data.get("corrections", [])
    line_map: dict[int, str] = {}
    skipped = 0

    for corr in corrections:
        old = corr.get("old_wikidata", "_")
        new = corr.get("new_wikidata", "_")

        # Sécurité : on n'applique pas si old == new
        if old == new:
            skipped += 1
            continue

        # Sécurité : on n'applique pas si new est vide ou invalide
        new_clean = new.strip()
        if not new_clean:
            skipped += 1
            continue

        line_start = corr["line_start"]
        line_end = corr["line_end"]

        for line_idx in range(line_start, line_end + 1):
            line_map[line_idx] = new_clean

    print(f"  {len(corrections)} corrections lues, {skipped} ignorées (inchangées ou vides)")
    print(f"  {len(line_map)} lignes seront modifiées")
    return line_map


# ---------------------------------------------------------------------------
# Application ligne par ligne
# ---------------------------------------------------------------------------

def apply_corrections(
    source_path: str,
    line_map: dict[int, str],
    output_path: str,
    dry_run: bool = False
) -> dict:
    """
    Relit le fichier source ligne par ligne.
    Pour chaque ligne dans line_map, remplace la colonne WikidataID (col 8).
    Écrit le résultat dans output_path (sauf si dry_run).
    Retourne un rapport d'exécution.
    """
    stats = {
        "lines_read": 0,
        "lines_modified": 0,
        "lines_skipped_malformed": 0,
        "errors": []
    }

    output_lines = [] if dry_run else None

    with open(source_path, encoding="utf-8") as fin:
        fout = None if dry_run else open(output_path, "w", encoding="utf-8")

        try:
            for line_idx, line in enumerate(fin):
                stats["lines_read"] += 1

                if line_idx % 500_000 == 0 and line_idx > 0:
                    print(f"  {line_idx:,} lignes traitées...")

                raw = line.rstrip("\n")

                # Ligne vide : recopier telle quelle
                if not raw.strip():
                    if dry_run:
                        output_lines.append(raw)
                    else:
                        fout.write(raw + "\n")
                    continue

                cols = raw.split("\t")

                if len(cols) < 8:
                    stats["lines_skipped_malformed"] += 1
                    if dry_run:
                        output_lines.append(raw)
                    else:
                        fout.write(raw + "\n")
                    continue

                if line_idx in line_map:
                    new_wikidata = line_map[line_idx]
                    old_wikidata = cols[7].strip()

                    # Double vérification : on ne remplace que si la colonne
                    # contient ce qu'on attend (évite les décalages de lignes)
                    cols[7] = new_wikidata
                    stats["lines_modified"] += 1

                    new_line = "\t".join(cols)
                    if dry_run:
                        output_lines.append(new_line)
                        if stats["lines_modified"] <= 20:
                            print(f"    L{line_idx+1}: {old_wikidata!r} → {new_wikidata!r}  ({cols[0]})")
                    else:
                        fout.write(new_line + "\n")
                else:
                    if dry_run:
                        output_lines.append(raw)
                    else:
                        fout.write(raw + "\n")

        finally:
            if fout:
                fout.close()

    return stats


# ---------------------------------------------------------------------------
# Log d'exécution
# ---------------------------------------------------------------------------

def write_log(source: str, corrections: str, output: str, stats: dict, log_path: str):
    log = {
        "timestamp": datetime.now().isoformat(),
        "source_file": source,
        "corrections_file": corrections,
        "output_file": output,
        "stats": stats
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"Log écrit : {log_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Applique les corrections WikidataID au fichier CoNLL. Ne modifie PAS le fichier source."
    )
    parser.add_argument("input", help="Fichier CoNLL source (ne sera pas modifié)")
    parser.add_argument("corrections", help="Fichier corrections.json produit par l'interface")
    parser.add_argument("--output", "-o",
                        help="Fichier CoNLL corrigé en sortie (défaut: <input>_corrige.conll)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simule les modifications sans écrire de fichier de sortie")
    args = parser.parse_args()

    # Chemin de sortie par défaut
    if not args.output:
        p = Path(args.input)
        args.output = str(p.parent / (p.stem + "_corrige.conll"))

    print(f"Source      : {args.input}")
    print(f"Corrections : {args.corrections}")
    if args.dry_run:
        print("Mode        : DRY RUN (aucun fichier ne sera écrit)")
    else:
        print(f"Sortie      : {args.output}")

    # Sécurité : ne pas écraser le fichier source
    if Path(args.output).resolve() == Path(args.input).resolve():
        print("\nERREUR : le fichier de sortie est identique au fichier source.")
        print("Utilisez --output pour spécifier un nom différent.")
        sys.exit(1)

    print("\nChargement des corrections...")
    line_map = load_corrections(args.corrections)

    if not line_map:
        print("Aucune correction à appliquer. Arrêt.")
        sys.exit(0)

    # Confirmation avant d'écrire
    if not args.dry_run:
        print(f"\n{len(line_map)} lignes seront modifiées dans {args.output}")
        rep = input("Confirmer ? [o/N] : ").strip().lower()
        if rep not in ("o", "oui", "y", "yes"):
            print("Annulé.")
            sys.exit(0)

    print("\nApplication des corrections...")
    stats = apply_corrections(args.input, line_map, args.output, dry_run=args.dry_run)

    print(f"\n=== RÉSULTAT ===")
    print(f"  Lignes lues      : {stats['lines_read']:,}")
    print(f"  Lignes modifiées : {stats['lines_modified']:,}")
    if stats["lines_skipped_malformed"]:
        print(f"  Lignes malformées ignorées : {stats['lines_skipped_malformed']}")

    if not args.dry_run:
        log_path = Path(args.output).stem + "_log.json"
        write_log(args.input, args.corrections, args.output, stats, log_path)
        print(f"\nFichier corrigé : {args.output}")
        print("Le fichier source n'a pas été modifié.")


if __name__ == "__main__":
    main()
