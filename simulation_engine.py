"""
Main simulation engine for the Agent-Based Model.
Orchestrates the simulation loop and handles all demographic events.
Implements realistic Polish demographic structure and synthetic population generation.
"""

from typing import Dict, List, Tuple, Optional
import random
import pandas as pd

from citizen import Citizen
from household import Household
from zone import Zone
from disease_model import DiseaseModel


class SimulationEngine:
    """
    Main simulation engine managing population dynamics.
    
    Implements realistic Polish demographic structure based on GUS (Statistics Poland) data.
    
    Attributes:
        citizens: Dictionary mapping citizen IDs to Citizen objects
        households: Dictionary mapping household IDs to Household objects
        zones: Dictionary mapping zone IDs to Zone objects
        disease_model: DiseaseModel instance
        current_month: Current month in simulation
        yearly_stats: Dictionary storing statistics for each year
        rng: Random number generator for reproducibility
        mortality_table: Age-sex specific mortality rates (per month)
        fertility_table: Age-specific fertility rates (per year)
    """
    
    # Age-specific mortality rates (monthly) - Polish demographic data inspired
    # Higher values for males and elderly
    DEFAULT_MORTALITY_TABLE = {
        # Age: (male_rate, female_rate)
        0: (0.0003, 0.0002),    # Infant mortality (per month)
        1: (0.00005, 0.00004),  # Children 1-4
        5: (0.00002, 0.00002),  # Children 5-9
        10: (0.00002, 0.00002), # Children 10-14
        15: (0.00003, 0.00002), # Youth 15-19
        20: (0.00005, 0.00003), # Young adult 20-24
        25: (0.00005, 0.00003), # Adult 25-29
        30: (0.00006, 0.00003), # Adult 30-34
        35: (0.00007, 0.00004), # Adult 35-39
        40: (0.00010, 0.00005), # Adult 40-44
        45: (0.00015, 0.00007), # Middle-aged 45-49
        50: (0.00025, 0.00012), # Middle-aged 50-54
        55: (0.00040, 0.00018), # Older 55-59
        60: (0.00065, 0.00030), # Older 60-64
        65: (0.00110, 0.00055), # Elderly 65-69
        70: (0.00190, 0.00100), # Elderly 70-74
        75: (0.00320, 0.00170), # Elderly 75-79
        80: (0.00550, 0.00300), # Elderly 80-84
        85: (0.00950, 0.00550), # Very elderly 85-89
        90: (0.01600, 0.01000), # Very elderly 90+
    }
    
    # Age-specific fertility rates (annual) - Polish data inspired
    # Peak fertility 25-35, realistic for Poland
    DEFAULT_FERTILITY_TABLE = {
        # Age: annual_fertility_rate
        15: 0.01,
        20: 0.04,
        25: 0.06,
        30: 0.05,
        35: 0.02,
        40: 0.005,
        45: 0.0005,
    }
    
    def __init__(
        self,
        disease_model: Optional[DiseaseModel] = None,
        seed: Optional[int] = None,
        mortality_table: Optional[Dict[int, Tuple[float, float]]] = None,
        fertility_table: Optional[Dict[int, float]] = None,
    ) -> None:
        """
        Initialize the simulation engine.
        
        Args:
            disease_model: DiseaseModel instance (creates default if None)
            seed: Random seed for reproducibility
            mortality_table: Age-specific mortality rates (defaults to Polish-inspired data)
            fertility_table: Age-specific fertility rates (defaults to Polish-inspired data)
        """
        self.disease_model: DiseaseModel = disease_model or DiseaseModel()
        self.citizens: Dict[int, Citizen] = {}
        self.households: Dict[int, Household] = {}
        self.zones: Dict[int, Zone] = {}
        self.current_month: int = 0
        self.yearly_stats: Dict[int, Dict] = {}
        self.rng: random.Random = random.Random(seed)
        
        # Demographic parameters
        self.mortality_table: Dict[int, Tuple[float, float]] = (
            mortality_table or self.DEFAULT_MORTALITY_TABLE.copy()
        )
        self.fertility_table: Dict[int, float] = (
            fertility_table or self.DEFAULT_FERTILITY_TABLE.copy()
        )
        
        # Simulation parameters
        self.fertility_rate: float = 1.0
        self.mortality_multiplier: float = 1.0
        self.household_split_probability: float = 0.001
        
        # Create default zones
        self._init_zones()
    
    def _init_zones(self) -> None:
        """Initialize default zones with environmental parameters."""
        zone_params = [
            {"air_quality": 0.75, "greenery_index": 0.6, "healthcare_access": 0.9, "population_density": 4000},
            {"air_quality": 0.65, "greenery_index": 0.4, "healthcare_access": 0.85, "population_density": 6000},
            {"air_quality": 0.70, "greenery_index": 0.5, "healthcare_access": 0.80, "population_density": 5000},
            {"air_quality": 0.55, "greenery_index": 0.3, "healthcare_access": 0.75, "population_density": 8000},
        ]
        
        for params in zone_params:
            zone = Zone(params)
            self.zones[zone.id] = zone
    
    def _get_mortality_rate(self, age_years: float, sex: str) -> float:
        """
        Get mortality rate for given age and sex using interpolation.
        
        Args:
            age_years: Age in years
            sex: "male" or "female"
        
        Returns:
            Monthly mortality probability (0-1)
        """
        age_int = int(age_years)
        
        # Find matching or nearest age in table
        if age_int in self.mortality_table:
            male_rate, female_rate = self.mortality_table[age_int]
        else:
            # Find closest age
            available_ages = sorted(self.mortality_table.keys())
            closest_age = min(available_ages, key=lambda x: abs(x - age_int))
            male_rate, female_rate = self.mortality_table[closest_age]
        
        rate = male_rate if sex == "male" else female_rate
        return min(max(rate, 0.0), 1.0)
    
    def _get_fertility_rate(self, age_years: float) -> float:
        """
        Get annual fertility rate for given female age.
        
        Args:
            age_years: Age in years
        
        Returns:
            Annual fertility rate
        """
        if age_years < 15 or age_years > 50:
            return 0.0
        
        age_int = int(age_years)
        
        # Find matching or nearest age
        if age_int in self.fertility_table:
            return self.fertility_table[age_int]
        
        # Interpolate between ages
        available_ages = sorted([a for a in self.fertility_table.keys() if a <= age_int])
        if not available_ages:
            return self.fertility_table[min(self.fertility_table.keys())]
        
        return self.fertility_table[available_ages[-1]]
    
    def load_initial_population(
        self,
        filepath: str = "population_data.xlsx",
        min_age: int = 20,
        max_age: int = 80,
    ) -> int:
        """
        Load initial population from Excel file or create synthetic if not found.
        
        The Excel file should have columns:
        - id, sex, age (in years), household_id, zone_id
        - Plus columns for diseases (0/1)
        
        Args:
            filepath: Path to Excel file (optional)
            min_age: Minimum age to include (years)
            max_age: Maximum age to include (years)
        
        Returns:
            Number of citizens loaded
        """
        try:
            df = pd.read_excel(filepath)
            print(f"Loaded from {filepath}: {len(df)} potential citizens")
        except Exception as e:
            print(f"Could not load from Excel ({e}). Creating synthetic population of 50,000 citizens.")
            return self._create_synthetic_population(50000)
        
        # Assume Excel has columns: id, sex, age, household_id, zone_id, and disease columns
        diseases_list = self.disease_model.diseases
        
        count = 0
        households_seen = set()
        
        for _, row in df.iterrows():
            # Skip invalid ages
            if pd.isna(row.get("age")):
                continue
            
            age = int(row["age"])
            if age < min_age or age > max_age:
                continue
            
            sex = str(row.get("sex", "")).lower()
            if sex not in ["male", "female", "m", "f"]:
                sex = self.rng.choice(["male", "female"])
            
            # Normalize sex
            if sex == "m":
                sex = "male"
            elif sex == "f":
                sex = "female"
            
            # Create citizen
            age_months = age * 12 + self.rng.randint(0, 11)
            
            # Get diseases
            diseases_dict = self.disease_model.get_initial_diseases()
            for disease in diseases_list:
                if disease in row and row[disease] == 1:
                    diseases_dict[disease] = 1
            
            household_id = int(row.get("household_id", 0)) or self.rng.randint(1, 1000)
            zone_id = int(row.get("zone_id", 0)) or self.rng.choice(list(self.zones.keys()))
            
            citizen = Citizen(
                sex=sex,
                age_months=age_months,
                household_id=household_id,
                zone_id=zone_id,
                diseases=diseases_dict,
            )
            
            citizen.compute_disability_score(
                self.disease_model.get_all_disability_weights()
            )
            
            self.citizens[citizen.id] = citizen
            count += 1
        
        # Create households for all citizens
        for citizen in self.citizens.values():
            if citizen.household_id not in self.households:
                zone_id = citizen.zone_id
                household = Household(zone_id)
                self.households[household.id] = household
                citizen.household_id = household.id
            self.households[citizen.household_id].add_member(citizen.id)
        
        return count
    
    def _create_synthetic_population(self, size: int = 50000) -> int:
        """
        Create a synthetic population with realistic Polish demographic structure.
        
        Includes:
        - Age distribution 0-90 years reflecting Polish population pyramid
        - Children (age 0-14) generated synthetically
        - Realistic sex ratio (51-52% female)
        - Age-appropriate disease prevalence
        - Risk factors based on age and other characteristics
        
        Args:
            size: Number of citizens to create (default 50,000)
        
        Returns:
            Number of citizens created
        """
        print(f"Creating synthetic realistic Polish population of {size} citizens...")
        
        # Polish-inspired age distribution (proportion of population in each decade)
        # Based on GUS population pyramid
        age_distribution = {
            0: 0.045,    # 0-9 years: 4.5%
            10: 0.055,   # 10-19: 5.5%
            20: 0.065,   # 20-29: 6.5% (young adult bulge)
            30: 0.085,   # 30-39: 8.5% (demographic bulge)
            40: 0.085,   # 40-49: 8.5% (demographic bulge)
            50: 0.075,   # 50-59: 7.5%
            60: 0.065,   # 60-69: 6.5%
            70: 0.055,   # 70-79: 5.5%
            80: 0.030,   # 80-89: 3.0%
            90: 0.010,   # 90+: 1.0%
        }
        
        # Normalize to ensure sum = 1.0
        total = sum(age_distribution.values())
        age_distribution = {age: prop / total for age, prop in age_distribution.items()}
        
        # Realistic Polish sex ratio (more females overall, even more at older ages)
        sex_ratio_by_decade = {
            0: 0.51,   # 51% female 0-9
            10: 0.50,  # 50% female 10-19
            20: 0.51,  # 51% female 20-29
            30: 0.51,  # 51% female 30-39
            40: 0.51,  # 51% female 40-49
            50: 0.52,  # 52% female 50-59
            60: 0.53,  # 53% female 60-69
            70: 0.55,  # 55% female 70-79
            80: 0.60,  # 60% female 80-89
            90: 0.65,  # 65% female 90+
        }
        
        # Create zones if not already done
        if not self.zones:
            self._init_zones()
        
        # Create households (average household size ~2.5)
        num_households = int(size / 2.5)
        household_members = [0] * num_households
        
        count = 0
        
        # Generate population by age group
        for decade_start in sorted(age_distribution.keys()):
            proportion = age_distribution[decade_start]
            count_in_decade = int(size * proportion)
            
            sex_ratio = sex_ratio_by_decade.get(decade_start, 0.51)
            
            for _ in range(count_in_decade):
                # Random age within decade
                age_years = decade_start + self.rng.random() * 10
                age_months = int(age_years * 12)
                
                # Determine sex based on age-specific ratio
                sex = "female" if self.rng.random() < sex_ratio else "male"
                
                # Initialize diseases based on age and prevalence
                diseases_dict = self.disease_model.get_initial_diseases()
                
                # Children (0-14) have very low disease prevalence
                if age_years < 14:
                    # Only rare congenital conditions
                    for disease in self.disease_model.diseases:
                        diseases_dict[disease] = 0  # No diseases in children
                else:
                    # Age-appropriate disease prevalence
                    age_factor = max(0, (age_years - 20) / 50)  # Increases with age
                    
                    for disease in self.disease_model.diseases:
                        base_prevalence = self.disease_model.get_prevalence(disease) / 100.0
                        # Higher prevalence in older ages
                        adjusted_prevalence = base_prevalence * (0.1 + age_factor)
                        if self.rng.random() < adjusted_prevalence:
                            diseases_dict[disease] = 1
                
                # Assign to household (distribute roughly evenly)
                household_idx = count % num_households
                household_id = list(self.households.keys())[0] if self.households else None
                
                zone_id = self.rng.choice(list(self.zones.keys()))
                
                # Create citizen
                citizen = Citizen(
                    sex=sex,
                    age_months=age_months,
                    household_id=household_id or 1,
                    zone_id=zone_id,
                    diseases=diseases_dict,
                )
                
                # Initialize risk factors based on age and characteristics
                citizen.risk_factors = self._init_risk_factors(citizen)
                
                citizen.compute_disability_score(
                    self.disease_model.get_all_disability_weights()
                )
                
                self.citizens[citizen.id] = citizen
                count += 1
        
        # Create households and assign citizens
        zone_list = list(self.zones.keys())
        for hh_idx in range(num_households):
            zone_id = zone_list[hh_idx % len(zone_list)]
            household = Household(zone_id)
            self.households[household.id] = household
        
        # Assign citizens to households
        household_ids = list(self.households.keys())
        for idx, citizen in enumerate(self.citizens.values()):
            household_id = household_ids[idx % len(household_ids)]
            citizen.household_id = household_id
            self.households[household_id].add_member(citizen.id)
        
        print(f"  Created {count} citizens in {len(self.households)} households")
        print(f"  Created {len(self.zones)} zones with environmental parameters")
        
        return count
    
    def _init_risk_factors(self, citizen: Citizen) -> Dict[str, int]:
        """
        Initialize risk factors for a citizen based on age and characteristics.
        
        Args:
            citizen: Citizen object
        
        Returns:
            Dictionary of risk factors
        """
        risk_factors = {rf: 0 for rf in Citizen.DEFAULT_RISK_FACTORS}
        
        age_years = citizen.age_years
        
        # Children have no risk factors
        if age_years < 15:
            return risk_factors
        
        # Smoking prevalence increases with age, peaks at 40-60, then decreases
        smoking_prob = 0.0
        if 20 <= age_years <= 70:
            peak_age = 45
            smoking_prob = 0.25 * (1 - ((age_years - peak_age) ** 2) / (50 ** 2))
            smoking_prob = max(smoking_prob, 0.10)
        if self.rng.random() < smoking_prob:
            risk_factors["smoking"] = 1
        
        # Obesity prevalence increases with age
        obesity_prob = 0.15 + (age_years - 20) * 0.008 if age_years > 20 else 0.05
        obesity_prob = min(obesity_prob, 0.45)
        if self.rng.random() < obesity_prob:
            risk_factors["obesity"] = 1
        
        # Physical inactivity increases with age
        inactivity_prob = 0.2 + (age_years - 20) * 0.005 if age_years > 20 else 0.1
        if self.rng.random() < inactivity_prob:
            risk_factors["physical_inactivity"] = 1
        
        # Alcohol abuse
        alcohol_prob = 0.08 if 20 <= age_years <= 65 else 0.02
        if self.rng.random() < alcohol_prob:
            risk_factors["alcohol_abuse"] = 1
        
        # High cholesterol increases with age
        cholesterol_prob = (age_years - 20) * 0.006 if age_years > 20 else 0.01
        if self.rng.random() < min(cholesterol_prob, 0.4):
            risk_factors["high_cholesterol"] = 1
        
        # Pre-hypertension stage
        hypertension_prob = (age_years - 30) * 0.008 if age_years > 30 else 0.01
        if self.rng.random() < min(hypertension_prob, 0.35):
            risk_factors["hypertension_stage0"] = 1
        
        # Family history (constant, independent of age)
        if self.rng.random() < 0.15:
            risk_factors["family_history"] = 1
        
        return risk_factors
    
    def run(self, months: int = 600) -> None:
        """
        Run the simulation for a specified number of months.
        
        Args:
            months: Number of months to simulate
        """
        print(f"Starting simulation for {months} months ({months/12:.1f} years)")
        print(f"Initial population: {len(self.citizens)} citizens")
        
        for month in range(months):
            self.step()
            
            # Collect yearly statistics
            if (month + 1) % 12 == 0:
                year = (month + 1) // 12
                self.collect_yearly_stats(year)
                if year % 5 == 0 or year == 1:
                    print(f"Year {year}: Population={len([c for c in self.citizens.values() if c.alive])}, "
                          f"Households={len(self.households)}")
        
        print(f"Simulation complete. Final population: {len([c for c in self.citizens.values() if c.alive])}")
    
    def step(self) -> None:
        """Execute one month of simulation."""
        self.current_month += 1
        
        # Age all citizens
        for citizen in self.citizens.values():
            if citizen.alive:
                citizen.age_one_month()
        
        # Handle deaths
        self.handle_deaths()
        
        # Handle births
        self.handle_births()
        
        # Handle household splits
        self.handle_household_splits()
    
    def handle_deaths(self) -> None:
        """Process deaths for all living citizens using mortality table and risk factors."""
        deaths = []
        
        for citizen_id, citizen in self.citizens.items():
            if not citizen.alive:
                continue
            
            # Get base mortality from table
            base_mortality = self._get_mortality_rate(citizen.age_years, citizen.sex)
            
            # Modify by disease burden
            disease_multiplier = 1.0 + (0.05 * citizen.num_conditions())
            disease_multiplier += 0.1 * citizen.disability_score
            
            # Modify by risk factors
            risk_multiplier = 1.0
            if citizen.risk_factors.get("smoking", 0) == 1:
                risk_multiplier *= 1.3
            if citizen.risk_factors.get("obesity", 0) == 1:
                risk_multiplier *= 1.15
            if citizen.risk_factors.get("alcohol_abuse", 0) == 1:
                risk_multiplier *= 1.25
            
            # Apply simulation multiplier
            total_mortality = (
                base_mortality * disease_multiplier * risk_multiplier * self.mortality_multiplier
            )
            
            # Clamp to valid probability
            total_mortality = min(max(total_mortality, 0.0), 1.0)
            
            if self.rng.random() < total_mortality:
                deaths.append(citizen_id)
        
        # Remove deceased from households
        for citizen_id in deaths:
            citizen = self.citizens[citizen_id]
            citizen.alive = False
            household = self.households.get(citizen.household_id)
            if household:
                household.remove_member(citizen_id)
    
    def handle_births(self) -> None:
        """Process births for eligible females using fertility table."""
        births = []
        
        for citizen in self.citizens.values():
            if citizen.alive and citizen.sex == "female":
                age_years = citizen.age_years
                annual_fertility = self._get_fertility_rate(age_years) * self.fertility_rate
                
                # Convert annual to monthly probability
                monthly_fertility = annual_fertility / 12.0
                
                # Reduce fertility based on disease burden
                disease_reduction = 1.0 - (0.05 * citizen.num_conditions() + 0.1 * citizen.disability_score)
                disease_reduction = max(disease_reduction, 0.0)
                
                monthly_fertility *= disease_reduction
                
                if self.rng.random() < monthly_fertility:
                    births.append(citizen)
        
        # Create newborns
        for mother in births:
            newborn_sex = self.rng.choice(["male", "female"])
            
            newborn = Citizen(
                sex=newborn_sex,
                age_months=0,
                household_id=mother.household_id,
                zone_id=mother.zone_id,
                diseases=self.disease_model.get_initial_diseases(),
            )
            
            # Newborns have no risk factors
            newborn.risk_factors = {rf: 0 for rf in Citizen.DEFAULT_RISK_FACTORS}
            
            self.citizens[newborn.id] = newborn
            
            household = self.households.get(mother.household_id)
            if household:
                household.add_member(newborn.id)
    
    def handle_household_splits(self) -> None:
        """
        Handle young adults leaving to form new households.
        
        Adults aged 25+ may leave their current household
        with some probability to form new households.
        """
        potential_movers = []
        
        for citizen in self.citizens.values():
            if (citizen.alive and 
                citizen.age_years >= 25 and 
                self.rng.random() < self.household_split_probability):
                potential_movers.append(citizen)
        
        # Move to new households
        for citizen in potential_movers:
            old_household = self.households.get(citizen.household_id)
            if old_household:
                old_household.remove_member(citizen.id)
            
            # Create new household
            zone_id = old_household.zone_id if old_household else 1
            new_household = Household(zone_id)
            self.households[new_household.id] = new_household
            new_household.add_member(citizen.id)
            citizen.household_id = new_household.id
    
    def collect_yearly_stats(self, year: int) -> None:
        """
        Collect population statistics for a given year.
        
        Args:
            year: Year number (1-50)
        """
        alive_citizens = [c for c in self.citizens.values() if c.alive]
        
        if not alive_citizens:
            self.yearly_stats[year] = {
                "total_population": 0,
                "num_households": 0,
                "average_household_size": 0,
                "num_males": 0,
                "num_females": 0,
                "age_pyramid": {},
            }
            return
        
        # Basic stats
        males = [c for c in alive_citizens if c.sex == "male"]
        females = [c for c in alive_citizens if c.sex == "female"]
        
        # Households with members
        active_households = [
            h for h in self.households.values() 
            if h.size() > 0 and any(
                self.citizens[m_id].alive for m_id in h.members 
                if m_id in self.citizens
            )
        ]
        
        avg_household_size = (
            sum(h.size() for h in active_households) / len(active_households)
            if active_households else 0
        )
        
        # Age pyramid (5-year bins)
        age_pyramid = self._build_age_pyramid(alive_citizens)
        
        self.yearly_stats[year] = {
            "total_population": len(alive_citizens),
            "num_households": len(active_households),
            "average_household_size": avg_household_size,
            "num_males": len(males),
            "num_females": len(females),
            "age_pyramid": age_pyramid,
            "multimorbidity_count": sum(
                1 for c in alive_citizens if c.has_multimorbidity()
            ),
            "average_disability_score": (
                sum(c.disability_score for c in alive_citizens) / len(alive_citizens)
            ) if alive_citizens else 0.0,
        }
    
    def _build_age_pyramid(self, citizens: List[Citizen]) -> Dict[str, Dict[str, int]]:
        """
        Build age pyramid data for visualization (5-year age bins from 0 to 90+).
        
        Args:
            citizens: List of citizens to include
        
        Returns:
            Dictionary with age bins and male/female counts
        """
        pyramid = {}
        
        # Create 5-year age bins from 0 to 90+
        for start_age in range(0, 90, 5):
            end_age = start_age + 5
            bin_name = f"{start_age}-{end_age-1}"
            
            males = sum(
                1 for c in citizens 
                if c.sex == "male" and start_age <= c.age_years < end_age
            )
            females = sum(
                1 for c in citizens 
                if c.sex == "female" and start_age <= c.age_years < end_age
            )
            
            pyramid[bin_name] = {"male": males, "female": females}
        
        # Add 90+ age group
        bin_name = "90+"
        males = sum(
            1 for c in citizens 
            if c.sex == "male" and c.age_years >= 90
        )
        females = sum(
            1 for c in citizens 
            if c.sex == "female" and c.age_years >= 90
        )
        pyramid[bin_name] = {"male": males, "female": females}
        
        return pyramid
    
    def get_statistics_summary(self) -> str:
        """Get a text summary of simulation statistics."""
        lines = ["=" * 70]
        lines.append("SIMULATION STATISTICS")
        lines.append("=" * 70)
        
        if not self.yearly_stats:
            lines.append("No statistics collected yet.")
            return "\n".join(lines)
        
        final_year = max(self.yearly_stats.keys())
        stats = self.yearly_stats[final_year]
        
        lines.append(f"Year: {final_year}")
        lines.append(f"Total Population: {stats['total_population']}")
        total_pop = max(stats['total_population'], 1)
        lines.append(f"Male: {stats['num_males']} ({stats['num_males']/total_pop*100:.1f}%)")
        lines.append(f"Female: {stats['num_females']} ({stats['num_females']/total_pop*100:.1f}%)")
        lines.append(f"Number of Households: {stats['num_households']}")
        lines.append(f"Average Household Size: {stats['average_household_size']:.2f}")
        lines.append(f"Multimorbidity Cases: {stats.get('multimorbidity_count', 0)}")
        lines.append(f"Average Disability Score: {stats.get('average_disability_score', 0.0):.3f}")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def apply_risk_factors(self) -> None:
        """
        Apply risk factors to citizens and update their disease probabilities.
        This method iterates through all citizens and adjusts their disease prevalence
        based on the defined risk factors in the DiseaseModel.
        """
        for citizen in self.citizens.values():
            for risk_factor, impacts in self.disease_model.get_risk_factors().items():
                if risk_factor in citizen.risk_factors:  # Check if citizen has this risk factor
                    for disease, impact in impacts.items():
                        if disease in citizen.diseases:
                            # Increase the probability of the disease based on the risk factor
                            current_prevalence = self.disease_model.get_prevalence(disease)
                            adjusted_prevalence = current_prevalence + (current_prevalence * impact)
                            self.disease_model.disease_prevalence[disease] = min(adjusted_prevalence, 100.0)
