#!/usr/bin/env python3
"""
Appli web locale pour contrôler et corriger les lemmes, mot par mot.

Principe :
- Les fichiers du dossier Data sont des TSV dont la 2e colonne (index 1)
  est le lemme.
- Les fichiers du dossier Authority_list contiennent chacun un lemme
  valide par ligne.
- L'appli repère toutes les occurrences de lemmes qui ne figurent dans
  aucun fichier Authority_list.
- Un bandeau à gauche liste les lemmes problématiques (avec leur nombre
  d'occurrences) : on choisit soi-même lequel traiter en premier.
- Pour le lemme choisi, on traite les occurrences UNE PAR UNE (pas de
  correction en lot) : le mot et son lemme actuel sont affichés avec son
  contexte (20 mots avant / 20 mots après), les lemmes les plus proches
  trouvés dans Authority_list sont proposés en boutons, ou on peut saisir
  le bon lemme à la main. La correction ne s'applique qu'à cette seule
  occurrence.

Avant toute modification, une sauvegarde zip horodatée des fichiers Data
est créée dans BACKUP_DIR.

Lancement :
    pip install flask
    python3 app_correction_lemmes.py
puis ouvrir http://127.0.0.1:5000 dans le navigateur.
"""

import difflib
import zipfile
from collections import deque
from datetime import datetime
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, url_for

# --- Configuration : à adapter -------------------------------------------


DATA_FILES = [
    "../Data/cornMol/cornmol_gold_v2.tsv",
    "../Data/frantext_oa/K639.xml.tab",
    "../Data/frantext_oa/L499.xml.tab",
    "../Data/frantext_oa/M374.xml.tab",
    "../Data/frantext_oa/M528.xml.tab",
    "../Data/frantext_oa/N268.xml.tab",
    "../Data/frantext_oa/K934.xml.tab",
    "../Data/frantext_oa/L784.xml.tab",
    "../Data/frantext_oa/M425.xml.tab",
    "../Data/frantext_oa/M548.xml.tab",
    "../Data/frantext_oa/N429.xml.tab",
    "../Data/frantext_oa/K999.xml.tab",
    "../Data/frantext_oa/L846.xml.tab",
    "../Data/frantext_oa/M433.xml.tab",
    "../Data/frantext_oa/M622.xml.tab",
    "../Data/frantext_oa/P556.xml.tab",
    "../Data/frantext_oa/L233.xml.tab",
    "../Data/frantext_oa/L884.xml.tab",
    "../Data/frantext_oa/M464.xml.tab",
    "../Data/frantext_oa/M629.xml.tab",
    "../Data/frantext_oa/Q454.xml.tab",
    "../Data/frantext_oa/L266.xml.tab",
    "../Data/frantext_oa/M223.xml.tab",
    "../Data/frantext_oa/M468.xml.tab",
    "../Data/frantext_oa/M893.xml.tab",
    "../Data/frantext_oa/L433.xml.tab",
    "../Data/frantext_oa/M289.xml.tab",
    "../Data/frantext_oa/M473.xml.tab",
    "../Data/frantext_oa/M939.xml.tab",
    "../Data/frantext_oa/L486.xml.tab",
    "../Data/frantext_oa/M362.xml.tab",
    "../Data/frantext_oa/M492.xml.tab",
    "../Data/frantext_oa/N245.xml.tab",
    "../Data/Gallicorpora/gallicorpora-15-bpt6k10516302.tsv",
    "../Data/Gallicorpora/gallicorpora-16-bpt6k724151.tsv",
    "../Data/Gallicorpora/gallicorpora-15-bpt6k1057726c.tsv",
    "../Data/Gallicorpora/gallicorpora-17-bpt6k1513919s.tsv",
    "../Data/Gallicorpora/gallicorpora-16-bpt6k990549b.tsv",
    "../Data/Gallicorpora/gallicorpora-17-bpt6k6424218b.tsv",
    "../Data/Gallicorpora/gallicorpora-15-bpt6k1057722.tsv",
    "../Data/Gallicorpora/gallicorpora-17-bpt6k6509381p.tsv",
    "../Data/Gallicorpora/gallicorpora-15-btv1b55008562q.tsv",
    "../Data/Gallicorpora/gallicorpora-17-bpt6k6551882q.tsv",
    "../Data/Gallicorpora/gallicorpora-15-btv1b8600143n.tsv",
    "../Data/Gallicorpora/gallicorpora-18-bpt6k15120824.tsv",
    "../Data/Gallicorpora/gallicorpora-15-btv1b8626779r.tsv",
    "../Data/Gallicorpora/gallicorpora-18-bpt6k6495917k.tsv",
    "../Data/Gallicorpora/gallicorpora-16-bpt6k15260973.tsv",
    "../Data/Gallicorpora/gallicorpora-18-btv1b8613380t.tsv",
    "../Data/Gallicorpora/gallicorpora-16-bpt6k3041989v.tsv",
    "../Data/Gallicorpora/gallicorpora-18-btv1b86146004.tsv",
    "../Data/presto_gold/presto_gold_v2.tsv",
    "../Data/presto_max/presto_max_v7.1.txt"
    "../Data/setaf/CRRPV04_Grans_pardons_et_indulgences_gold.tsv",
    "../Data/setaf/CRRPV08_Livre_des_marchans_gold.tsv",
    "../Data/setaf/CRRPV09_Maniere_et_fasson_gold.tsv",
    "../Data/setaf/CRRPV16_Chansons_nouvelles_gold.tsv",
    "../Data/setaf/CRRPV19_Faictz_gold.tsv",
    "../Data/setaf/CRRPV22_Declaration_de_la_messe_gold.tsv",
    "../Data/setaf/CRRPV23_Summaire_et_briefve_declaration_gold.tsv",
    "../Data/setaf/CRRPV25_Letres_certaines_gold.tsv",
]

AUTHORITY_FILES = [
    "../Authority_list/noms.txt",
    "../Authority_list/lieux.txt",
    "../Authority_list/prenoms_antiques_bibliques.txt",
    "../Authority_list/prenoms.txt",
    "../Authority_list/patronymes.txt",
    "../Authority_list/villes.txt",
    "../Authority_list/pays.txt",
    "../Authority_list/communes_francaises.txt",
    "../Authority_list/fleuves.txt",
    "../Authority_list/nombres.txt",
    "../Authority_list/entites_plus.txt",
    "../Authority_list/alphabet.txt",
    "../Authority_list/authority_ajouts.txt",
    "../Authority_list/acronymes.txt",
    "../Authority_list/authority.tsv",
    "../Authority_list/foreign.txt",
]

NB_SUGGESTIONS = 8
SEUIL_SIMILARITE = 0.4
NB_MOTS_CONTEXTE = 20  # mots avant / après

BACKUP_DIR = Path("backups")

# ---------------------------------------------------------------------------

app = Flask(__name__)

# État en mémoire, chargé une fois au démarrage
fichiers_data = {}          # chemin -> liste de lignes (str, sans \n)
occurrences = {}            # lemme -> deque[(chemin, index_ligne), ...]
exemple_mot = {}            # lemme -> premier mot rencontré avec ce lemme
lemmes_autorises = set()    # ensemble de tous les lemmes valides

lemme_actif = None          # lemme actuellement sélectionné dans le bandeau


def sauvegarder(fichiers):
    BACKUP_DIR.mkdir(exist_ok=True)
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin_zip = BACKUP_DIR / f"backup_{horodatage}.zip"
    with zipfile.ZipFile(chemin_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for chemin in fichiers:
            p = Path(chemin)
            if p.exists():
                z.write(p, arcname=p.name)
    print(f"Sauvegarde créée -> {chemin_zip}")


def charger_donnees():
    for chemin in AUTHORITY_FILES:
        p = Path(chemin)
        if not p.exists():
            print(f"Attention : fichier Authority_list introuvable -> {chemin}")
            continue
        with open(p, encoding="utf-8") as f:
            for ligne in f:
                lemme = ligne.strip()
                if lemme:
                    lemmes_autorises.add(lemme)

    existants = [f for f in DATA_FILES if Path(f).exists()]
    manquants = [f for f in DATA_FILES if f not in existants]
    if manquants:
        print("Fichiers Data absents (ignorés) :", ", ".join(manquants))
    sauvegarder(existants)

    for chemin in existants:
        with open(chemin, encoding="utf-8") as f:
            lignes = [l.rstrip("\n") for l in f]
        fichiers_data[chemin] = lignes

        for idx, ligne in enumerate(lignes):
            if not ligne.strip():
                continue
            colonnes = ligne.split("\t")
            if len(colonnes) < 2:
                continue
            lemme = colonnes[1]
            if lemme and lemme not in lemmes_autorises:
                occurrences.setdefault(lemme, deque()).append((chemin, idx))
                exemple_mot.setdefault(lemme, colonnes[0])

    nb_occurrences_total = sum(len(dq) for dq in occurrences.values())
    print(f"{len(occurrences)} lemme(s) distinct(s) à contrôler "
          f"({nb_occurrences_total} occurrence(s) au total).")


def ecrire_fichier(chemin):
    with open(chemin, "w", encoding="utf-8") as f:
        for ligne in fichiers_data[chemin]:
            f.write(ligne + "\n")


def mot_de_la_ligne(chemin, idx):
    """Renvoie le mot (1re colonne) d'une ligne, ou la ligne brute si mal formée."""
    if idx < 0 or idx >= len(fichiers_data[chemin]):
        return ""
    colonnes = fichiers_data[chemin][idx].split("\t")
    return colonnes[0] if colonnes else fichiers_data[chemin][idx]


def contexte(chemin, idx):
    debut = max(0, idx - NB_MOTS_CONTEXTE)
    fin = idx + NB_MOTS_CONTEXTE
    mots_avant = [mot_de_la_ligne(chemin, i) for i in range(debut, idx)]
    mots_apres = [mot_de_la_ligne(chemin, i) for i in range(idx + 1, fin + 1)]
    return mots_avant, mots_apres


def occurrence_courante(lemme):
    dq = occurrences.get(lemme)
    if not dq:
        return None
    return dq[0]


TEMPLATE = """
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Correction des lemmes</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, sans-serif; color: #222; margin: 0; display: flex; }

  nav { width: 260px; height: 100vh; overflow-y: auto; background: #fafafa;
        border-right: 1px solid #ddd; padding: 16px; flex-shrink: 0; }
  nav h2 { font-size: 1em; margin: 0 0 12px 0; color: #555; }
  nav ul { list-style: none; padding: 0; margin: 0; }
  nav li { margin-bottom: 4px; }
  nav a { display: flex; justify-content: space-between; padding: 6px 8px; border-radius: 6px;
          text-decoration: none; color: #222; font-size: 0.92em; }
  nav a:hover { background: #eee; }
  nav a.actif { background: #d6e6ff; font-weight: 600; }
  nav .compte { color: #888; }

  main { flex: 1; padding: 40px; max-width: 820px; }
  h1 { font-size: 1.3em; }
  .compteur { color: #666; margin-bottom: 24px; }

  .contexte { font-size: 1.15em; line-height: 1.8; background: #f7f7f7; padding: 20px;
              border-radius: 8px; margin-bottom: 20px; }
  .contexte .avant, .contexte .apres { color: #444; }
  .contexte .cible { background: #ffe08a; padding: 2px 6px; border-radius: 4px; font-weight: 700; }

  .lemme { font-size: 1.1em; color: #b00; margin-bottom: 20px; }

  .suggestions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 24px; }
  .suggestions button { padding: 8px 14px; border: 1px solid #ccc; border-radius: 6px;
                          background: #f5f5f5; cursor: pointer; font-size: 1em; }
  .suggestions button:hover { background: #e8e8e8; }

  .manuel { display: flex; gap: 8px; align-items: center; margin: 16px 0 16px 0; }
  .manuel input[type=text] { padding: 8px; font-size: 1em; flex: 1; }
  .manuel button { padding: 8px 14px; cursor: pointer; white-space: nowrap; }
  .options { margin: 0 0 16px 0; font-size: 0.9em; color: #555; display: flex;
             align-items: center; gap: 8px; flex-wrap: wrap; }
  .options select { max-width: 260px; }

  .passer button { background: none; border: none; color: #888; text-decoration: underline;
                    cursor: pointer; font-size: 0.9em; }
  .toutes { display: block; margin-top: 6px; font-size: 0.85em; color: #666; }
  .termine, .vide { font-size: 1.15em; color: #2a2; }
</style>
</head>
<body>

<nav>
  <h2>Lemmes à contrôler ({{ total_lemmes }})</h2>
  <ul>
    {% for l, n in lemmes_tries %}
      <li>
        <a href="{{ url_for('choisir_lemme', lemme=l) }}" class="{{ 'actif' if l == lemme_actif else '' }}">
          <span>{{ l }}</span><span class="compte">{{ n }}</span>
        </a>
      </li>
    {% else %}
      <li><em>Aucun lemme restant.</em></li>
    {% endfor %}
  </ul>
</nav>

<main>
{% if lemme_actif is none %}
  <h1>Contrôle des lemmes</h1>
  {% if total_lemmes == 0 %}
    <p class="termine">Terminé — tous les lemmes ont été contrôlés.</p>
  {% else %}
    <p class="vide">Choisissez un lemme dans le bandeau à gauche pour commencer.</p>
  {% endif %}
{% else %}
  <h1>Lemme : « {{ lemme_actif }} »</h1>
  <p class="compteur">{{ nb_restantes }} occurrence(s) restante(s) pour ce lemme</p>

  <div class="contexte">
    <span class="avant">{{ mots_avant|join(' ') }}</span>
    <span class="cible">{{ mot_cible }}</span>
    <span class="apres">{{ mots_apres|join(' ') }}</span>
  </div>

  <p class="lemme">Lemme actuel : « {{ lemme_actif }} » (absent de la liste de référence) — fichier {{ chemin }}, ligne {{ idx + 1 }}</p>

  <form method="post" action="{{ url_for('valider') }}">
    <input type="hidden" name="lemme_original" value="{{ lemme_actif }}">
    <input type="hidden" name="chemin" value="{{ chemin }}">
    <input type="hidden" name="idx" value="{{ idx }}">

    <div class="suggestions">
      {% for s in suggestions %}
        <button type="submit" name="lemme_choisi" value="{{ s }}">{{ s }}</button>
      {% else %}
        <em>Aucune suggestion proche trouvée.</em>
      {% endfor %}
    </div>

    <div class="manuel">
      <input type="text" name="lemme_manuel" placeholder="...ou saisir le bon lemme manuellement">
      <button type="submit">Valider la saisie manuelle</button>
    </div>

    <div class="options">
      <label>
        <input type="checkbox" name="ajouter_autorite">
        Si saisie manuelle, ajouter aussi ce lemme à :
      </label>
      <select name="fichier_autorite">
        {% for f in fichiers_autorite %}
          <option value="{{ f }}">{{ f }}</option>
        {% endfor %}
      </select>
    </div>

    {% if nb_restantes > 1 %}
      <label class="toutes">
        <input type="checkbox" name="appliquer_toutes">
        Appliquer directement à {{ nb_restantes }} occurrence(s) restante(s) de « {{ lemme_actif }} », sans repasser par leur contexte
      </label>
    {% endif %}
  </form>

  <form method="post" action="{{ url_for('passer') }}" class="passer">
    <input type="hidden" name="lemme" value="{{ lemme_actif }}">
    <button type="submit">Passer cette occurrence (revient plus tard) &raquo;</button>
  </form>
{% endif %}
</main>
</body>
</html>
"""


def contexte_html():
    occ = occurrence_courante(lemme_actif) if lemme_actif else None
    if occ is None:
        return {}
    chemin, idx = occ
    mots_avant, mots_apres = contexte(chemin, idx)
    mot_cible = mot_de_la_ligne(chemin, idx)
    suggestions = difflib.get_close_matches(
        lemme_actif, lemmes_autorises, n=NB_SUGGESTIONS, cutoff=SEUIL_SIMILARITE
    )
    return dict(
        chemin=chemin, idx=idx, mots_avant=mots_avant, mots_apres=mots_apres,
        mot_cible=mot_cible, suggestions=suggestions,
        nb_restantes=len(occurrences[lemme_actif]),
    )


def lemmes_tries_pour_affichage():
    return sorted(
        ((l, len(dq)) for l, dq in occurrences.items() if dq),
        key=lambda t: -t[1]
    )


@app.route("/")
def accueil():
    ctx = contexte_html()
    return render_template_string(
        TEMPLATE,
        lemme_actif=lemme_actif,
        lemmes_tries=lemmes_tries_pour_affichage(),
        total_lemmes=len(occurrences),
        fichiers_autorite=AUTHORITY_FILES,
        **ctx,
    )


@app.route("/lemme/<path:lemme>")
def choisir_lemme(lemme):
    global lemme_actif
    if lemme in occurrences and occurrences[lemme]:
        lemme_actif = lemme
    return redirect(url_for("accueil"))


@app.route("/valider", methods=["POST"])
def valider():
    global lemme_actif
    lemme_original = request.form["lemme_original"]
    chemin = request.form["chemin"]
    idx = int(request.form["idx"])
    lemme_choisi = request.form.get("lemme_choisi")
    lemme_manuel = request.form.get("lemme_manuel", "").strip()
    lemme_corrige = lemme_choisi or lemme_manuel

    dq = occurrences.get(lemme_original)
    if not lemme_corrige or not dq or dq[0] != (chemin, idx):
        # état incohérent (page rechargée avec des données périmées) : on ignore
        return redirect(url_for("accueil"))

    appliquer_toutes = bool(request.form.get("appliquer_toutes"))
    a_corriger = list(dq) if appliquer_toutes else [dq[0]]

    fichiers_touches = set()
    for c, i in a_corriger:
        colonnes = fichiers_data[c][i].split("\t")
        colonnes[1] = lemme_corrige
        fichiers_data[c][i] = "\t".join(colonnes)
        fichiers_touches.add(c)
    for c in fichiers_touches:
        ecrire_fichier(c)
    print(f"  {lemme_original!r} -> {lemme_corrige!r} "
          f"({len(a_corriger)} occurrence(s), {len(fichiers_touches)} fichier(s))")

    if appliquer_toutes:
        del occurrences[lemme_original]
        lemme_actif = None
    else:
        dq.popleft()
        if not dq:
            del occurrences[lemme_original]
            lemme_actif = None

    if lemme_manuel and request.form.get("ajouter_autorite") and lemme_corrige not in lemmes_autorises:
        fichier_cible = request.form.get("fichier_autorite", AUTHORITY_FILES[0])
        with open(fichier_cible, "a", encoding="utf-8") as f:
            f.write(lemme_corrige + "\n")
        lemmes_autorises.add(lemme_corrige)
        print(f"  Ajouté à {fichier_cible} : {lemme_corrige!r}")

    return redirect(url_for("accueil"))


@app.route("/passer", methods=["POST"])
def passer():
    lemme = request.form["lemme"]
    dq = occurrences.get(lemme)
    if dq:
        dq.rotate(-1)  # l'occurrence courante repasse en fin de file
    return redirect(url_for("accueil"))


if __name__ == "__main__":
    charger_donnees()
    app.run(debug=False, port=5000)
