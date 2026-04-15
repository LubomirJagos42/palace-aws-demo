import gmsh
from basicpalacesolverhelperpackage import BasicMfemMesher

##########################################################################################################
# MAIN PROGRAM
##########################################################################################################
gmsh.initialize()
gmsh.model.add("test_dimtags_after_cutting")

mesherObj = BasicMfemMesher()

##########################################################################################################
# GEOMETRY
##########################################################################################################
# mesherObj.addGmshVolumeObject("sphere_1", gmsh.model.occ.addBox(70,0, 0,50, 50, 50), priority=8000)
# mesherObj.addGmshVolumeObject("sphere_2", gmsh.model.occ.addBox(80,30, 0,50, 50, 50), priority=6000)

mesherObj.addGmshVolumeObject("sphere_1", gmsh.model.occ.addSphere(90,0,0, 25), priority=8000)
mesherObj.addGmshVolumeObject("sphere_2", gmsh.model.occ.addSphere(90,0,20, 25), priority=6000)

mesherObj.addGmshVolumeObject("box_1", gmsh.model.occ.addBox(-90,-90,-10, 180,180,260), priority=4000)
gmsh.model.occ.synchronize()

sphereObj = mesherObj.getGeometryObject("sphere_1")
boxObj = mesherObj.getGeometryObject("box_1")

print()
print(f"Dimtags before cutting:")
print(f"sphere: {sphereObj['dimtags']}")
print(f"box: {boxObj['dimtags']}")

# mesherObj.cutVolumesInsideModel()
mesherObj.cutOnlyVolumesInModelBetweenEachOther(allowSurfacesToBeCutted=True)
print()
print(f"Dimtags after cutting:")
print(f"sphere: {sphereObj['dimtags']}")
print(f"box: {boxObj['dimtags']}")

# gmsh.model.occ.removeAllDuplicates()
gmsh.model.occ.synchronize()
mesherObj.performFragmentationAndReassignTags(renewVolumeSurfaces=True)

print()
print(f"Dimtags after fragmentation:")
print(f"sphere: {sphereObj['dimtags']}")
print(f"box: {boxObj['dimtags']}")

print()
print(f"GMSH all entities:")
print(f"2D: {gmsh.model.getEntities(2)}")
print(f"3D: {gmsh.model.getEntities(3)}")

mesherObj.createGroup("mySphere", "sphere_1", 3)
mesherObj.createGroup("mySphere2", "sphere_2", 3)
mesherObj.createGroup("myBox", "box_1", 3)

# field_surface_sphere = mesherObj.setSurfaceMeshSize(["sphere_1"], 1.5, 5.0, 0.0, 2.0)
# field_surface_box = mesherObj.setSurfaceMeshSize(["box_1"], 1.5, 3.0, 0.0, 2.0)

field_volume_sphere = mesherObj.setSizeForVolume(["sphere_1"], 2.5)
field_volume_sphere_2 = mesherObj.setSizeForVolume(["sphere_1"], 2.5)
field_volume_box = mesherObj.setSizeForVolume(["box_1"], 8.0)

mesherObj.setBackgroundMinFieldUsingAllDefinedFields()

gmsh.model.occ.synchronize()
gmsh.model.mesh.generate(3)
gmsh.fltk.run()

gmsh.fltk.finalize()
