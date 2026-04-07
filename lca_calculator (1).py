"""
Life Cycle Assessment (LCA) Calculator
Coffee Supply Chain Analysis
ISO 14040/44 Compliant

Author: Goutam Raman
Created: April 2026
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple
import json
from pathlib import Path


@dataclass
class ImpactFactor:
    """Impact factor for a given process and impact category"""
    process: str
    impact_category: str
    value: float
    unit: str
    source: str
    
    def __repr__(self):
        return f"{self.process}: {self.value} {self.unit} ({self.impact_category})"


@dataclass
class LifecycleStage:
    """Represents a single lifecycle stage with inputs and outputs"""
    name: str
    description: str
    inputs: Dict[str, float]  # {material: kg}
    outputs: Dict[str, float]  # {product: kg}
    energy_inputs: Dict[str, float]  # {energy_type: kWh}
    water_inputs: float  # m³
    
    def __repr__(self):
        return f"LifecycleStage: {self.name}"


class CoffeeProductLCA:
    """
    Life Cycle Assessment model for coffee production
    Follows ISO 14040/44 standards
    """
    
    # Impact categories (kg unit per 1 kg coffee)
    IMPACT_CATEGORIES = {
        'GWP': 'kg CO₂-eq',      # Global Warming Potential
        'AP': 'kg SO₂-eq',       # Acidification Potential
        'EP': 'kg PO₄³⁻-eq',     # Eutrophication Potential
        'WD': 'm³',              # Water Depletion
        'LU': 'm²·year'          # Land Use
    }
    
    def __init__(self, scenario: str = 'conventional', 
                 functional_unit: str = '1 kg coffee (roasted)'):
        """
        Initialize LCA Calculator
        
        Args:
            scenario: 'conventional' or 'sustainable'
            functional_unit: Reference unit for analysis
        """
        self.scenario = scenario
        self.functional_unit = functional_unit
        self.lifecycle_stages = {}
        self.impact_factors = {}
        self.results = {}
        self.sensitivity_analysis_results = {}
        
        # Initialize lifecycle stages
        self._initialize_lifecycle_stages()
    
    def _initialize_lifecycle_stages(self):
        """Initialize the main lifecycle stages for coffee production"""
        
        # Stage 1: Agricultural Production
        self.lifecycle_stages['agricultural'] = LifecycleStage(
            name='Agricultural Production',
            description='Farm-level cultivation and harvesting',
            inputs={
                'nitrogen_fertilizer': 0.12 if self.scenario == 'conventional' else 0.05,
                'phosphate_fertilizer': 0.03 if self.scenario == 'conventional' else 0.01,
                'potassium_fertilizer': 0.08 if self.scenario == 'conventional' else 0.02,
                'pesticides': 0.015 if self.scenario == 'conventional' else 0.0,
                'fungicides': 0.008 if self.scenario == 'conventional' else 0.0,
            },
            outputs={'wet_coffee_beans': 1.3},  # ~1.3 kg wet beans per kg dried
            energy_inputs={'diesel': 2.5},  # kWh per kg wet beans
            water_inputs=0.8  # m³ per kg wet beans
        )
        
        # Stage 2: Wet Processing (Milling)
        self.lifecycle_stages['wet_processing'] = LifecycleStage(
            name='Wet Processing',
            description='Coffee mill operations (fermentation, washing, drying)',
            inputs={'wet_coffee_beans': 1.3},
            outputs={'dried_coffee_beans': 1.0},
            energy_inputs={
                'electricity': 0.8,
                'natural_gas': 1.2
            },
            water_inputs=0.5  # m³ per kg output
        )
        
        # Stage 3: Roasting & Packaging
        self.lifecycle_stages['roasting_packaging'] = LifecycleStage(
            name='Roasting & Packaging',
            description='Roasting facility and packaging operations',
            inputs={
                'dried_coffee_beans': 1.0,
                'packaging_material': 0.012  # kg (varies by type)
            },
            outputs={'packaged_coffee': 1.012},
            energy_inputs={'electricity': 0.5, 'natural_gas': 0.3},
            water_inputs=0.01
        )
        
        # Stage 4: Transport & Distribution
        self.lifecycle_stages['transport'] = LifecycleStage(
            name='Transport & Distribution',
            description='From farm gate to consumer (warehouse, last-mile)',
            inputs={'packaged_coffee': 1.012},
            outputs={'coffee_at_consumer': 1.012},
            energy_inputs={'diesel': 0.15, 'fuel_oil': 0.08},  # kWh equivalent
            water_inputs=0.0
        )
        
        # Stage 5: Consumption & End-of-Life
        self.lifecycle_stages['consumption'] = LifecycleStage(
            name='Consumption & End-of-Life',
            description='Brewing process and disposal/composting',
            inputs={'coffee_at_consumer': 1.0},
            outputs={'spent_grounds': 0.95, 'packaging_waste': 0.012},
            energy_inputs={'electricity': 0.08},  # Water heating
            water_inputs=0.08  # m³ (water for brewing)
        )
    
    def _get_emission_factors(self) -> Dict[str, Dict[str, float]]:
        """
        Get emission factors for different materials and processes
        Values based on ECOINVENT 3.8 and Agribalyse databases
        """
        
        factors = {
            # Fertilizers (kg CO2-eq per kg applied)
            'nitrogen_fertilizer': {'GWP': 1.9, 'AP': 0.012, 'EP': 0.005, 'WD': 0.0},
            'phosphate_fertilizer': {'GWP': 0.5, 'AP': 0.002, 'EP': 0.001, 'WD': 0.0},
            'potassium_fertilizer': {'GWP': 0.3, 'AP': 0.001, 'EP': 0.0005, 'WD': 0.0},
            
            # Pesticides (kg CO2-eq per kg applied)
            'pesticides': {'GWP': 4.5, 'AP': 0.015, 'EP': 0.008, 'WD': 0.0},
            'fungicides': {'GWP': 3.8, 'AP': 0.012, 'EP': 0.006, 'WD': 0.0},
            
            # Energy sources (kg CO2-eq per kWh)
            'electricity': {'GWP': 0.4, 'AP': 0.002, 'EP': 0.0015, 'WD': 0.001},
            'diesel': {'GWP': 0.267, 'AP': 0.001, 'EP': 0.0008, 'WD': 0.0},
            'natural_gas': {'GWP': 0.202, 'AP': 0.0008, 'EP': 0.0005, 'WD': 0.0},
            'fuel_oil': {'GWP': 0.318, 'AP': 0.0015, 'EP': 0.001, 'WD': 0.0},
            
            # Packaging (kg CO2-eq per kg)
            'packaging_material': {'GWP': 1.2, 'AP': 0.005, 'EP': 0.003, 'WD': 0.05},
            
            # Water impacts (m³ per m³)
            'water_consumption': {'GWP': 0.0, 'AP': 0.0, 'EP': 0.001, 'WD': 1.0, 'LU': 0.0}
        }
        
        return factors
    
    def calculate_lci(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate Life Cycle Inventory (LCI)
        Quantifies all inputs and outputs through the lifecycle
        """
        
        lci_results = {}
        emission_factors = self._get_emission_factors()
        
        for stage_name, stage in self.lifecycle_stages.items():
            lci_results[stage_name] = {
                'inputs': stage.inputs,
                'outputs': stage.outputs,
                'energy': stage.energy_inputs,
                'water': stage.water_inputs
            }
        
        self.lci_results = lci_results
        return lci_results
    
    def assess_impacts(self) -> Dict[str, Dict[str, float]]:
        """
        Assess environmental impacts based on LCI
        Calculates all impact categories for the lifecycle
        """
        
        emission_factors = self._get_emission_factors()
        impact_results = {cat: 0.0 for cat in self.IMPACT_CATEGORIES.keys()}
        stage_impacts = {}
        
        # Process each lifecycle stage
        for stage_name, stage in self.lifecycle_stages.items():
            stage_impact = {cat: 0.0 for cat in self.IMPACT_CATEGORIES.keys()}
            
            # Calculate impacts from material inputs
            for material, quantity in stage.inputs.items():
                if material in emission_factors:
                    for impact_cat, value in emission_factors[material].items():
                        stage_impact[impact_cat] += quantity * value
            
            # Calculate impacts from energy inputs
            for energy_type, quantity_kwh in stage.energy_inputs.items():
                if energy_type in emission_factors:
                    for impact_cat, factor in emission_factors[energy_type].items():
                        stage_impact[impact_cat] += quantity_kwh * factor
            
            # Calculate impacts from water consumption
            if stage.water_inputs > 0:
                water_factor = emission_factors['water_consumption']
                for impact_cat, factor in water_factor.items():
                    stage_impact[impact_cat] += stage.water_inputs * factor
            
            # Sum to total
            for impact_cat in self.IMPACT_CATEGORIES.keys():
                impact_results[impact_cat] += stage_impact[impact_cat]
            
            stage_impacts[stage_name] = stage_impact
        
        self.results = impact_results
        self.stage_impacts = stage_impacts
        
        return impact_results
    
    def calculate_hotspots(self) -> Dict[str, Tuple[str, float]]:
        """
        Identify hotspots - stages with greatest environmental impact
        """
        hotspots = {}
        
        if not self.stage_impacts:
            self.assess_impacts()
        
        for impact_cat in self.IMPACT_CATEGORIES.keys():
            max_stage = None
            max_value = 0
            
            for stage_name, impacts in self.stage_impacts.items():
                if impacts[impact_cat] > max_value:
                    max_value = impacts[impact_cat]
                    max_stage = stage_name
            
            hotspots[impact_cat] = (max_stage, max_value)
        
        return hotspots
    
    def sensitivity_analysis(self, 
                            variable: str = 'nitrogen_fertilizer',
                            variation_range: Tuple[float, float] = (0.8, 1.2),
                            steps: int = 5) -> Dict[str, List[float]]:
        """
        Perform sensitivity analysis on key variables
        
        Args:
            variable: Variable to test (e.g., 'nitrogen_fertilizer')
            variation_range: Tuple of (min_multiplier, max_multiplier)
            steps: Number of steps in the range
        
        Returns:
            Dictionary of impact categories with results across range
        """
        
        results = {cat: [] for cat in self.IMPACT_CATEGORIES.keys()}
        variations = np.linspace(variation_range[0], variation_range[1], steps)
        
        original_value = self.lifecycle_stages['agricultural'].inputs.get(variable)
        
        for multiplier in variations:
            # Modify the variable
            self.lifecycle_stages['agricultural'].inputs[variable] = original_value * multiplier
            
            # Recalculate
            impacts = self.assess_impacts()
            for cat in self.IMPACT_CATEGORIES.keys():
                results[cat].append(impacts[cat])
        
        # Restore original
        self.lifecycle_stages['agricultural'].inputs[variable] = original_value
        
        self.sensitivity_analysis_results[variable] = {
            'variations': list(variations),
            'results': results
        }
        
        return results
    
    def get_results_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame for easy analysis"""
        
        if not self.results:
            self.assess_impacts()
        
        data = {
            'Impact Category': list(self.IMPACT_CATEGORIES.keys()),
            'Value': list(self.results.values()),
            'Unit': list(self.IMPACT_CATEGORIES.values()),
            'Scenario': [self.scenario] * len(self.IMPACT_CATEGORIES)
        }
        
        return pd.DataFrame(data)
    
    def get_stage_breakdown(self) -> pd.DataFrame:
        """Get breakdown of impacts by lifecycle stage"""
        
        if not self.stage_impacts:
            self.assess_impacts()
        
        data = []
        for stage_name, impacts in self.stage_impacts.items():
            for impact_cat, value in impacts.items():
                data.append({
                    'Stage': stage_name,
                    'Impact Category': impact_cat,
                    'Value': value,
                    'Unit': self.IMPACT_CATEGORIES[impact_cat]
                })
        
        return pd.DataFrame(data)
    
    def generate_report(self, output_path: str = 'lca_report.txt'):
        """Generate a comprehensive LCA report"""
        
        if not self.results:
            self.assess_impacts()
        
        report = f"""
{'='*80}
LIFE CYCLE ASSESSMENT REPORT
Coffee Supply Chain Analysis
ISO 14040/44 Compliant
{'='*80}

GOAL AND SCOPE
Functional Unit: {self.functional_unit}
Scenario: {self.scenario.upper()}
Scope: Cradle-to-grave (farm to consumption)

LIFECYCLE STAGES
1. Agricultural Production
2. Wet Processing (Milling)
3. Roasting & Packaging
4. Transport & Distribution
5. Consumption & End-of-Life

IMPACT ASSESSMENT RESULTS
{'-'*80}
"""
        
        for impact_cat, value in self.results.items():
            unit = self.IMPACT_CATEGORIES[impact_cat]
            report += f"{impact_cat:5} ({unit:15}): {value:.4f}\n"
        
        report += f"\n{'='*80}\nSTAGE BREAKDOWN\n{'-'*80}\n"
        
        for stage_name, impacts in self.stage_impacts.items():
            report += f"\n{stage_name.upper()}:\n"
            for impact_cat, value in impacts.items():
                unit = self.IMPACT_CATEGORIES[impact_cat]
                percentage = (value / self.results[impact_cat] * 100) if self.results[impact_cat] > 0 else 0
                report += f"  {impact_cat}: {value:.4f} {unit} ({percentage:.1f}%)\n"
        
        hotspots = self.calculate_hotspots()
        report += f"\n{'='*80}\nHOTSPOT ANALYSIS\n{'-'*80}\n"
        for impact_cat, (stage, value) in hotspots.items():
            report += f"{impact_cat}: {stage} ({value:.4f})\n"
        
        report += f"\n{'='*80}\nINTERPRETATION\n{'-'*80}\n"
        report += "Key findings and recommendations for sustainability improvements.\n"
        report += f"{'='*80}\n"
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write(report)
        
        return report


class ComparativeLCA:
    """Compare multiple scenarios"""
    
    def __init__(self, scenarios: List[str]):
        self.scenarios = scenarios
        self.models = {}
        
        for scenario in scenarios:
            self.models[scenario] = CoffeeProductLCA(scenario=scenario)
    
    def run_all(self):
        """Run LCA for all scenarios"""
        for model in self.models.values():
            model.assess_impacts()
    
    def get_comparison_dataframe(self) -> pd.DataFrame:
        """Compare results across scenarios"""
        self.run_all()
        
        data = []
        for scenario, model in self.models.items():
            for impact_cat, value in model.results.items():
                data.append({
                    'Scenario': scenario,
                    'Impact Category': impact_cat,
                    'Value': value,
                    'Unit': model.IMPACT_CATEGORIES[impact_cat]
                })
        
        return pd.DataFrame(data)
    
    def calculate_improvements(self, baseline: str = 'conventional', 
                              target: str = 'sustainable') -> pd.DataFrame:
        """Calculate percentage improvements between scenarios"""
        
        self.run_all()
        
        baseline_results = self.models[baseline].results
        target_results = self.models[target].results
        
        data = []
        for impact_cat in baseline_results.keys():
            baseline_val = baseline_results[impact_cat]
            target_val = target_results[impact_cat]
            
            if baseline_val > 0:
                improvement = ((baseline_val - target_val) / baseline_val) * 100
            else:
                improvement = 0
            
            data.append({
                'Impact Category': impact_cat,
                'Baseline': baseline_val,
                'Target': target_val,
                'Improvement %': improvement
            })
        
        return pd.DataFrame(data)


# Example usage
if __name__ == "__main__":
    # Create LCA models for both scenarios
    conventional_lca = CoffeeProductLCA(scenario='conventional')
    sustainable_lca = CoffeeProductLCA(scenario='sustainable')
    
    # Calculate impacts
    print("Calculating impacts...")
    conv_results = conventional_lca.assess_impacts()
    sust_results = sustainable_lca.assess_impacts()
    
    # Print results
    print("\n" + "="*60)
    print("CONVENTIONAL SCENARIO RESULTS")
    print("="*60)
    for cat, value in conv_results.items():
        unit = conventional_lca.IMPACT_CATEGORIES[cat]
        print(f"{cat}: {value:.4f} {unit}")
    
    print("\n" + "="*60)
    print("SUSTAINABLE SCENARIO RESULTS")
    print("="*60)
    for cat, value in sust_results.items():
        unit = sustainable_lca.IMPACT_CATEGORIES[cat]
        print(f"{cat}: {value:.4f} {unit}")
    
    # Compare scenarios
    print("\n" + "="*60)
    print("IMPROVEMENTS (Sustainable vs. Conventional)")
    print("="*60)
    for cat in conv_results.keys():
        improvement = ((conv_results[cat] - sust_results[cat]) / conv_results[cat]) * 100
        print(f"{cat}: {improvement:.1f}% reduction")
    
    # Sensitivity analysis
    print("\n" + "="*60)
    print("SENSITIVITY ANALYSIS: Nitrogen Fertilizer")
    print("="*60)
    sensitivity = conventional_lca.sensitivity_analysis('nitrogen_fertilizer')
    print(f"GWP variations: {sensitivity['GWP']}")
    
    # Generate reports
    conventional_lca.generate_report('lca_report_conventional.txt')
    sustainable_lca.generate_report('lca_report_sustainable.txt')
