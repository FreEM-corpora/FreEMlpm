#!/usr/bin/env python3
"""
Compare une série de fichiers texte et repère les lignes qui apparaissent
plus d'une fois, que ce soit dans un même fichier ou réparties entre
plusieurs fichiers.

Résultat : un fichier listant chaque ligne dupliquée, avec le nombre
total d'occurrences et le détail par fichier.
"""

from collections import defaultdict
from pathlib import Path

# --- Configuration : à adapter -------------------------------------------

FICHIERS = [
    "noms.txt",
    "lieux.txt",
    "prenoms_antiques_bibliques.txt",
    "prenoms.txt",
    "patronymes.txt",
    "villes.txt",
    "pays.txt",
    "communes_francaises.txt",
    "fleuves.txt",
    "nombres.txt",
    "entites_plus.txt",
    "alphabet.txt",
    "authority_ajouts.txt",
    "acronymes.txt",
    "authority.tsv",
]

FICHIER_SORTIE = "doublons.txt"

IGNORER_LIGNES_VIDES = True

# ---------------------------------------------------------------------------


def lire_lignes(chemin):
    with open(chemin, encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.rstrip("\n")
            if IGNORER_LIGNES_VIDES and not ligne.strip():
                continue
            yield ligne


def main():
    # occurrences[ligne] = {nom_fichier: compte}
    occurrences = defaultdict(lambda: defaultdict(int))

    for chemin in FICHIERS:
        p = Path(chemin)
        if not p.exists():
            print(f"Attention : fichier introuvable, ignoré -> {chemin}")
            continue
        for ligne in lire_lignes(p):
            occurrences[ligne][p.name] += 1

    # On ne garde que les lignes dont le total d'occurrences dépasse 1
    doublons = {
        ligne: comptes
        for ligne, comptes in occurrences.items()
        if sum(comptes.values()) > 1
    }

    with open(FICHIER_SORTIE, "w", encoding="utf-8") as sortie:
        for ligne in sorted(doublons):
            comptes = doublons[ligne]
            total = sum(comptes.values())
            detail = ", ".join(f"{fichier} x{n}" for fichier, n in sorted(comptes.items()))
            sortie.write(f"{ligne}\t(total: {total})\t{detail}\n")

    print(f"{len(doublons)} ligne(s) dupliquée(s) trouvée(s) -> {FICHIER_SORTIE}")


if __name__ == "__main__":
    main()
