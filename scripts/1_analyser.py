#!/usr/bin/env python3
"""
ÉTAPE 1 — Analyse du fichier CoNLL
===================================
Ce script LIT le fichier CoNLL et produit un rapport JSON.
Il ne modifie JAMAIS le fichier source.

Usage:
    python 1_analyser.py mon_corpus.conll
    python 1_analyser.py mon_corpus.conll --rapport rapport.json

Sortie:
    rapport.json  — toutes les entités groupées avec leurs contextes
"""

import sys
import json
import argparse
import re
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Structures
# ---------------------------------------------------------------------------

@dataclass
class Occurrence:
    """Une occurrence d'une entité dans le texte, avec son contexte."""
    occurrence_id: int          # Identifiant unique de cette occurrence
    line_start: int             # Ligne de début dans le fichier (0-indexé)
    line_end: int               # Ligne de fin dans le fichier
    token_text: str             # Texte brut de l'entité (ex: "Dijon")
    context_before: str         # Phrase ou contexte avant l'entité
    context_after: str          # Phrase ou contexte après
    current_wikidata: str       # ID actuel ('_' si absent)
    ner1: str
    ner2: str


@dataclass
class EntityGroup:
    """Groupe d'occurrences partageant le même texte normalisé + type NER."""
    group_id: str               # Ex: "Paris__loc"
    text_normalized: str        # Texte en minuscules pour regrouper
    text_display: str           # Texte tel qu'il apparaît (première occurrence)
    ner_type: str
    occurrences: list[Occurrence] = field(default_factory=list)
    existing_ids: dict = field(default_factory=dict)   # {qid: count}
    status: str = "à traiter"  # à traiter | vérifié | ignoré


# ---------------------------------------------------------------------------
# Parsing CoNLL
# ---------------------------------------------------------------------------

def extract_sentence_bounds(tokens_flat: list[dict], token_idx: int) -> tuple[int, int]:
    """
    À partir d'un index de token, trouve les bornes de la phrase
    en cherchant la ponctuation de fin (. ? ! ;) de chaque côté.
    Retourne (start, end) en indices dans tokens_flat.
    """
    PUNCT_END = {".", "?", "!", ";"}

    # Cherche vers la gauche
    start = token_idx
    for i in range(token_idx - 1, -1, -1):
        t = tokens_flat[i]["token"]
        if t in PUNCT_END:
            start = i + 1
            break
        if i == 0:
            start = 0

    # Cherche vers la droite
    end = token_idx
    for i in range(token_idx + 1, len(tokens_flat)):
        t = tokens_flat[i]["token"]
        if t in PUNCT_END:
            end = i
            break
        if i == len(tokens_flat) - 1:
            end = i

    return start, end


def tokens_to_text(tokens_flat: list[dict], start: int, end: int,
                   highlight_start: int = -1, highlight_end: int = -1) -> tuple[str, str, str]:
    """
    Reconstruit le texte d'une plage de tokens.
    Retourne (context_before, entity_text, context_after).
    """
    ATTACHED_LEFT = {".", ",", ")", "]", "}", ":", ";", "!", "?", "'", "\u2019", "»"}
    ATTACHED_RIGHT = {"(", "[", "{", "\u00ab", "'", "\u2018"}

    def join_tokens(toks):
        result = ""
        for i, t in enumerate(toks):
            tok = t["token"]
            if i == 0:
                result = tok
            elif tok in ATTACHED_LEFT or result.endswith(("'", "\u2019", "-")):
                result += tok
            elif tok.startswith("-") or tok.startswith("'"):
                result += tok
            else:
                result += " " + tok
        return result

    before_toks = tokens_flat[start:highlight_start] if highlight_start >= 0 else []
    entity_toks = tokens_flat[highlight_start:highlight_end + 1] if highlight_start >= 0 else []
    after_toks  = tokens_flat[highlight_end + 1:end + 1] if highlight_start >= 0 else []

    return join_tokens(before_toks), join_tokens(entity_toks), join_tokens(after_toks)


def parse_conll(path: str) -> tuple[list[dict], list[dict]]:
    """
    Parse le fichier CoNLL ligne par ligne.
    Retourne (tokens_flat, raw_entities).
    tokens_flat : liste de dicts {token, lemma, pos, ner1, ner2, ner3, ner4, wikidata, line_idx}
    raw_entities : liste de dicts {tokens_indices, text, ner_type, wikidata, line_start, line_end}
    """
    tokens_flat = []
    raw_entities = []
    current_entity = None
    occ_id_counter = 0

    print(f"Lecture de {path}...")

    with open(path, encoding="utf-8") as f:
        for line_idx, line in enumerate(f):
            if line_idx % 500_000 == 0 and line_idx > 0:
                print(f"  {line_idx:,} lignes lues...")

            line = line.rstrip("\n")

            # Ligne vide = séparateur de phrase
            if not line.strip():
                if current_entity:
                    raw_entities.append(current_entity)
                    current_entity = None
                tokens_flat.append({
                    "token": ".", "lemma": "", "pos": "SENT",
                    "ner1": "O", "ner2": "O", "ner3": "O", "ner4": "O",
                    "wikidata": "_", "line_idx": line_idx, "is_separator": True
                })
                continue

            cols = line.split("\t")
            if len(cols) < 8:
                continue

            tok = {
                "token": cols[0], "lemma": cols[1], "pos": cols[2],
                "ner1": cols[3], "ner2": cols[4], "ner3": cols[5], "ner4": cols[6],
                "wikidata": cols[7].strip(),
                "line_idx": line_idx,
                "is_separator": False
            }
            flat_idx = len(tokens_flat)
            tokens_flat.append(tok)

            # Détection des spans B-/I-
            tag = tok["ner1"] if tok["ner1"] != "O" else (tok["ner2"] if tok["ner2"] != "O" else "O")

            if tag.startswith("B-"):
                if current_entity:
                    raw_entities.append(current_entity)
                ner_type = tag[2:]
                wikidata = tok["wikidata"] if tok["wikidata"] != "_" else ""
                current_entity = {
                    "occ_id": occ_id_counter,
                    "flat_indices": [flat_idx],
                    "text": tok["token"],
                    "ner_type": ner_type,
                    "wikidata": wikidata,
                    "line_start": line_idx,
                    "line_end": line_idx,
                    "ner1": tok["ner1"],
                    "ner2": tok["ner2"],
                }
                occ_id_counter += 1

            elif tag.startswith("I-") and current_entity:
                current_entity["flat_indices"].append(flat_idx)
                current_entity["text"] += " " + tok["token"]
                current_entity["line_end"] = line_idx
                if tok["wikidata"] != "_" and not current_entity["wikidata"]:
                    current_entity["wikidata"] = tok["wikidata"]

            else:
                if current_entity:
                    raw_entities.append(current_entity)
                    current_entity = None

    if current_entity:
        raw_entities.append(current_entity)

    print(f"  Terminé : {len(tokens_flat):,} tokens, {len(raw_entities):,} entités brutes")
    return tokens_flat, raw_entities


# ---------------------------------------------------------------------------
# Construction des groupes
# ---------------------------------------------------------------------------

# Types d'entités sans intérêt pour l'annotation Wikidata (jamais d'ID)
TYPES_SANS_ID = {"time", "amount"}


def build_groups(tokens_flat: list[dict], raw_entities: list[dict]) -> list[EntityGroup]:
    """
    Regroupe les entités par (texte normalisé + type NER + ID existant).

    La clé de regroupement inclut l'ID Wikidata existant, ce qui garantit que :
      - "Paris" avec Q90     → groupe "paris__loc__Q90"
      - "Paris" avec Q830149 → groupe "paris__loc__Q830149"
      - "Paris" sans ID      → groupe "paris__loc___"
    Cela évite tout écrasement silencieux d'un ID par un autre lors de la validation.

    Les types dans TYPES_SANS_ID sans aucun ID sont ignorés (time, amount…).
    """
    print("Construction des groupes et extraction des contextes...")
    groups: dict[str, EntityGroup] = {}
    skipped_types = 0

    for i, ent in enumerate(raw_entities):
        if i % 10_000 == 0 and i > 0:
            print(f"  {i:,} / {len(raw_entities):,} entités traitées...")

        ner_type = ent["ner_type"]
        wikidata = ent["wikidata"] or ""

        # Ignorer les types sans intérêt s'ils n'ont pas d'ID
        base_type = ner_type.split(".")[0].lower()
        if base_type in TYPES_SANS_ID and not wikidata:
            skipped_types += 1
            continue

        text_norm = ent["text"].lower().strip()

        # La clé inclut l'ID pour séparer les occurrences ambiguës
        id_key = wikidata if wikidata else "_"
        group_key = f"{text_norm}__{ner_type}__{id_key}"

        if group_key not in groups:
            # Label lisible pour l'interface
            display_id = f" [{wikidata}]" if wikidata else " [sans ID]"
            groups[group_key] = EntityGroup(
                group_id=group_key,
                text_normalized=text_norm,
                text_display=ent["text"],
                ner_type=ner_type,
            )
            if wikidata:
                groups[group_key].existing_ids[wikidata] = 0  # sera incrémenté ci-dessous

        grp = groups[group_key]

        # Contexte : phrase complète autour du premier token de l'entité
        first_flat = ent["flat_indices"][0]
        last_flat  = ent["flat_indices"][-1]
        sent_start, sent_end = extract_sentence_bounds(tokens_flat, first_flat)

        ctx_before, entity_text, ctx_after = tokens_to_text(
            tokens_flat, sent_start, sent_end, first_flat, last_flat
        )

        occ = Occurrence(
            occurrence_id=ent["occ_id"],
            line_start=ent["line_start"],
            line_end=ent["line_end"],
            token_text=ent["text"],
            context_before=ctx_before,
            context_after=ctx_after,
            current_wikidata=id_key,
            ner1=ent["ner1"],
            ner2=ent["ner2"],
        )
        grp.occurrences.append(occ)

        # Comptage des IDs existants
        if wikidata:
            grp.existing_ids[wikidata] = grp.existing_ids.get(wikidata, 0) + 1

    groups_list = sorted(groups.values(), key=lambda g: -len(g.occurrences))

    print(f"  {len(groups_list):,} groupes distincts construits")
    if skipped_types:
        print(f"  {skipped_types:,} occurrences ignorées (types sans ID : time, amount…)")

    return groups_list


# ---------------------------------------------------------------------------
# Rapport JSON
# ---------------------------------------------------------------------------

import hashlib

def write_rapport(groups: list[EntityGroup], output_path: str, source_file: str):
    """Écrit le rapport JSON. Structure claire, lisible, rechargeable."""
    total_occ = sum(len(g.occurrences) for g in groups)
    rapport_id = hashlib.md5(
        f"{source_file}|{len(groups)}|{total_occ}".encode()
    ).hexdigest()[:12]

    data = {
        "meta": {
            "source_file": source_file,
            "rapport_id": rapport_id,
            "total_groups": len(groups),
            "total_occurrences": total_occ,
            "groups_with_id": sum(1 for g in groups if g.existing_ids),
            "groups_without_id": sum(1 for g in groups if not g.existing_ids),
            "note": (
                "Chaque groupe est homogène : même texte + même type NER + même ID existant. "
                "Un texte ambigu (ex: Paris Q90 vs Paris Q830149) génère plusieurs groupes distincts."
            )
        },
        "groups": []
    }

    for g in groups:
        data["groups"].append({
            "group_id": g.group_id,
            "text_display": g.text_display,
            "ner_type": g.ner_type,
            "total_occurrences": len(g.occurrences),
            "existing_ids": g.existing_ids,
            "status": g.status,
            "occurrences": [asdict(occ) for occ in g.occurrences]
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nRapport écrit : {output_path}")
    print(f"  Groupes totaux       : {data['meta']['total_groups']:,}")
    print(f"  Occurrences totales  : {data['meta']['total_occurrences']:,}")
    print(f"  Groupes avec ID      : {data['meta']['groups_with_id']:,}")
    print(f"  Groupes sans ID      : {data['meta']['groups_without_id']:,}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Analyse un fichier CoNLL et produit un rapport JSON. Ne modifie PAS le fichier source."
    )
    parser.add_argument("input", help="Fichier CoNLL source (ne sera pas modifié)")
    parser.add_argument("--rapport", "-r", default="rapport.json",
                        help="Fichier JSON de sortie (défaut: rapport.json)")
    args = parser.parse_args()

    tokens_flat, raw_entities = parse_conll(args.input)
    groups = build_groups(tokens_flat, raw_entities)
    write_rapport(groups, args.rapport, args.input)

    print("\nProchaine étape :")
    print("  Ouvre l'interface web (2_reviser.html) et charge le fichier rapport.json")


if __name__ == "__main__":
    main()
