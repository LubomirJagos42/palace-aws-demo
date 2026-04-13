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

mm = 0.001

##########################################################################################################
# GEOMETRY
##########################################################################################################
mesherObj.addStepfile("port_in", "stepfiles/feed_port_gen_model.step", priority=8000)
mesherObj.addStepfile("antenna", "stepfiles/antenna_gen_model.step", priority=7000)
mesherObj.addStepfile("gnd", "stepfiles/top_gnd_gen_model.step", priority=6000)
mesherObj.addStepfile("substrate", "stepfiles/substrate_gen_model.step", priority=5000)

mesherObj.addGmshVolumeObject("airbox", gmsh.model.occ.addSphere(40,-37,0.0, 120), priority=1000)

mesherObj.cutVolumesInsideModel()
gmsh.model.occ.removeAllDuplicates()
gmsh.model.occ.synchronize()
mesherObj.performFragmentationAndReassignTags()
gmsh.model.occ.removeAllDuplicates()

gmsh.model.occ.synchronize()
# gmsh.fltk.run()

mesherObj.getGeometryObject("antenna")["dimtags"].remove((2,13))
mesherObj.getGeometryObject("gnd")["dimtags"].remove((2,11))

##########################################################################################################
# Create mesh size fields for patch and port
# Using distance field for the fine mesh near patch and port, coarser elsewhere
##########################################################################################################

# field_antenna = mesherObj.setSurfaceMeshSize(["antenna"], 1.5, 10.0, 0.0, 5.0)
# field_gnd = mesherObj.setSurfaceMeshSize(["gnd"], 3.0, 10.0, 0.0, 5.0)
field_antenna = mesherObj.setSizeOnFace(["antenna"], 2.0)
field_gnd = mesherObj.setSizeOnFace(["gnd"], 5.0)
field_port_in = mesherObj.setSizeOnFace(["port_in"], 0.2)

f_airbox = gmsh.model.mesh.field.add("Ball")
gmsh.model.mesh.field.setNumber(f_airbox, "VIn",        13.0)   # mm inside sphere
gmsh.model.mesh.field.setNumber(f_airbox, "VOut",       13.0)   # mm outside sphere
gmsh.model.mesh.field.setNumber(f_airbox, "Radius",    120.0)   # mm
gmsh.model.mesh.field.setNumber(f_airbox, "XCenter",     40.0)
gmsh.model.mesh.field.setNumber(f_airbox, "YCenter",     37.0)
gmsh.model.mesh.field.setNumber(f_airbox, "ZCenter",     0.0)
gmsh.model.mesh.field.setNumber(f_airbox, "Thickness",  10.0)   # transition zone mm
field_constant_portIn = mesherObj.setSizeOnFace("port_in", 1.0)

f_min = gmsh.model.mesh.field.add("Min")
gmsh.model.mesh.field.setNumbers(f_min, "FieldsList", [
    field_antenna,
    field_gnd,
    field_port_in,
    f_airbox
])
gmsh.model.mesh.field.setAsBackgroundMesh(f_min)

# gmsh.model.mesh.field.setAsBackgroundMesh(f_airbox)


# ── 7. Disable gmsh automatic sizing overrides ──────────
gmsh.option.setNumber("Mesh.MeshSizeFromPoints",             0)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature",          0)
gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary",     0)

##########################################################################################################
# Define physical groups for volumes and surfaces
##########################################################################################################
gmshGroupId = {}
gmshGroupId["airbox_volume"] = 1000
gmshGroupId["antenna"] = 2000
gmshGroupId["gnd"] = 3000
gmshGroupId["substrate"] = 3500
gmshGroupId["port_in"] = 4000
gmshGroupId["airbox_surface"] = 5000

mesherObj.createGroup("airbox_volume", "airbox", 3, groupTag=gmshGroupId["airbox_volume"])
mesherObj.createGroup("substrate", "substrate", 3, groupTag=gmshGroupId["substrate"])
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
simulationConfig["Problem"]["Output"] = "sim_result_s11"

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
simulationConfig["Domains"]["Materials"].append({
    "Attributes": [gmshGroupId["substrate"]],
    "Permittivity": 4.2,
    "Permeability": 1.0,
    "LossTan": 0.02
})

simulationConfig["Boundaries"] = {}
simulationConfig["Boundaries"]["Absorbing"] = {"Attributes": [gmshGroupId["airbox_surface"]], "Order": 1}
simulationConfig["Boundaries"]["PEC"] = {"Attributes": [gmshGroupId["antenna"], gmshGroupId["gnd"]]}
simulationConfig["Boundaries"]["LumpedPort"] = []
simulationConfig["Boundaries"]["LumpedPort"].append({
    "Index": 1,
    "Attributes": [gmshGroupId["port_in"]],
    "Direction": "-Y",
    "R": 50.0,
    "Excitation": True
})

simulationConfig["Solver"] = {}
simulationConfig["Solver"]["Driven"] = {}

# frequency sweep for S11 plot
simulationConfig["Solver"]["Driven"]["MinFreq"] = 1.5
simulationConfig["Solver"]["Driven"]["MaxFreq"] = 3.0
simulationConfig["Solver"]["Driven"]["FreqStep"] = 0.05
simulationConfig["Solver"]["Driven"]["SaveStep"] = 1
simulationConfig["Solver"]["Driven"]["AdaptiveTol"] = 1e-3

simulationConfig["Solver"]["Linear"] = {}
simulationConfig["Solver"]["Linear"]["Type"] = "Default"
simulationConfig["Solver"]["Linear"]["KSPType"] = "GMRES"
simulationConfig["Solver"]["Linear"]["Tol"] = 1e-3
simulationConfig["Solver"]["Linear"]["MaxIts"] = 200

simulationConfig["Solver"]["Order"] = 2

simulationConfig["Solver"]["Device"] = "CPU"

#
#   Write simulation to .json file
#
json.dump(simulationConfig, open("inverted_f_antenna_s11.json", "w"), indent=2)

##################################################################################################################
# farfield calculation at freq
##################################################################################################################
simulationConfig["Problem"]["Output"] = "sim_result_farfield"

simulationConfig["Boundaries"]["Postprocessing"] = {}
simulationConfig["Boundaries"]["Postprocessing"]["FarField"] = {
    "Attributes": [gmshGroupId["airbox_surface"]],
    "NSample": 64800,
    "ThetaPhis": [[35, 20]]
}
simulationConfig["Solver"]["Driven"] = {}
simulationConfig["Solver"]["Driven"]["Samples"] = []
simulationConfig["Solver"]["Driven"]["Samples"].append({
    "Type": "Point",
    "Freq": [2.200],
    "SaveStep": 1
})

json.dump(simulationConfig, open("inverted_f_antenna_farfield.json", "w"), indent=2)
