import gmsh

import os, sys
sys.path.append(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "utils"
))
from BasicMfemMesher import BasicMfemMesher

##########################################################################################################
# MAIN PROGRAM
##########################################################################################################
gmsh.initialize()
gmsh.model.add("patch_antenna")

mesherObj = BasicMfemMesher()

##########################################################################################################
# GEOMETRY
##########################################################################################################
mesherObj.addStepfile("substrate", "stepfiles/substrate.step", priority=2000)
mesherObj.addStepfile("gnd", "stepfiles/gnd.step", priority=3000)
mesherObj.addStepfile("patch", "stepfiles/patch.step", priority=4000)
mesherObj.addStepfile("port_in", "stepfiles/port_in.step", priority=5000)

mesherObj.addGmshVolumeObject("airbox", gmsh.model.occ.addSphere(0,0,0, 140), priority=1000)

mesherObj.cutVolumesInsideModel()
gmsh.model.occ.removeAllDuplicates()
gmsh.model.occ.synchronize()
mesherObj.performFragmentationAndReassignTags()

gmsh.model.occ.synchronize()
gmsh.fltk.run()

##########################################################################################################
# Create mesh size fields for patch and port
# Using distance field for the fine mesh near patch and port, coarser elsewhere
##########################################################################################################

field_threshold = mesherObj.setSurfaceMeshSize(["patch", "gnd"], 10.5, 35.0, 0.0, 5.0)
gmsh.model.mesh.field.setAsBackgroundMesh(field_threshold)

##########################################################################################################
# Define physical groups for volumes and surfaces
##########################################################################################################

mesherObj.createGroup("airbox", "airbox", 3, groupTag=1)
mesherObj.createGroup("substrate", "substrate", 3, groupTag=1000)
mesherObj.createGroup("patch", "patch", 2, groupTag=300)
mesherObj.createGroup("gnd", "gnd", 2, groupTag=301)
mesherObj.createGroup("port_in", "port_in", 2, groupTag=302)

# mesherObj.createGroup("farfield", "airbox", 2, groupTag=303)

airboxVolumeDimtag = mesherObj.getGeometryObject("airbox")["dimtags"][0]
_, gmshObjectBoundary = gmsh.model.occ.getSurfaceLoops(airboxVolumeDimtag[1])
boundaryTags = []
for tag in gmshObjectBoundary[0]:
    boundaryTags.append(tag)
gmsh.model.addPhysicalGroup(2, boundaryTags, tag=303, name="farfield")

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
