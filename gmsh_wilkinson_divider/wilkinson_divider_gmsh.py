import json

import gmsh
from basicpalacesolverhelperpackage import BasicMfemMesher

##########################################################################################################
# SUPPORT FUNCTIONS
##########################################################################################################
mesherObj = BasicMfemMesher()

##########################################################################################################
# MAIN PROGRAM
##########################################################################################################
gmsh.initialize()
gmsh.model.add("patch_antenna")

# Set larger tolerance BEFORE creating geometry
gmsh.option.setNumber("Geometry.Tolerance", 1e-4)
gmsh.option.setNumber("Geometry.ToleranceBoolean", 1e-4)

# Enable geometry healing
gmsh.option.setNumber("Geometry.OCCFixDegenerated", 1)
gmsh.option.setNumber("Geometry.OCCFixSmallEdges", 1)
gmsh.option.setNumber("Geometry.OCCFixSmallFaces", 1)

##########################################################################################################
# GEOMETRY
##########################################################################################################
# mesherObj.addGmshVolumeObject("simbox", gmsh.model.occ.addBox(-25.0,-30.0,-5.0, 50.0, 50.0, 10.0), priority=1000)

mesherObj.addStepfile("wilkinson_trace", "stepfiles/wilkinson_trace.step", priority=6000)
mesherObj.addStepfile("gnd", "stepfiles/gnd.step", priority=5000)
mesherObj.addStepfile("port_in", "stepfiles/port_in.step", priority=4000)
mesherObj.addStepfile("port_out_1", "stepfiles/port_out_1.step", priority=3000)
mesherObj.addStepfile("port_out_2", "stepfiles/port_out_2.step", priority=2000)
mesherObj.addStepfile("substrate", "stepfiles/substrate.step", priority=1500)

mesherObj.addGmshVolumeObject("simbox", gmsh.model.occ.addBox(-25.0,-30.0,-5.0, 50.0, 50.0, 10.0), priority=1000)

gmsh.model.occ.synchronize()

#   Cut substrate from airbox
#   This also working OK using manager array for geometries
#
mesherObj.cutVolumesInsideModel()

gmsh.model.occ.removeAllDuplicates()
gmsh.model.occ.synchronize()

#
#   Whole model fragmentation
#
mesherObj.performFragmentationAndReassignTags()

gmsh.model.occ.synchronize()
gmsh.fltk.run()

##########################################################################################################
# Create mesh size fields for patch and port
# Using distance field for the fine mesh near patch and port, coarser elsewhere
##########################################################################################################

field_threshold = mesherObj.setSurfaceMeshSize(["wilkinson_trace", "gnd"], 1.0, 15.0, 0.0, 2.0)
gmsh.model.mesh.field.setAsBackgroundMesh(field_threshold)

# Also set global limits
gmsh.option.setNumber("Mesh.MeshSizeMin", 0.5)   # Absolute minimum
gmsh.option.setNumber("Mesh.MeshSizeMax", 30.0)  # Absolute maximum

##########################################################################################################
# Define physical groups for volumes and surfaces
##########################################################################################################

gmshGroupId = {}
gmshGroupId["wilkinson_trace"] = 100
gmshGroupId["gnd"] = 200
gmshGroupId["port_in"] = 300
gmshGroupId["port_out_1"] = 400
gmshGroupId["port_out_2"] = 500
gmshGroupId["substrate"] = 600
gmshGroupId["simbox"] = 700
gmshGroupId["simbox_surface"] = 801

mesherObj.createGroup("wilkinson_trace", "wilkinson_trace", 2, groupTag=gmshGroupId["wilkinson_trace"])
mesherObj.createGroup("gnd", "gnd", 2, groupTag=gmshGroupId["gnd"])
mesherObj.createGroup("port_in", "port_in", 2, groupTag=gmshGroupId["port_in"])
mesherObj.createGroup("port_out_1", "port_out_1", 2, groupTag=gmshGroupId["port_out_1"])
mesherObj.createGroup("port_out_2", "port_out_2", 2, groupTag=gmshGroupId["port_out_2"])
mesherObj.createGroup("substrate", "substrate", 3, groupTag=gmshGroupId["substrate"])
mesherObj.createGroup("simbox", "simbox", 3, groupTag=gmshGroupId["simbox"])

# Warning: Use this just when volume is added BEFORE STEP FILES!!!
# Erorr: Still wrong as seems like there is wrong dimtags assignment to original object after fragmentation
# mesherObj.createGroup("simbox_surface", "simbox", 2, groupTag=800)

# Warning: Use this just when volume is added AFTER STEP FILES!!!
airboxVolumeDimtag = mesherObj.getGeometryObject("simbox")["dimtags"][0]
_, gmshObjectBoundary = gmsh.model.occ.getSurfaceLoops(airboxVolumeDimtag[1])
boundaryTags = []
for tag in gmshObjectBoundary[0]:
    boundaryTags.append(tag)
gmsh.model.addPhysicalGroup(2, boundaryTags, tag=gmshGroupId["simbox_surface"], name="simbox_surface")

##########################################################################################################
# MESH GENERATE
##########################################################################################################
# gmsh directives
gmsh.option.setNumber("General.Terminal", 1)  # print messages
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.Binary", 0)       # text .msh file
# gmsh.option.setNumber("Mesh.Algorithm3D", 10)
gmsh.option.setNumber("Mesh.Algorithm3D", 1)    #delaunay

gmsh.model.occ.removeAllDuplicates()
gmsh.model.occ.synchronize()

# Generate mesh
gmsh.model.mesh.generate(3)
gmsh.write("mesh/wilkinson_divider.msh")

print("PASS - Mesh generated and saved as mesh/wilkinson_divider.msh")

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
simulationConfig["Model"]["Mesh"] = "mesh/wilkinson_divider.msh"
simulationConfig["Model"]["L0"] = 1.0e-3

simulationConfig["Domains"] = {}
simulationConfig["Domains"]["Materials"] = []
simulationConfig["Domains"]["Materials"].append({
    "Attributes": [gmshGroupId["simbox"]],
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
simulationConfig["Boundaries"]["Absorbing"] = {"Attributes": [gmshGroupId["simbox_surface"]], "Order": 1}
simulationConfig["Boundaries"]["PEC"] = {"Attributes": [gmshGroupId["wilkinson_trace"], gmshGroupId["gnd"]]}
simulationConfig["Boundaries"]["LumpedPort"] = []
simulationConfig["Boundaries"]["LumpedPort"].append({
    "Index": 1,
    "Attributes": [gmshGroupId["port_in"]],
    "Direction": "Z",
    "R": 50.0,
    "Excitation": True
})
simulationConfig["Boundaries"]["LumpedPort"].append({
    "Index": 2,
    "Attributes": [gmshGroupId["port_out_1"]],
    "Direction": "Z",
    "R": 50.0,
    "Excitation": False
})
simulationConfig["Boundaries"]["LumpedPort"].append({
    "Index": 3,
    "Attributes": [gmshGroupId["port_out_2"]],
    "Direction": "Z",
    "R": 50.0,
    "Excitation": False
})

simulationConfig["Solver"] = {}
simulationConfig["Solver"]["Driven"] = {}
simulationConfig["Solver"]["Driven"]["MinFreq"] = 0.5
simulationConfig["Solver"]["Driven"]["MaxFreq"] = 4.0
simulationConfig["Solver"]["Driven"]["FreqStep"] = 0.3
simulationConfig["Solver"]["Driven"]["SaveStep"] = 1
simulationConfig["Solver"]["Driven"]["AdaptiveTol"] = 1e-3

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
json.dump(simulationConfig, open("wilkinson_divider_transfer.json", "w"), indent=2)
