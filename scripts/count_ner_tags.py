import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

file_path = "Data/presto_max/presto_max_v6.txt"

# Lecture ligne par ligne sécurisée
rows = []
with open(file_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 8:
            parts += ["_"] * (8 - len(parts))
        elif len(parts) > 8:
            parts = parts[:8]
        rows.append(parts)

columns = ["token", "lemma", "pos", "ner1", "ner2", "ner3", "ner4", "other"]
df = pd.DataFrame(rows, columns=columns)

# Fonction pour afficher la distribution par colonne (en filtrant O si demandé)
def plot_column_counts(df, column, ignore_O=False, top_n=None):
    data = df[column]
    if ignore_O:
        data = data[data != "O"]  # ignorer O
    counts = data.value_counts()
    if top_n is not None:
        counts = counts.head(top_n)
    if len(counts) == 0:
        print(f"Aucune valeur à afficher pour {column} après filtrage")
        return counts
    plt.figure(figsize=(10, 6))
    sns.barplot(x=counts.index, y=counts.values, color="steelblue")
    plt.title(f"Distribution des valeurs pour la colonne '{column}'")
    plt.xticks(rotation=45, ha='right')
    plt.ylabel("Nombre d'occurrences")
    plt.xlabel("Valeurs")
    plt.tight_layout()
    plt.show()
    return counts

# Colonnes à visualiser
visualize_cols = ["pos", "ner1", "ner2", "ner3", "ner4"]

for col in visualize_cols:
    print(f"\n--- Colonne: {col} ---")
    plot_column_counts(df, col, ignore_O=(col.startswith("ner")))