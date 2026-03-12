import gmsh

##########################################################################################################
# SUPPORT FUNCTIONS
##########################################################################################################

def get_tag_after_fragment (object_dimtags, input_dimtags, mapping):
    resultDimtagList = []
    for objDimtag in object_dimtags:
        wasDimtagFound = False
        for k in range(len(input_dimtags)):
            if objDimtag == input_dimtags[k]:
                resultDimtagList = resultDimtagList + mapping[k]
                wasDimtagFound = True
        if wasDimtagFound == False:
            resultDimtagList.append(objDimtag)

    return resultDimtagList

def importStepFileAndGetAllNewEntities(step_file):

    print(f"Importing {step_file}...")

    # Get entities before import
    entities_before = gmsh.model.getEntities()

    # Import
    gmsh.merge(step_file)
    gmsh.model.occ.synchronize()

    # Get new entities
    new_entities = [e for e in gmsh.model.getEntities() if e not in entities_before]

    print(f"  Added {len(new_entities)} tags")

    return new_entities

def getGeometryObject(geometryObjectList, name):
    for geometryObject in geometryObjectList:
        if geometryObject['name'] == name:
            return geometryObject

def performFragmentationAndReassignTags(geometryList):
    print("Performing fragmentation...")
    gmsh.model.occ.synchronize()

    #
    # first do surface fragmentation
    #
    input_dimtags = gmsh.model.occ.getEntities(2)
    out_tags, out_map = gmsh.model.occ.fragment(input_dimtags, [])
    for geometryObject in geometryList:
        geometryObject["dimtags"] = get_tag_after_fragment(geometryObject["dimtags"], input_dimtags, out_map)

    gmsh.model.occ.synchronize()

    input_dimtags = gmsh.model.occ.getEntities(3)
    out_tags, out_map = gmsh.model.occ.fragment(input_dimtags, [])
    for geometryObject in geometryList:
        geometryObject["dimtags"] = get_tag_after_fragment(geometryObject["dimtags"], input_dimtags, out_map)

    gmsh.model.occ.synchronize()

    #
    # do volume fragmentation with surfaces
    #
    input_dimtags = gmsh.model.occ.getEntities(3)
    input_dimtags_tool = gmsh.model.occ.getEntities(2)
    out_tags, out_map = gmsh.model.occ.fragment(input_dimtags, input_dimtags_tool, removeObject=True, removeTool=True)
    for geometryObject in geometryList:
        geometryObject["dimtags"] = get_tag_after_fragment(geometryObject["dimtags"], input_dimtags + input_dimtags_tool, out_map)

    gmsh.model.occ.synchronize()

    #
    # Find NEW surfaces created outside out_tags
    #   - made with help with ClaudeAI
    #   - there seems to be new surface created after fragmentation between 3D and 2D objects
    #   - THIS IS EXPERIMENTAL SEEMS RUNNING FOR PATCH ANTENNA, NEED TO BE TESTED IN OTHER SCENARIOS
    #
    surfaces_after = set(tag for dim, tag in gmsh.model.occ.getEntities(2))
    out_tags_surfaces = set(tag for dim, tag in out_tags if dim == 2)
    orphan_surfaces = surfaces_after - out_tags_surfaces
    if orphan_surfaces:
        print(f"\n⚠ WARNING: Surfaces created outside out_tags: {orphan_surfaces}")

        # These might be volume boundary surfaces
        # Assign them to appropriate geometry objects based on location/adjacency
        for surf_tag in orphan_surfaces:
            up, down = gmsh.model.getAdjacencies(2, surf_tag)
            print(f"  Surface {surf_tag} touches volumes: {up}")

            for geometryObject in geometryList:
                if hasattr(up, '__len__'):
                    for upItem in up:
                        if (3, upItem) in geometryObject["dimtags"]:
                            geometryObject["dimtags"].append((2, surf_tag))
                else:
                    if (3, up) in geometryObject["dimtags"]:
                        geometryObject["dimtags"].append((2, surf_tag))

    #
    # synchronize current model
    #
    gmsh.model.occ.removeAllDuplicates()
    gmsh.model.occ.synchronize()
    print("Fragmentation finished...")

def createGroup(geometryList, groupName, objectName, dimension, groupTag=-1):
    gmsh.model.addPhysicalGroup(dimension, [tag for dim, tag in getGeometryObject(geometryList, objectName)["dimtags"] if dim == dimension], tag=groupTag, name=groupName)

##########################################################################################################
# MAIN PROGRAM
##########################################################################################################
gmsh.initialize()
gmsh.model.add("patch_antenna")

##########################################################################################################
# GEOMETRY
##########################################################################################################
geometryOrderedList = []
# geometryOrderedList.append({"name": "airbox", "dimtags": importStepFileAndGetAllNewEntities('stepfiles/airbox.step')})
geometryOrderedList.append({"name": "patch", "dimtags": importStepFileAndGetAllNewEntities('stepfiles/patch.step')})
geometryOrderedList.append({"name": "substrate", "dimtags": importStepFileAndGetAllNewEntities('stepfiles/substrate.step')})
geometryOrderedList.append({"name": "gnd", "dimtags": importStepFileAndGetAllNewEntities('stepfiles/gnd.step')})
geometryOrderedList.append({"name": "port_in", "dimtags": importStepFileAndGetAllNewEntities('stepfiles/port_in.step')})

#
#   Create in gmsh - patch
#
airboxObj = gmsh.model.occ.addSphere(0,0,0, 140)
_, airbox_boundary = gmsh.model.occ.getSurfaceLoops(airboxObj)
dimtags = [(3,airboxObj)]
for tag in airbox_boundary[0]:
    dimtags.append((2, tag))
geometryOrderedList.append({"name": "airbox", "dimtags": dimtags})

#   Cut substrate from airbox
#   This also working OK using manager array for geometries
#       TODO: Try to do fragment instead of cut
#
#   Without this cutting all 3D objects between each other there is error in palace from MFEM library:
#         Verification failed: (faces_info[gf].Elem2No < 0) is false:
#          --> Invalid mesh topology.  Interior triangular face found connecting elements 20, 21 and 40.
#          ... in function: void mfem::Mesh::AddTriangleFaceElement(int, int, int, int, int, int)
#          ... in file: /opt/palace-build/extern/mfem/mesh/mesh.cpp:8198
#   This error can be replicate just by loading mesh in python mfem library.
#
print("Cutting substrate from airbox...")
out_air, map_air = gmsh.model.occ.cut(
    [ (gmshTuple[0], gmshTuple[1]) for gmshTuple in getGeometryObject(geometryOrderedList, "airbox")["dimtags"] if gmshTuple[0] == 3],
    [ (gmshTuple[0], gmshTuple[1]) for gmshTuple in getGeometryObject(geometryOrderedList, "substrate")["dimtags"] if gmshTuple[0] == 3],
    removeObject=True,
    removeTool=False  # Keep substrate
)

#
#   Whole model fragmentation
#
performFragmentationAndReassignTags(geometryOrderedList)

gmsh.model.occ.synchronize()
gmsh.fltk.run()

##########################################################################################################
# Create mesh size fields for patch and port
# Using distance field for the fine mesh near patch and port, coarser elsewhere
##########################################################################################################

# Collect all surface tags
all_surfaces = []
all_surfaces.extend([tag for dim, tag in getGeometryObject(geometryOrderedList, "patch")["dimtags"] if dim == 2])
all_surfaces.extend([tag for dim, tag in getGeometryObject(geometryOrderedList, "gnd")["dimtags"] if dim == 2])

# Simple distance-based field
field_dist = gmsh.model.mesh.field.add("Distance")
gmsh.model.mesh.field.setNumbers(field_dist, "SurfacesList", all_surfaces)

field_threshold = gmsh.model.mesh.field.add("Threshold")
gmsh.model.mesh.field.setNumber(field_threshold, "InField", field_dist)
gmsh.model.mesh.field.setNumber(field_threshold, "SizeMin", 10.5)  # Fine near surfaces
gmsh.model.mesh.field.setNumber(field_threshold, "SizeMax", 35.0)  # Coarse far away
gmsh.model.mesh.field.setNumber(field_threshold, "DistMin", 0)
gmsh.model.mesh.field.setNumber(field_threshold, "DistMax", 5.0)

gmsh.model.mesh.field.setAsBackgroundMesh(field_threshold)

##########################################################################################################
# Define physical groups for volumes and surfaces
##########################################################################################################

createGroup(geometryOrderedList, "airbox", "airbox", 3)
createGroup(geometryOrderedList, "substrate", "substrate", 3, groupTag=1000)
createGroup(geometryOrderedList, "patch", "patch", 2, groupTag=300)
createGroup(geometryOrderedList, "gnd", "gnd", 2, groupTag=301)
createGroup(geometryOrderedList, "port_in", "port_in", 2, groupTag=302)
createGroup(geometryOrderedList, "farfield", "airbox", 2, groupTag=303)
# createGroup(geometryOrderedList, "airbox_boundary", "airbox_boundary", 2)
# gmsh.model.addPhysicalGroup(2, airboxSurfaceTags, name='airbox_boundary')

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
gmsh.write("simulation_config/antenna_model.msh")

print("PASS - Mesh generated and saved as simulation_model/antenna_model.msh")

##########################################################################################################
# Open generated msh file
##########################################################################################################
gmsh.fltk.run()

gmsh.clear()
gmsh.finalize()
