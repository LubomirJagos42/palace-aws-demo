import json

from basicpalacesolverhelperpackage import BasicMfemMesher

##########################################################################################################
# Generate Palace solver simulation .json file
##########################################################################################################
gmshGroupId = {}
gmshGroupId["airbox_volume"] = 1000
gmshGroupId["antenna"] = 2000
gmshGroupId["gnd"] = 3000
gmshGroupId["port_in"] = 4000
gmshGroupId["airbox_surface"] = 5000

simulationConfig = {}

simulationConfig["Problem"] = {}
simulationConfig["Problem"]["Type"] = "Driven"
simulationConfig["Problem"]["Verbose"] = 3
simulationConfig["Problem"]["Output"] = "sim_result"

simulationConfig["Model"] = {}
simulationConfig["Model"]["Mesh"] = "mesh/antenna_model.msh"
simulationConfig["Model"]["L0"] = 1.0e-3

simulationConfig["Domains"] = {}
simulationConfig["Domains"]["Materials"] = []
simulationConfig["Domains"]["Materials"].append({
    "Attributes": [gmshGroupId["airbox_volume"]],
    "Permittivity": 1.0,
    "Permeability": 1.0,
    "LossTan": 0.0
})

simulationConfig["Boundaries"] = {}
simulationConfig["Boundaries"]["Absorbing"] = {"Attributes": [gmshGroupId["airbox_surface"]], "Order": 1}
simulationConfig["Boundaries"]["PEC"] = {"Attributes": [gmshGroupId["antenna"], gmshGroupId["gnd"]]}
simulationConfig["Boundaries"]["LumpedPort"] = []
simulationConfig["Boundaries"]["LumpedPort"].append({
    "Index": 1,
    "Attributes": [gmshGroupId["port_in"]],
    "Direction": "-Z",
    "R": 50.0,
    "Excitation": True
})

simulationConfig["Solver"] = {}
simulationConfig["Solver"]["Driven"] = {}

# farfield calculation at freq
simulationConfig["Boundaries"]["Postprocessing"] = {}
simulationConfig["Boundaries"]["Postprocessing"]["FarField"] = {
    "Attributes": [gmshGroupId["airbox_surface"]],
    "NSample": 64800,
    "ThetaPhis": [[35, 20]]
}
simulationConfig["Solver"]["Driven"]["Samples"] = {}
simulationConfig["Solver"]["Driven"]["Samples"]["Type"] = "Point"
simulationConfig["Solver"]["Driven"]["Samples"]["Freq"] = [1.866]
simulationConfig["Solver"]["Driven"]["Samples"]["SaveStep"] = 1


simulationConfig["Solver"]["Linear"] = {}
simulationConfig["Solver"]["Linear"]["Type"] = "Default"
simulationConfig["Solver"]["Linear"]["KSPType"] = "GMRES"
simulationConfig["Solver"]["Linear"]["Tol"] = 1e-3
simulationConfig["Solver"]["Linear"]["MaxIts"] = 100

simulationConfig["Solver"]["Order"] = 2

simulationConfig["Solver"]["Device"] = "CPU"

#
#   Write simulation to .json file
#
json.dump(simulationConfig, open("helix_antenna_farfield.json", "w"), indent=2)
