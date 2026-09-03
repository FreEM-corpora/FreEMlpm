#!/usr/bin/env python3
"""
Nettoie une série de fichiers texte selon deux règles :

1. Si une ligne apparaît plusieurs fois dans un MEME fichier, on ne garde
   qu'une seule occurrence (déduplication interne).

2. Certains fichiers sont "prioritaires", regroupés par thème :
   - noms   : prenoms_antiques_bibliques.txt, patronymes.txt, prenoms.txt
              -> priment sur noms.txt
   - lieux  : fleuves.txt, communes_francaises.txt, pays.txt
              -> priment sur lieux.txt
   Si une ligne présente dans un fichier prioritaire d'un groupe se
   retrouve aussi dans le fichier secondaire du même groupe, on supprime
   cette ligne du fichier secondaire (on la garde uniquement dans le
   fichier prioritaire).

Avant toute modification, une sauvegarde zip horodatée de tous les
fichiers concernés est créée dans le dossier BACKUP_DIR.
"""

import shutil
import zipfile
from datetime import datetime
from pathlib import Path

# --- Configuration : à adapter -------------------------------------------

# Chaque règle définit un groupe de fichiers prioritaires et le fichier
# secondaire dont ils doivent faire disparaître les doublons.
REGLES_PRIORITE = [
    {
        "prioritaires": [
            "prenoms_antiques_bibliques.txt",
            "patronymes.txt",
            "prenoms.txt",
        ],
        "secondaire": "noms.txt",
    },
    {
        "prioritaires": [
            "fleuves.txt",
            "communes_francaises.txt",
            "pays.txt",
        ],
        "secondaire": "lieux.txt",
    },
]

# Autres fichiers de la série, sur lesquels on applique quand même
# la règle 1 (déduplication interne), mais pas la règle 2.
AUTRES_FICHIERS = [
    "nombres.txt",
    "entites_plus.txt",
    "alphabet.txt",
    "authority_ajouts.txt",
    "acronymes.txt",
    "authority.tsv",
]

# Liste complète et dédupliquée de tous les fichiers concernés
TOUS_LES_FICHIERS = list(
    dict.fromkeys(
        [f for regle in REGLES_PRIORITE for f in regle["prioritaires"]]
        + [regle["secondaire"] for regle in REGLES_PRIORITE]
        + AUTRES_FICHIERS
    )
)

BACKUP_DIR = Path("backups")

# ---------------------------------------------------------------------------


def sauvegarder(fichiers):
    """Crée un zip horodaté de tous les fichiers existants avant modification."""
    BACKUP_DIR.mkdir(exist_ok=True)
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin_zip = BACKUP_DIR / f"backup_{horodatage}.zip"

    with zipfile.ZipFile(chemin_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for chemin in fichiers:
            p = Path(chemin)
            if p.exists():
                z.write(p, arcname=p.name)

    print(f"Sauvegarde créée -> {chemin_zip}")
    return chemin_zip


def lire_lignes(chemin):
    with open(chemin, encoding="utf-8") as f:
        return [ligne.rstrip("\n") for ligne in f]


def ecrire_lignes(chemin, lignes):
    with open(chemin, "w", encoding="utf-8") as f:
        for ligne in lignes:
            f.write(ligne + "\n")


def dedupliquer_interne(lignes, nom_fichier):
    """Règle 1 : supprime les doublons internes, en conservant l'ordre
    d'apparition. Affiche chaque ligne supprimée."""
    vues = set()
    resultat = []
    for ligne in lignes:
        if ligne in vues:
            print(f"  {nom_fichier} : doublon interne supprimé -> {ligne!r}")
            continue
        vues.add(ligne)
        resultat.append(ligne)
    return resultat


def main():
    # On ne travaille que sur les fichiers qui existent réellement
    fichiers_presents = [f for f in TOUS_LES_FICHIERS if Path(f).exists()]
    manquants = [f for f in TOUS_LES_FICHIERS if f not in fichiers_presents]
    if manquants:
        print("Fichiers absents (ignorés) :", ", ".join(manquants))

    # --- Sauvegarde avant toute manipulation ---
    sauvegarder(fichiers_presents)

    # --- Étape 1 : déduplication interne de chaque fichier ---
    print("\n--- Étape 1 : doublons internes ---")
    contenu = {}
    for chemin in fichiers_presents:
        lignes = lire_lignes(chemin)
        lignes_dedupliquees = dedupliquer_interne(lignes, chemin)
        nb_supprime = len(lignes) - len(lignes_dedupliquees)
        if nb_supprime:
            print(f"{chemin} : {nb_supprime} doublon(s) interne(s) supprimé(s) au total")
        contenu[chemin] = lignes_dedupliquees

    # --- Étape 2 : priorité des fichiers prioritaires sur les secondaires ---
    print("\n--- Étape 2 : priorité des fichiers prioritaires ---")

    for regle in REGLES_PRIORITE:
        secondaire = regle["secondaire"]
        if secondaire not in contenu:
            continue

        # On garde trace de quel fichier prioritaire contient chaque ligne,
        # pour pouvoir l'afficher dans le détail.
        source_prioritaire = {}
        for chemin in regle["prioritaires"]:
            if chemin in contenu:
                for ligne in contenu[chemin]:
                    source_prioritaire.setdefault(ligne, chemin)

        nouvelles_lignes = []
        nb_supprime = 0
        for ligne in contenu[secondaire]:
            if ligne in source_prioritaire:
                print(f"  {secondaire} : {ligne!r} supprimée (déjà dans {source_prioritaire[ligne]})")
                nb_supprime += 1
            else:
                nouvelles_lignes.append(ligne)
        contenu[secondaire] = nouvelles_lignes
        if nb_supprime:
            print(f"{secondaire} : {nb_supprime} ligne(s) supprimée(s) au total")

    # --- Écriture des fichiers nettoyés ---
    for chemin, lignes in contenu.items():
        ecrire_lignes(chemin, lignes)

    print("Nettoyage terminé.")


if __name__ == "__main__":
    main()
