# Annotation CoNLL — Révision Wikidata

Outil de vérification et correction des identifiants Wikidata dans un fichier d'annotation CoNLL.  
Le fichier source n'est **jamais modifié** : toutes les corrections transitent par des fichiers intermédiaires.

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `1_analyser.py` | Lit le CoNLL, produit `rapport.json` |
| `2_reviser.html` | Interface de révision interactive (navigateur) |
| `3_appliquer.py` | Applique `corrections.json` au CoNLL pour produire un fichier corrigé |
| `4_diff.py` | Compare source et corrigé, produit un rapport HTML lisible |

---

## Processus

### Étape 1 — Analyser

```bash
python 1_analyser.py mon_corpus.conll
# ou avec un nom de rapport personnalisé :
python 1_analyser.py mon_corpus.conll --rapport rapport.json
```

- Lit le fichier CoNLL (même très volumineux, 5M de lignes)
- Extrait toutes les entités nommées (spans B-/I-)
- **Regroupe par (texte + type NER + ID existant)** — un même texte avec des IDs différents forme des groupes distincts
- Extrait la phrase complète autour de chaque occurrence comme contexte
- Ignore les entités de type `time` et `amount` sans ID (non référençables)
- Écrit `rapport.json` — ne modifie pas le CoNLL

### Étape 2 — Réviser

Ouvrir `2_reviser.html` dans un navigateur (double-clic), puis charger `rapport.json`.

**Interface :**
- La sidebar liste les groupes triés par fréquence décroissante (les plus impactants en premier)
- Les groupes traités, à revoir et impossibles descendent en bas de la liste
- Chaque groupe affiche la phrase complète autour de chaque occurrence
- Si un ID Wikidata est déjà présent, un aperçu Wikipedia s'affiche automatiquement

**Pour chaque groupe, quatre actions possibles :**

| Action | Effet |
|---|---|
| Cliquer sur un ID existant → **✓ Valider** | Confirme l'ID pour les occurrences compatibles |
| **Chercher** sur Wikidata + cliquer un résultat | Assigne un nouvel ID |
| **⏸ À revoir** | Marque le groupe pour y revenir plus tard |
| **✗ Impossible** | Marque l'entité comme non référençable (personnage fictif, etc.) |

> **Règle de sécurité** : un ID n'est jamais appliqué à une occurrence qui possède déjà un ID différent. Seules les occurrences avec exactement cet ID (ou sans ID si le groupe est homogène) sont modifiées.

**Sauvegarde :** les décisions sont sauvegardées automatiquement dans le navigateur (localStorage). Fermer et rouvrir l'interface recharge la session en cours.

**Repartir de zéro :** bouton *Repartir de zéro* en haut à droite (avec confirmation).

Quand la révision est terminée (ou à tout moment) : **Exporter corrections.json**.

### Étape 3 — Appliquer

```bash
# Simuler sans écrire (recommandé avant la vraie application)
python 3_appliquer.py mon_corpus.conll corrections.json --dry-run

# Appliquer et écrire le fichier corrigé
python 3_appliquer.py mon_corpus.conll corrections.json --output corpus_corrige.conll
```

- Demande confirmation avant d'écrire
- Le fichier source n'est pas modifié
- Un log `corpus_corrige_log.json` est écrit à côté du fichier de sortie

### Étape 4 — Vérifier

```bash
python 4_diff.py mon_corpus.conll corpus_corrige.conll
# ou avec un nom de rapport personnalisé :
python 4_diff.py mon_corpus.conll corpus_corrige.conll --output rapport_diff.html
```

Compare directement le fichier source original et le fichier corrigé final, **sans dépendre d'aucune autre étape** ni de `corrections.json`. On part du point de départ, on arrive au point d'arrivée — le rapport montre tout ce qui a changé entre les deux.

Ouvrir `rapport_diff.html` dans un navigateur.

Le rapport affiche :
- Les statistiques globales (lignes modifiées, entités touchées, anomalies)
- **Toutes les modifications** groupées par type de changement (`_ → Q90`, `Q12 → Q90`, etc.), sans troncature, triées par nombre d'occurrences
- Les **anomalies** en rouge si une colonne autre que WikidataID a été modifiée (signe d'un problème à investiguer avant d'aller plus loin)

---

## Format CoNLL attendu

```
token   lemme   POS   NER1   NER2   NER3   NER4   WikidataID
```

- `WikidataID` vaut `_` si absent
- Les entités sont balisées en schéma BIO (`B-loc`, `I-loc`, etc.)
- La colonne NER1 est prioritaire ; NER2 est utilisée en fallback

---

## Conseils

- Toujours faire un `--dry-run` avant d'appliquer les corrections
- Garder le `rapport.json` et le `corrections.json` : ils permettent de retracer toutes les décisions
- Si tu relances `1_analyser.py` sur un corpus modifié, le `rapport_id` change et les corrections précédentes ne sont pas rechargées automatiquement dans le navigateur
- Les groupes *Impossibles* et *À revoir* sont exportés dans `corrections.json` avec leur statut, pour archivage
