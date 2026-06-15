import sys, os
# Ensure the repo package is found before the thesis-leo/pyssem/ data directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'pyssem-repo'))
from pyssem.model import Model
import json

with open("configs/baseline.json") as f:
    sim = json.load(f)

p = sim["scenario_properties"]

# Pass SEP_mapping if it exists in the config
sep_mapping = sim.get("SEP_mapping", None)

model = Model(
    start_date=p["start_date"],
    simulation_duration=p["simulation_duration"],
    steps=p["steps"],
    min_altitude=p["min_altitude"],
    max_altitude=p["max_altitude"],
    n_shells=p["n_shells"],
    launch_function=p["launch_function"],
    integrator=p["integrator"],
    density_model=p["density_model"],
    LC=p["LC"],
    v_imp=p["v_imp"],
    fragment_spreading=p.get("fragment_spreading", False),
    parallel_processing=p.get("parallel_processing", False),
    baseline=p.get("baseline", False),
    launch_scenario=p.get("launch_scenario"),
    SEP_mapping=sep_mapping,
)

species_list = model.configure_species(sim["species"])

print("Running simulation...")
results = model.run_model()
print("Done.")
model.create_plots()
