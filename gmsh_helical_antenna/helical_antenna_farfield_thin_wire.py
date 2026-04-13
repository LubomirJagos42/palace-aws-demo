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
mesherObj.addStepfile("antenna", "stepfiles/helix_antenna_thin_wire.step", priority=5000)
mesherObj.addStepfile("port_in", "stepfiles/feed_port.step", priority=4000)
mesherObj.addStepfile("gnd", "stepfiles/gnd.step", priority=3000)

mesherObj.addGmshVolumeObject("airbox", gmsh.model.occ.addSphere(0,0,125, 350), priority=1000)
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

# field_threshold_wire = mesherObj.setSurfaceMeshSize(["antenna"], 0.5, 20.0, 0.0, 5.0)
field_threshold_wire = mesherObj.setSurfaceMeshSize(["antenna"], 0.7, 4.0, 0.0, 5.0)
field_threshold_gnd = mesherObj.setSurfaceMeshSize(["gnd"], 7.0, 20.0, 0.0, 5.0)

f_airbox = gmsh.model.mesh.field.add("Box")
gmsh.model.mesh.field.setNumber(f_airbox, "VIn",       45.0)   # mm — coarse inside airbox
gmsh.model.mesh.field.setNumber(f_airbox, "VOut",      45.0)   # same outside (don't care)
gmsh.model.mesh.field.setNumber(f_airbox, "XMin",     -65.0)
gmsh.model.mesh.field.setNumber(f_airbox, "XMax",      65.0)
gmsh.model.mesh.field.setNumber(f_airbox, "YMin",     -65.0)
gmsh.model.mesh.field.setNumber(f_airbox, "YMax",      65.0)
gmsh.model.mesh.field.setNumber(f_airbox, "ZMin",     -10.0)
gmsh.model.mesh.field.setNumber(f_airbox, "ZMax",      150.0)
gmsh.model.mesh.field.setNumber(f_airbox, "Thickness",  10.0)  # transition zone

field_constant_portIn = mesherObj.setSizeOnFace("port_in", 1.0)

f_min = gmsh.model.mesh.field.add("Min")
gmsh.model.mesh.field.setNumbers(f_min, "FieldsList", [
    field_threshold_wire,   # drives fine mesh on helix
    # field_threshold_gnd,    # drives coarse mesh on ground
    f_airbox,               # caps coarse mesh in far-field,
    field_constant_portIn
])
gmsh.model.mesh.field.setAsBackgroundMesh(f_min)


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
gmsh.write("mesh/antenna_model_thin_wire.msh")

print("PASS - Mesh generated and saved as mesh/antenna_model_thin_wire.msh")

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
simulationConfig["Problem"]["Output"] = "sim_result_thin_wire"

simulationConfig["Model"] = {}
simulationConfig["Model"]["Mesh"] = "mesh/antenna_model_thin_wire.msh"
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
simulationConfig["Solver"]["Driven"]["MinFreq"] = 1.5
simulationConfig["Solver"]["Driven"]["MaxFreq"] = 2.6
simulationConfig["Solver"]["Driven"]["FreqStep"] = 0.1
simulationConfig["Solver"]["Driven"]["SaveStep"] = 1
simulationConfig["Solver"]["Driven"]["AdaptiveTol"] = 1e-3

simulationConfig["Solver"]["Linear"] = {}
simulationConfig["Solver"]["Linear"]["Type"] = "Default"
simulationConfig["Solver"]["Linear"]["KSPType"] = "GMRES"
simulationConfig["Solver"]["Linear"]["Tol"] = 1e-3
simulationConfig["Solver"]["Linear"]["MaxIts"] = 100
simulationConfig["Solver"]["Order"] = 2
simulationConfig["Solver"]["Device"] = "CPU"

json.dump(simulationConfig, open("helix_antenna_s11_thin_wire.json", "w"), indent=2)

##########################################################################################################
# Generate Palace solver simulation for farfield .json file
##########################################################################################################

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
    "Freq": [2.400],
    "SaveStep": 1
})

#
#   Write simulation to .json file
#
json.dump(simulationConfig, open("helix_antenna_farfield_thin_wire.json", "w"), indent=2)
