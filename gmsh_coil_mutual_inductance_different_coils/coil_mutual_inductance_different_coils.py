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

mesherObj.addStepfile("coil_top", "stepfiles/top_coil.step", priority=9000)
mesherObj.addStepfile("coil_bottom", "stepfiles/bottom_coil.step", priority=8900)
mesherObj.addStepfile("port_in", "stepfiles/port_in.step", priority=8800)
mesherObj.addStepfile("port_out", "stepfiles/port_out.step", priority=8700)
mesherObj.addStepfile("coil_core", "stepfiles/coil_core.step", priority=8600)


#
#   Create in gmsh - airbox
#
mesherObj.addGmshVolumeObject("airbox", gmsh.model.occ.addSphere(0,0,0, 100), priority=8500)
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

# print("Temporarily ending script.")
# exit(0)

##########################################################################################################
# Create mesh size fields for patch and port
# Using distance field for the fine mesh near patch and port, coarser elsewhere
##########################################################################################################

field_threshold = mesherObj.setSurfaceMeshSize(["coil_top", "coil_bottom"], 0.5, 15.0, 0.0, 10.0)
gmsh.model.mesh.field.setAsBackgroundMesh(field_threshold)

# Also set global limits
gmsh.option.setNumber("Mesh.MeshSizeMin", 0.1)   # Absolute minimum
gmsh.option.setNumber("Mesh.MeshSizeMax", 10.0)  # Absolute maximum

##########################################################################################################
# Define physical groups for volumes and surfaces
##########################################################################################################

mesherObj.createGroup("airbox", "airbox", 3, groupTag=100)
mesherObj.createGroup("coil_core", "coil_core", 2, groupTag=200)
mesherObj.createGroup("coil_top", "coil_top", 2, groupTag=300)
mesherObj.createGroup("coil_bottom", "coil_bottom", 2, groupTag=400)
mesherObj.createGroup("port_in", "port_in", 2, groupTag=500)
mesherObj.createGroup("port_out", "port_out", 2, groupTag=600)

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
gmsh.write("simulation_config/coil_model.msh")

print("PASS - Mesh generated and saved as simulation_model/coil_model.msh")

##########################################################################################################
# Open generated msh file
##########################################################################################################
gmsh.fltk.run()

gmsh.clear()
gmsh.finalize()
