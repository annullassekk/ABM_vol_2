"""
Main entry point for the Urban Health ABM simulation.

This script orchestrates the entire simulation:
1. Initializes demographic engine with realistic Polish population structure
2. Runs 50-year (600-month) demographic simulation with 50,000 agents
3. Collects yearly statistics (age pyramid, households, mortality, etc.)
4. Generates interactive visualizations in Plotly format
"""

import sys
from simulation_engine import SimulationEngine
from disease_model import DiseaseModel
from visualization import SimulationVisualizer


def main() -> None:
    """Main simulation execution function."""
    
    print("=" * 70)
    print("URBAN HEALTH AGENT-BASED MODEL (URBAN-ABM)")
    print("Demographic Simulation with 50,000 Agents")
    print("Polish GUS-Inspired Population Structure")
    print("=" * 70)
    print()
    
    # Initialize disease model with top 15 diseases
    print("Initializing disease model...")
    disease_model = DiseaseModel()
    print(f"Selected {disease_model.get_disease_count()} diseases for simulation:")
    for i, disease in enumerate(disease_model.diseases, 1):
        prevalence = disease_model.get_prevalence(disease)
        weight = disease_model.get_disability_weight(disease)
        print(f"  {i:2}. {disease:<40} (prevalence={prevalence:5.1f}%, disability={weight:.2f})")
    print()
    
    # Create simulation engine
    print("Creating simulation engine with demographic tables...")
    engine = SimulationEngine(
        disease_model=disease_model,
        seed=42,  # For reproducibility
    )
    
    # Configure simulation parameters
    engine.fertility_rate = 1.0
    engine.mortality_multiplier = 1.0
    engine.household_split_probability = 0.001
    
    print(f"  Fertility rate multiplier: {engine.fertility_rate}")
    print(f"  Mortality multiplier: {engine.mortality_multiplier}")
    print(f"  Household split probability: {engine.household_split_probability}")
    print(f"  Zones created: {len(engine.zones)}")
    print()
    
    # Load initial population (create 50,000 synthetic with Polish demographics)
    print("Generating initial population...")
    loaded = engine._create_synthetic_population(50000)
    
    print(f"  Initial households: {len(engine.households)}")
    print(f"  Total zones: {len(engine.zones)}")
    
    # Display age distribution
    alive = [c for c in engine.citizens.values() if c.alive]
    children = sum(1 for c in alive if c.age_years < 15)
    working = sum(1 for c in alive if 18 <= c.age_years < 65)
    elderly = sum(1 for c in alive if c.age_years >= 65)
    pct_female = sum(1 for c in alive if c.sex == "female") / len(alive) * 100
    
    print(f"  Population composition:")
    print(f"    - Children (0-14): {children} ({children/len(alive)*100:.1f}%)")
    print(f"    - Working-age (18-64): {working} ({working/len(alive)*100:.1f}%)")
    print(f"    - Elderly (65+): {elderly} ({elderly/len(alive)*100:.1f}%)")
    print(f"    - Female: {pct_female:.1f}%")
    print()
    
    # Run simulation
    print("Running simulation for 50 years (600 months)...")
    engine.run(months=600)
    print()
    
    # Display final statistics
    print(engine.get_statistics_summary())
    print()
    
    # Generate visualizations
    print("Generating interactive visualizations...")
    visualizer = SimulationVisualizer(engine.yearly_stats)
    visualizer.generate_all_plots()
    print()
    
    print("=" * 70)
    print("SIMULATION COMPLETE")
    print("=" * 70)
    print("\nGenerated output files:")
    print("  📊 DEMOGRAFIC PYRAMIDS (GUS-style, interactive):")
    print("     - piramida_wieku_rok_50.html (Age pyramid - year 50)")
    print("     - piramida_wieku_animowana.html (Animated pyramid with year slider)")
    print("  📈 POPULATION TRENDS:")
    print("     - population_trends.html (Population, multimorbidity, disability)")
    print("     - households_trends.html (Household dynamics)")
    print("     - gender_distribution.html (Male/Female temporal distribution)")
    print("\nOpen HTML files in a web browser to interactively analyze results.")
    print(f"\nTotal agents simulated: 50,000")
    print(f"Simulation duration: 50 years")
    print(f"Final population: {len([c for c in engine.citizens.values() if c.alive])}")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
