"""
Analiza czynników ryzyka i ich wpływu na choroby.
Skrypt generuje:
 - mapę cieplną `risk_factor_impact.png`
 - plik CSV `risk_factor_rankings.csv` z rankingami czynników dla każdej choroby
 - plik tekstowy `risk_factor_summary.txt` z czytelną listą najlepiej wpływających czynników

Uwaga: dane wejściowe (słownik `risk_factors`) zawierają wagi (0-1), które
oznaczają względny wpływ danego czynnika na chorobę (np. 0.2 = 20% względnego
wskaźnika wpływu używanego w prostym modelu addytywnym).
"""

import csv
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx


# --- Definicja danych (przykładowe, można podmienić z DiseaseModel) ---
risk_factors = {
    "Palenie": {"Migrena": 0.20, "Kamica żółciowa": 0.10},
    "Brak aktywności": {"Otyłość": 0.30, "Stłuszczenie wątroby": 0.25},
    "Dieta wysokotłuszczowa": {"Otyłość": 0.40, "Kamica żółciowa": 0.20},
}


def analyze_risk_factors(risk_factors):
    """
    Analizuje wpływ czynników ryzyka na choroby.

    Zwraca ranking czynników dla każdej choroby oraz generuje wykres i pliki wynikowe.
    """
    # Zbiór wszystkich chorób
    diseases = set()
    for impacts in risk_factors.values():
        diseases.update(impacts.keys())

    diseases = sorted(diseases)
    factors = sorted(risk_factors.keys())

    # Macierz wpływów: wiersze = choroby, kolumny = czynniki
    impact_matrix = np.zeros((len(diseases), len(factors)))
    for j, factor in enumerate(factors):
        for i, disease in enumerate(diseases):
            impact_matrix[i, j] = risk_factors[factor].get(disease, 0.0)

    # --- Zapis rankingów do CSV i pliku tekstowego ---
    csv_file = "risk_factor_rankings.csv"
    txt_file = "risk_factor_summary.txt"

    with open(csv_file, "w", newline='', encoding='utf-8') as cf, open(txt_file, "w", encoding='utf-8') as tf:
        writer = csv.writer(cf)
        writer.writerow(["disease", "risk_factor", "impact"])

        tf.write("Ranking wpływu czynników ryzyka na choroby\n")
        tf.write("=======================================\n\n")

        for i, disease in enumerate(diseases):
            impacts = []
            for j, factor in enumerate(factors):
                val = impact_matrix[i, j]
                impacts.append((factor, val))

            # Sortowanie malejąco
            impacts_sorted = sorted(impacts, key=lambda x: x[1], reverse=True)

            tf.write(f"Choroba: {disease}\n")
            for factor, val in impacts_sorted:
                tf.write(f"  {factor}: {val:.3f}\n")
                writer.writerow([disease, factor, f"{val:.6f}"])
            tf.write("\n")

    print(f"Zapisano ranking do {csv_file} i {txt_file}")

    # --- Mapa cieplna ---
    plt.figure(figsize=(10, max(4, len(diseases) * 0.6)))
    im = plt.imshow(impact_matrix, cmap="YlGnBu", aspect="auto")
    plt.colorbar(im, label="Wpływ (0-1)")
    plt.xticks(ticks=range(len(factors)), labels=factors, rotation=45, ha="right")
    plt.yticks(ticks=range(len(diseases)), labels=diseases)
    plt.title("Wpływ czynników ryzyka na choroby")
    plt.xlabel("Czynniki ryzyka")
    plt.ylabel("Choroby")
    plt.tight_layout()
    output_png = "risk_factor_impact.png"
    plt.savefig(output_png)
    plt.close()
    print(f"Zapisano mapę cieplną do {output_png}")


def generate_dependency_tree(risk_factors):
    """
    Tworzy drzewo zależności między czynnikami ryzyka a chorobami i zapisuje je jako plik graficzny.
    """
    G = nx.DiGraph()

    # Dodawanie węzłów i krawędzi
    for factor, diseases in risk_factors.items():
        for disease, impact in diseases.items():
            G.add_edge(factor, disease, weight=impact)

    # Wizualizacja drzewa
    pos = nx.spring_layout(G, seed=42)  # Układ węzłów
    plt.figure(figsize=(12, 8))
    
    # Rysowanie węzłów i krawędzi
    nx.draw(
        G, pos, with_labels=True, node_size=3000, node_color="lightblue",
        font_size=10, font_weight="bold", edge_color="gray"
    )

    # Dodawanie etykiet wag na krawędziach
    edge_labels = nx.get_edge_attributes(G, 'weight')
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels={k: f"{v:.2f}" for k, v in edge_labels.items()}, font_size=9
    )

    # Zapis do pliku
    output_file = "risk_factor_dependency_tree.png"
    plt.title("Drzewo zależności: Czynniki ryzyka a choroby")
    plt.savefig(output_file)
    plt.close()
    print(f"Zapisano drzewo zależności do {output_file}")


if __name__ == "__main__":
    analyze_risk_factors(risk_factors)
    generate_dependency_tree(risk_factors)