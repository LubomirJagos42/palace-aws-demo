# Automaticaly generate gmsh model suitable for palace solver
#
#
from wsgiref.util import request_uri

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

# Parameters
mesh_size_fine = 0.5
mesh_size_coarse = 2

##########################################################################################################
# GEOMETRY
##########################################################################################################
geometryOrderedList = []
geometryOrderedList.append({"name": "port_in", "dimtags": importStepFileAndGetAllNewEntities('stepfiles/port_in.step')})
geometryOrderedList.append({"name": "patch", "dimtags": importStepFileAndGetAllNewEntities('stepfiles/patch.step')})
geometryOrderedList.append({"name": "gnd", "dimtags": importStepFileAndGetAllNewEntities('stepfiles/gnd.step')})
geometryOrderedList.append({"name": "substrate", "dimtags": importStepFileAndGetAllNewEntities('stepfiles/substrate.step')})
geometryOrderedList.append({"name": "airbox", "dimtags": importStepFileAndGetAllNewEntities('stepfiles/airbox.step')})

print("Ordered objects list:")
for geometryObject in geometryOrderedList:
    print("\t"+geometryObject['name'])

performFragmentationAndReassignTags(geometryOrderedList)

##########################################################################################################
# Create mesh size fields for patch and port
# Using distance field for the fine mesh near patch and port, coarser elsewhere
##########################################################################################################

# Field 1: Fine mesh near port
surfaceTags = [dimtag[1] for dimtag in getGeometryObject(geometryOrderedList, "patch")["dimtags"] if dimtag[0] == 2]
field_mesh = gmsh.model.mesh.field.add("Distance")
gmsh.model.mesh.field.setNumbers(field_mesh, "SurfacesList", surfaceTags)

field_mesh_size = gmsh.model.mesh.field.add("Threshold")
gmsh.model.mesh.field.setNumber(field_mesh_size, "InField", field_mesh)
gmsh.model.mesh.field.setNumber(field_mesh_size, "SizeMin", 2.0)  # Min size near port
gmsh.model.mesh.field.setNumber(field_mesh_size, "SizeMax", 5.0)   # Max size far from port
gmsh.model.mesh.field.setNumber(field_mesh_size, "DistMin", 4.0)   # Distance where min applies
gmsh.model.mesh.field.setNumber(field_mesh_size, "DistMax", 8.0)   # Distance where max applies

# Field 2: Coarse mesh elsewhere
field_default = gmsh.model.mesh.field.add("MathEval")
gmsh.model.mesh.field.setString(field_default, "F", "100.0")  # Default coarse size

# Combine fields (take minimum)
field_min = gmsh.model.mesh.field.add("Min")
gmsh.model.mesh.field.setNumbers(field_min, "FieldsList", [field_mesh_size, field_default])

# Set as background mesh
gmsh.model.mesh.field.setAsBackgroundMesh(field_min)



#
# WAY 2 - NOT WOKRING - Using mesh sizes
#
# gmsh.model.mesh.setSize([dimtag for dimtag in getGeometryObject(geometryOrderedList, "patch")["dimtags"]], 0.1)
# gmsh.model.mesh.setSize([dimtag for dimtag in getGeometryObject(geometryOrderedList, "gnd")["dimtags"]], 0.5)






##########################################################################################################
# Define physical groups for volumes and surfaces
##########################################################################################################

createGroup(geometryOrderedList, "airbox", "airbox", 3)
createGroup(geometryOrderedList, "substrate", "substrate", 3)
createGroup(geometryOrderedList, "patch", "patch", 2)
createGroup(geometryOrderedList, "gnd", "gnd", 2)
createGroup(geometryOrderedList, "farfield", "airbox", 2)
createGroup(geometryOrderedList, "port_in", "port_in", 2)

# gmsh.fltk.run()

##########################################################################################################
# MESH GENERATE
##########################################################################################################
# gmsh directives
gmsh.option.setNumber("General.Terminal", 1)  # print messages
gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
gmsh.option.setNumber("Mesh.Binary", 0)       # text .msh file
gmsh.option.setNumber("Mesh.Algorithm3D", 10) #HXT algorithm
# gmsh.option.setNumber("Mesh.Algorithm3D", 1)    #Delaunay
gmsh.option.setNumber("Mesh.MeshSizeMin", 0.05)

# Generate mesh
gmsh.model.mesh.generate(3)
gmsh.write("simulation_config/antenna_model.msh")

print("✅ Mesh generated and saved as simulation_model/antenna_model.msh")

##########################################################################################################
# Open generated msh file
##########################################################################################################
gmsh.fltk.run()

gmsh.clear()
gmsh.finalize()
