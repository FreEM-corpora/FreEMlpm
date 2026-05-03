#!/usr/bin/env python3
"""
CoNLL Wikidata Checker
Vérifie et complète les WikidataIDs dans un fichier d'annotation CoNLL.

Usage:
    python conll_wikidata_checker.py input.conll
    python conll_wikidata_checker.py input.conll --output corrige.conll
    python conll_wikidata_checker.py input.conll --verify-only
    python conll_wikidata_checker.py input.conll --interactive
"""

import sys
import time
import argparse
import urllib.request
import urllib.parse
import json
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Structures de données
# ---------------------------------------------------------------------------

@dataclass
class Token:
    line_idx: int
    token: str
    lemma: str
    pos: str
    ner1: str
    ner2: str
    ner3: str
    ner4: str
    wikidata: str  # '_' si absent

    def to_line(self) -> str:
        return "\t".join([
            self.token, self.lemma, self.pos,
            self.ner1, self.ner2, self.ner3, self.ner4,
            self.wikidata
        ])


@dataclass
class Entity:
    text: str
    lemma: str
    ner_type: str
    wikidata: str
    token_indices: list[int]
    verified: Optional[bool] = None
    verified_label: str = ""
    suggestions: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing CoNLL
# ---------------------------------------------------------------------------

def parse_conll(path: str) -> tuple[list[Token], list[Entity]]:
    tokens: list[Token] = []
    entities: list[Entity] = []
    current: Optional[Entity] = None

    with open(path, encoding="utf-8") as f:
        for line_idx, line in enumerate(f):
            line = line.rstrip("\n")
            if not line.strip():
                if current:
                    entities.append(current)
                    current = None
                tokens.append(Token(line_idx, "", "", "", "", "", "", "", ""))
                continue

            cols = line.split("\t")
            if len(cols) < 8:
                print(f"  [WARN] ligne {line_idx+1} ignorée (colonnes insuffisantes) : {line!r}")
                continue

            tok = Token(
                line_idx=line_idx,
                token=cols[0], lemma=cols[1], pos=cols[2],
                ner1=cols[3], ner2=cols[4], ner3=cols[5], ner4=cols[6],
                wikidata=cols[7].strip()
            )
            tokens.append(tok)

            # Extraction des spans d'entités à partir de ner1 (ou ner2)
            tag = tok.ner1 if tok.ner1 != "O" else (tok.ner2 if tok.ner2 != "O" else "O")

            if tag.startswith("B-"):
                if current:
                    entities.append(current)
                ner_type = tag[2:]
                wikidata = tok.wikidata if tok.wikidata != "_" else ""
                current = Entity(
                    text=tok.token,
                    lemma=tok.lemma,
                    ner_type=ner_type,
                    wikidata=wikidata,
                    token_indices=[len(tokens) - 1]
                )
            elif tag.startswith("I-") and current:
                current.text += " " + tok.token
                current.token_indices.append(len(tokens) - 1)
                if tok.wikidata != "_" and not current.wikidata:
                    current.wikidata = tok.wikidata
            else:
                if current:
                    entities.append(current)
                    current = None

    if current:
        entities.append(current)

    return tokens, entities


# ---------------------------------------------------------------------------
# API Wikidata
# ---------------------------------------------------------------------------

WIKIDATA_SEARCH_URL = "https://www.wikidata.org/w/api.php"
WIKIDATA_ENTITY_URL = "https://www.wikidata.org/w/api.php"


def wikidata_search(query: str, lang: str = "fr", limit: int = 5) -> list[dict]:
    params = urllib.parse.urlencode({
        "action": "wbsearchentities",
        "search": query,
        "language": lang,
        "limit": limit,
        "format": "json"
    })
    url = f"{WIKIDATA_SEARCH_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CoNLL-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data.get("search", [])
    except Exception as e:
        print(f"    [ERREUR réseau] {e}")
        return []


def wikidata_verify(qid: str) -> tuple[bool, str]:
    """Vérifie qu'un QID existe et retourne (valide, label_fr)."""
    params = urllib.parse.urlencode({
        "action": "wbgetentities",
        "ids": qid,
        "props": "labels",
        "languages": "fr|en",
        "format": "json"
    })
    url = f"{WIKIDATA_ENTITY_URL}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CoNLL-Checker/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        entity = data.get("entities", {}).get(qid, {})
        if entity.get("missing"):
            return False, ""
        labels = entity.get("labels", {})
        label = labels.get("fr", {}).get("value") or labels.get("en", {}).get("value") or qid
        return True, label
    except Exception as e:
        print(f"    [ERREUR réseau] {e}")
        return False, ""


# ---------------------------------------------------------------------------
# Application des corrections aux tokens
# ---------------------------------------------------------------------------

def apply_entity_wikidata(tokens: list[Token], entity: Entity):
    """Propage le WikidataID de l'entité à tous ses tokens."""
    val = entity.wikidata if entity.wikidata else "_"
    for i in entity.token_indices:
        tokens[i].wikidata = val


# ---------------------------------------------------------------------------
# Modes d'exécution
# ---------------------------------------------------------------------------

def run_verify_only(tokens: list[Token], entities: list[Entity]):
    """Vérifie les IDs existants et affiche un rapport."""
    print("\n=== VÉRIFICATION DES WIKIDATAIDS EXISTANTS ===\n")
    with_id = [e for e in entities if e.wikidata]
    without_id = [e for e in entities if not e.wikidata]

    print(f"Entités totales       : {len(entities)}")
    print(f"Avec WikidataID       : {len(with_id)}")
    print(f"Sans WikidataID       : {len(without_id)}\n")

    if not with_id:
        print("Aucun ID à vérifier.")
        return

    print("Vérification en cours...\n")
    ok, ko = 0, 0
    for ent in with_id:
        valid, label = wikidata_verify(ent.wikidata)
        if valid:
            ok += 1
            print(f"  [OK]  {ent.text!r:30s}  {ent.wikidata}  →  {label}")
            ent.verified = True
            ent.verified_label = label
        else:
            ko += 1
            print(f"  [KO]  {ent.text!r:30s}  {ent.wikidata}  →  ID INVALIDE")
            ent.verified = False
        time.sleep(0.2)

    print(f"\nRésultat : {ok} valides, {ko} invalides")

    if ko > 0:
        print("\n--- Entités avec ID invalide ---")
        for ent in with_id:
            if ent.verified is False:
                results = wikidata_search(ent.text)
                if results:
                    print(f"\n  {ent.text!r} ({ent.ner_type})")
                    for r in results[:3]:
                        print(f"    {r['id']:12s}  {r.get('label','')}  —  {r.get('description','')[:60]}")


def run_auto(tokens: list[Token], entities: list[Entity]):
    """Recherche automatique pour les entités sans ID."""
    print("\n=== RECHERCHE AUTOMATIQUE WIKIDATA ===\n")
    missing = [e for e in entities if not e.wikidata]
    print(f"{len(missing)} entités sans WikidataID\n")

    for ent in missing:
        print(f"  Recherche : {ent.text!r} ({ent.ner_type})")
        results = wikidata_search(ent.text)
        if results:
            best = results[0]
            ent.suggestions = results[:3]
            print(f"    → Suggestion : {best['id']}  {best.get('label','')}  —  {best.get('description','')[:60]}")
        else:
            print("    → Aucune suggestion.")
        time.sleep(0.2)


def run_interactive(tokens: list[Token], entities: list[Entity]):
    """Mode interactif : l'utilisateur valide ou corrige chaque entité."""
    print("\n=== MODE INTERACTIF ===")
    print("Pour chaque entité, appuyez sur Entrée pour accepter, tapez un QID pour corriger,")
    print("ou tapez 's' pour ignorer, 'q' pour quitter.\n")

    for ent in entities:
        print(f"\n  Entité : {ent.text!r}  [{ent.ner_type}]")

        if ent.wikidata:
            valid, label = wikidata_verify(ent.wikidata)
            if valid:
                print(f"  ID actuel : {ent.wikidata}  →  {label}  [VALIDE]")
                rep = input("  Conserver ? [Entrée=oui / nouveau QID / s=ignorer / q=quitter] : ").strip()
            else:
                print(f"  ID actuel : {ent.wikidata}  [INVALIDE]")
                results = wikidata_search(ent.text)
                if results:
                    print("  Suggestions :")
                    for i, r in enumerate(results[:5]):
                        print(f"    {i+1}. {r['id']:12s}  {r.get('label','')}  —  {r.get('description','')[:60]}")
                rep = input("  Nouveau QID (ou numéro suggestion) / s / q : ").strip()
        else:
            print("  Pas de WikidataID.")
            results = wikidata_search(ent.text)
            if results:
                print("  Suggestions :")
                for i, r in enumerate(results[:5]):
                    print(f"    {i+1}. {r['id']:12s}  {r.get('label','')}  —  {r.get('description','')[:60]}")
                rep = input("  Choisir un QID (ou numéro) / s=ignorer / q=quitter : ").strip()
            else:
                print("  Aucune suggestion automatique.")
                rep = input("  Saisir un QID manuellement / s=ignorer / q=quitter : ").strip()
            results = results if 'results' in dir() else []

        if rep.lower() == 'q':
            print("Interruption.")
            break
        elif rep.lower() == 's' or rep == '':
            pass
        elif rep.isdigit() and 1 <= int(rep) <= len(results):
            chosen = results[int(rep)-1]
            ent.wikidata = chosen['id']
            print(f"  → {chosen['id']} sélectionné.")
        elif rep.upper().startswith('Q') and rep[1:].isdigit():
            ent.wikidata = rep.upper()
            print(f"  → {ent.wikidata} appliqué.")

        apply_entity_wikidata(tokens, ent)
        time.sleep(0.1)


# ---------------------------------------------------------------------------
# Rapport et export
# ---------------------------------------------------------------------------

def print_report(entities: list[Entity]):
    print("\n=== RAPPORT FINAL ===\n")
    for ent in entities:
        status = ""
        if ent.verified is True:
            status = f"[OK: {ent.verified_label}]"
        elif ent.verified is False:
            status = "[INVALIDE]"
        elif ent.wikidata:
            status = "[non vérifié]"
        else:
            status = "[sans ID]"
        print(f"  {ent.text!r:35s}  {ent.ner_type:20s}  {ent.wikidata or '—':12s}  {status}")


def write_conll(tokens: list[Token], output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        for tok in tokens:
            if tok.token == "":
                f.write("\n")
            else:
                f.write(tok.to_line() + "\n")
    print(f"\nFichier écrit : {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Vérificateur CoNLL/Wikidata")
    parser.add_argument("input", help="Fichier CoNLL en entrée")
    parser.add_argument("--output", "-o", help="Fichier CoNLL corrigé en sortie")
    parser.add_argument("--verify-only", action="store_true",
                        help="Vérifie les IDs existants sans modifier le fichier")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Mode interactif : valider/corriger entité par entité")
    parser.add_argument("--auto", "-a", action="store_true",
                        help="Suggestion automatique pour les entités sans ID (sans modifier)")
    args = parser.parse_args()

    print(f"Lecture de {args.input}...")
    tokens, entities = parse_conll(args.input)
    print(f"  {len(tokens)} tokens, {len(entities)} entités extraites.")

    if args.verify_only:
        run_verify_only(tokens, entities)
    elif args.interactive:
        run_verify_only(tokens, entities)
        run_interactive(tokens, entities)
        print_report(entities)
    elif args.auto:
        run_verify_only(tokens, entities)
        run_auto(tokens, entities)
        print_report(entities)
    else:
        # Par défaut : vérification + suggestions automatiques
        run_verify_only(tokens, entities)
        run_auto(tokens, entities)
        print_report(entities)

    if args.output and not args.verify_only:
        for ent in entities:
            apply_entity_wikidata(tokens, ent)
        write_conll(tokens, args.output)


if __name__ == "__main__":
    main()
