import json
import os

import gmsh
from basicpalacesolverhelperpackage import BasicMfemMesher

##########################################################################################################
# MAIN PROGRAM
##########################################################################################################
gmsh.initialize()
gmsh.model.add("patch_antenna")

mesherObj = BasicMfemMesher()

##########################################################################################################
# GEOMETRY
##########################################################################################################
mesherObj.addStepfile("antenna", "stepfiles/helix_antenna.step", priority=5000)
mesherObj.addStepfile("port_in", "stepfiles/feed_port.step", priority=4000)
mesherObj.addStepfile("gnd", "stepfiles/gnd.step", priority=3000)

mesherObj.addGmshVolumeObject("airbox", gmsh.model.occ.addSphere(0,0,125, 250), priority=1000)
# mesherObj.addGmshVolumeObject("airbox", gmsh.model.occ.addBox(-90,-90,-10, 180,180,260), priority=1000)

mesherObj.cutVolumesInsideModel()
gmsh.model.occ.removeAllDuplicates()
gmsh.model.occ.synchronize()
mesherObj.performFragmentationAndReassignTags()

gmsh.model.occ.synchronize()
# gmsh.fltk.run()

##########################################################################################################
# Create mesh size fields for patch and port
# Using distance field for the fine mesh near patch and port, coarser elsewhere
##########################################################################################################

# field_threshold_1 = mesherObj.setSurfaceMeshSize(["antenna"], 0.5, 1.5, 0.0, 2.0)
field_threshold_1 = mesherObj.setSurfaceMeshSize(["antenna"], 3.5, 10.0, 0.0, 2.0)
# field_threshold_2 = mesherObj.setSurfaceMeshSize(["airbox"], 15.0, 30.0, 0.0, 5.0)
# mesherObj.setSizeOnFace(["port_in"], 0.1)
gmsh.model.mesh.field.setAsBackgroundMesh(field_threshold_1)

##########################################################################################################
# Define physical groups for volumes and surfaces
##########################################################################################################
gmshGroupId = {}
gmshGroupId["airbox_volume"] = 1000
gmshGroupId["antenna"] = 2000
gmshGroupId["gnd"] = 3000
gmshGroupId["port_in"] = 4000
gmshGroupId["airbox_surface"] = 5000

mesherObj.createGroup("airbox_volume", "airbox", 3, groupTag=gmshGroupId["airbox_volume"])
mesherObj.createGroup("antenna", "antenna", 2, groupTag=gmshGroupId["antenna"])
mesherObj.createGroup("gnd", "gnd", 2, groupTag=gmshGroupId["gnd"])
mesherObj.createGroup("port_in", "port_in", 2, groupTag=gmshGroupId["port_in"])

# mesherObj.createGroup("airbox_surface", "airbox", 2, groupTag=5000)
airboxVolumeDimtag = mesherObj.getGeometryObject("airbox")["dimtags"][0]
_, gmshObjectBoundary = gmsh.model.occ.getSurfaceLoops(airboxVolumeDimtag[1])
boundaryTags = []
for tag in gmshObjectBoundary[0]:
    boundaryTags.append(tag)
gmsh.model.addPhysicalGroup(2, boundaryTags, tag=gmshGroupId["airbox_surface"], name="airbox_surface")

##########################################################################################################
# MESH GENERATE
##########################################################################################################
# gmsh directives
gmsh.option.setNumber("General.Terminal", 1)  # print messages
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.Binary", 0)       # text .msh file
# gmsh.option.setNumber("Mesh.Algorithm3D", 10)
gmsh.option.setNumber("Mesh.Algorithm3D", 1)    #delaunay

# Generate mesh
# gmsh.model.mesh.generate(2)
gmsh.model.mesh.generate(3)
try:
    os.mkdir("mesh")
except:
    pass
gmsh.write("mesh/antenna_model.msh")

print("PASS - Mesh generated and saved as mesh/antenna_model.msh")

##########################################################################################################
# Open generated msh file
##########################################################################################################
gmsh.fltk.run()

gmsh.clear()
gmsh.finalize()

##########################################################################################################
# Generate Palace solver simulation .json file
##########################################################################################################

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

# # frequency sweep for S11 plot
# simulationConfig["Solver"]["Driven"]["MinFreq"] = 1.7
# simulationConfig["Solver"]["Driven"]["MaxFreq"] = 2.1
# simulationConfig["Solver"]["Driven"]["FreqStep"] = 0.02
# simulationConfig["Solver"]["Driven"]["SaveStep"] = 1
# simulationConfig["Solver"]["Driven"]["AdaptiveTol"] = 1e-3

# farfield calculation at freq
simulationConfig["Boundaries"]["Postprocessing"] = {}
simulationConfig["Boundaries"]["Postprocessing"]["FarField"] = {
    "Attributes": [gmshGroupId["airbox_surface"]],
    "NSample": 64800,
    "ThetaPhis": [[35, 20]]
}
simulationConfig["Solver"]["Driven"]["Samples"] = []
simulationConfig["Solver"]["Driven"]["Samples"].append({
    "Type": "Point",
    "Freq": [1.860],
    "SaveStep": 1
})


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
json.dump(simulationConfig, open("helix_antenna.json", "w"), indent=2)
