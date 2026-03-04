# Urban Health Agent-Based Model (ABM)

## Przegląd

Zaawansowany obiektowy Agent-Based Model (ABM) symulujący demografię i multimorbidność populacji przez **50 lat (600 miesięcy)**. Model oparty jest na rzeczywistych danych epidemiologicznych z badań zdrowotnych.

## Główne Cechy

✅ **Dane rzeczywiste**: 15 najczęstszych chorób wyekstrahowanych z danych epidemiologicznych (Excel)
✅ **Modularna architektura**: Czysty kod Python z typowaniem (`typing`)
✅ **Pełna symulacja demograficzna**:
  - Starzenie się (1 miesiąc na iterację)
  - Narodziny (tylko dla kobiet 18-40 lat)
  - Zgony (zależne od wieku, liczby chorób, disability score)
  - Tworzenie/rozbijanie gospodarstw domowych
  - Opuszczanie gospodarstw przez dorosłe dzieci
✅ **Multimorbidność**: Model progresji chorób, liczba chorób, disability score
✅ **Statystyki roczne**: Zbieranie danych co 12 miesięcy
✅ **Interaktywne wizualizacje**: Plotly z suwakami rocznymi

## Struktura Projektu

```
urban_health_abm/
├── main.py                          # Główny punkt wejścia
├── citizen.py                       # Klasa Citizen
├── household.py                     # Klasa Household
├── disease_model.py                 # Klasa DiseaseModel
├── simulation_engine.py             # Klasa SimulationEngine
├── visualization.py                 # Klasa SimulationVisualizer
├── population_data.xlsx             # Dane wejściowe (15 kolumn chorób)
├── age_pyramid_interactive.html     # Piramida wieku z suwakiem
├── population_trends.html           # Trendy populacyjne
├── households_trends.html           # Dynamika gospodarstw
└── gender_distribution.html         # Rozkład płci
```

## Architektura Klas

### 1. **Citizen**
Reprezentuje pojedynczego obywatela.

**Atrybuty**:
- `id: int` - Unikalny identyfikator
- `sex: str` - "male" lub "female"
- `age_months: int` - Wiek w miesiącach
- `alive: bool` - Status życia
- `household_id: int` - ID gospodarstwa
- `diseases: Dict[str, int]` - Słownik chorób (0/1)
- `disability_score: float` - Suma wag chorób

**Metody**:
- `age_one_month()` - Starzenie się o 1 miesiąc
- `compute_disability_score()` - Obliczanie disability
- `mortality_risk()` - Ryzyko śmierci
- `fertility_probability()` - Prawdopodobieństwo narodzin
- `maybe_die()` - Losowa śmierć
- `maybe_give_birth()` - Losowe narodziny

### 2. **Household**
Reprezentuje gospodarstwo domowe.

**Atrybuty**:
- `id: int` - Unikalny identyfikator
- `zone_id: int` - ID strefy geograficznej
- `members: List[int]` - IDs członków

**Metody**:
- `add_member()`, `remove_member()`
- `size()` - Liczba członków
- `has_children()`, `is_empty()`

### 3. **DiseaseModel**
Zarządza chorobami w symulacji.

**Stale**:
- `DEFAULT_DISEASES` - 15 głównych chorób
- `DEFAULT_PREVALENCE` - Częstości epidemiologiczne
- `DEFAULT_DISABILITY_WEIGHTS` - Wagi disability (0-1)

**Metody**:
- `get_initial_diseases()` - Słownik chorób zainicjalizowany na 0
- `get_prevalence()`, `get_disability_weight()`

### 4. **SimulationEngine**
Główny silnik symulacji.

**Atrybuty**:
- `citizens: Dict[int, Citizen]` - Populacja
- `households: Dict[int, Household]` - Gospodarstwa
- `disease_model: DiseaseModel` - Model chorób
- `yearly_stats: Dict[int, Dict]` - Statystyki roczne
- `current_month: int` - Aktualny miesiąc

**Parametry konfiguracyjne**:
- `fertility_rate` - Mnożnik płodności
- `mortality_multiplier` - Mnożnik śmiertelności
- `household_split_probability` - Prawdopodobieństwo rozbicia gospodarstwa

**Metody**:
- `load_initial_population()` - Wczytanie z Excel lub stworzenie syntetyczne
- `run(months)` - Uruchomienie symulacji
- `step()` - Jeden miesiąc symulacji
- `handle_births()`, `handle_deaths()`, `handle_household_splits()`
- `collect_yearly_stats()` - Zbieranie statystyk
- `apply_risk_factors()` - Dostosowuje prawdopodobieństwa chorób na podstawie czynników ryzyka

### 5. **SimulationVisualizer**
Generowanie interaktywnych wykresów.

**Metody**:
- `plot_interactive_age_pyramid()` - Piramida wieku ze suwakiem
- `plot_population_trends()` - Trendy: populacja, multimorbidność, disability
- `plot_households_trends()` - Dynamika gospodarstw
- `plot_gender_distribution()` - Rozkład płci
- `generate_all_plots()` - Wszystkie wykresy

## Logika Modelu

### Starzenie
```
Każdy miesiąc: age_months += 1
```

### Narodziny
- Tylko kobiety 18-40 lat
- Szczyt płodności 25-30 lat (rozkład Gaussa)
- Zmniejszenie przez obciążenie chorobami
- Dziecko wieku 0 miesięcy trafia do gospodarstwa matki

### Zgony
Model ryzyka śmiertelności:
```
risk = age_factor * (1 + exp((age - 55)/15)) + 
       disease_factor * (0.001 * n_conditions + 0.005 * disability)
```
- Kobiety mają 15% niższe ryzyko
- Ryzyko wzrasta exponentially po 55 roku życia

### Gospodarstwa
- Osoby 25+ lat mogą opuścić gospodarstwo z prawdopodobieństwem `household_split_probability`
- Tworzą nowe gospodarstwa w tej samej strefie
- Gospodarstwa puste są usuwane

## Dane Wejściowe

Plik Excel (`population_data.xlsx`) powinien zawierać:
- `id` - ID osoby
- `sex` - "M" lub "F"
- `age` - Wiek w latach (20-80)
- `household_id` - ID gospodarstwa
- `zone_id` - ID strefy (1-3)
- 15 kolumn chorób (0/1):
  - Obesity, Hypercholesterolemia, Osteoarthritis, Hypertension, Allergy
  - Focal thyroid lesions, Lower limb varicose veins, Rectal varices
  - Hypertriglyceridemia, Gastroesophageal reflux disease, Peptic ulcer disease
  - Discopathy, Migraine, Cholelithiasis, Fatty liver disease

## Uruchamianie

```bash
# 1. Przygotowanie środowiska
pip install pandas openpyxl plotly numpy scipy

# 2. Przygotowanie danych (opcjonalnie)
# Umieść plik population_data.xlsx w bieżącym katalogu
# Lub system automatycznie stworzy populację syntetyczną

# 3. Uruchomienie symulacji
python main.py
```

## Wyjście

Program generuje 4 interaktywne HTML pliki:

### 1. **age_pyramid_interactive.html**
- Piramida wieku i płci
- Mężczyźni na lewej stronie (wartości ujemne)
- Kobiety na prawej stronie (wartości dodatnie)
- **Suwak roczny** (0-50 lat)
- Hover: liczba osób w grupie wieku

### 2. **population_trends.html**
- Wykres 1: Całkowita populacja w czasie
- Wykres 2: Liczba przypadków multimorbidności
- Wykres 3: Średni disability score
- Trend przez 50 lat

### 3. **households_trends.html**
- Liczba gospodarstw w czasie
- Średnia wielkość gospodarstwa
- Zmiana dynamiki rodzinnej

### 4. **gender_distribution.html**
- Rozkład płci w populacji
- Liczba mężczyzn i kobiet w czasie

## Parametryzacja

Możliwość zmienienia parametrów w `main.py`:

```python
engine.fertility_rate = 1.0                    # Domyślnie
engine.mortality_multiplier = 1.0              # Domyślnie
engine.household_split_probability = 0.001     # 0.1% miesięcznie
```

## Wymagania Jakościowe ✓

- ✅ **Typing**: Wszystkie funkcje mają type hints
- ✅ **Docstrings**: Pełna dokumentacja wszystkich klas i metod
- ✅ **Modularność**: Czysty podział na klasy i moduły
- ✅ **Brak kodu proceduralnego**: Tylko w `main.py`
- ✅ **Separacja logiki i wizualizacji**: Osobne moduły
- ✅ **Pełna uruchamialność**: Działa bez błędów

## Przykładowe Rezultaty

```
Year 1:  Population= 1522, Households= 414
Year 5:  Population= 1256, Households= 469
Year 10: Population=  983, Households= 544
Year 20: Population=  632, Households= 642
Year 30: Population=  429, Households= 702
Year 50: Population=  229, Households= 769

Multimorbidity Cases (Year 50): 77
Average Disability Score: 0.133
```

## Uwagi na temat Modelu

1. **Przemiany demograficzne**: Populacja systematycznie się starzeje i maleje (realistyczne dla populacji 20-80 lat bez migracji)

2. **Multimorbidność**: Rośnie z wiekiem, wpływa na śmiertelność i płodność

3. **Disability Score**: Suma wag chorób (0.05-0.20 per choroba)

4. **Gospodarstwa**: Dynamicznie ulegają zmianom - osoby dorosłe opuszczają dom, tworząc nowe gospodarstwa

5. **Płodność**: Modelowana realistycznie - szczyt 25-30 lat, spadek po 40 rokach

## Technologia

- **Python 3.12**
- **Pandas**: Wczytywanie danych z Excel
- **Plotly**: Interaktywne wykresy
- **NumPy**: Operacje numeryczne
- **Random**: Generator liczb losowych z seed dla reproducibility

## Autorzy

Urban Health ABM - Agent-Based Model demografii i multimorbidności
Projekt zespołowy - 2026

---

**Szczegóły**: Model symuluje realną populację 20-80 lat przez 50 lat z dokładnym modelowaniem:
- Starzenia się (miesięcznym)
- Narodzin (z realistycznym rozkładem wieku matki)
- Zgonów (exponential z wiekiem + wpływ chorób)
- Dynamiki gospodarstw (osoby dorosłe opuszczają dom)
- Multimorbidności (do 15 chorób, disability score, wpływ na zgony)

---

## Nowe Funkcjonalności

#### Czynniki Ryzyka
Model uwzględnia czynniki ryzyka, które wpływają na rozwój chorób. Przykładowe czynniki ryzyka:
- **Palenie**: Zwiększa ryzyko migreny i kamicy żółciowej.
- **Brak aktywności fizycznej**: Zwiększa ryzyko otyłości i stłuszczenia wątroby.
- **Dieta wysokotłuszczowa**: Zwiększa ryzyko otyłości i kamicy żółciowej.

#### Nowe Metody
- `apply_risk_factors()`: Metoda w `SimulationEngine`, która dostosowuje prawdopodobieństwa chorób na podstawie czynników ryzyka.
