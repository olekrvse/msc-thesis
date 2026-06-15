"""
Sweep Pm (post-mission disposal effectiveness) from 0.5 to 0.99.
Purpose: confirm disposal compliance affects debris trajectory as expected.
"""
from pyssem.model import Model
import json
import os
import copy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "configs", "baseline.json")

with open(CONFIG_PATH) as f:
    base_config = json.load(f)

PM_VALUES = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]

for pm in PM_VALUES:
    print(f"\n--- Running Pm = {pm} ---")
    
    config = copy.deepcopy(base_config)
    
    # Set Pm for the active satellite species
    for species in config["species"]:
        if species.get("active", False):
            species["Pm"] = pm
    
    props = config["scenario_properties"]
    
    model = Model(
        start_date=props["start_date"],
        simulation_duration=props["simulation_duration"],
        steps=props["steps"],
        min_altitude=props["min_altitude"],
        max_altitude=props["max_altitude"],
        n_shells=props["n_shells"],
        launch_function=props["launch_function"],
        integrator=props["integrator"],
        density_model=props["density_model"],
        LC=props["LC"],
        v_imp=props["v_imp"],
        fragment_spreading=False,
        parallel_processing=False,
        baseline=False,
    )
    
    species_list = model.configure_species(config["species"])
    results = model.run_model()
    
    # TODO: extract key metrics from results and store
    # You'll need to inspect what results contains after the first run
    print(f"Pm = {pm}: simulation complete")

print("\nAll Pm runs complete.")