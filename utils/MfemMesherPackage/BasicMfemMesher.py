##
# author: LuboJ
# descritpion: Basic general mesher to prepare model for MFEM library used by Palace solver
#

import gmsh

class BasicMfemMesher:

    geometryObjectList = []
    internalGeometryObjectIndexCounter = 0
    _meshFieldList = []

    def __init__(self):
        print("MFEM mesher created")

    def get_tag_after_fragment (self, object_dimtags, input_dimtags, mapping):
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

    def addStepfile(self, name, stepfile, priority=-1):
        if priority == -1:
            priority = self.internalGeometryObjectIndexCounter
            self.internalGeometryObjectIndexCounter += 1

        self.geometryObjectList.append({"name": name, "dimtags": self.importStepFileAndGetAllNewEntities(stepfile), "priority": priority, "type": "stepfile"})

    def addGmshObjectUsingDimtags(self, name, dimtags, priority=-1, type=""):
        if priority == -1:
            priority = self.internalGeometryObjectIndexCounter
            self.internalGeometryObjectIndexCounter += 1

        self.geometryObjectList.append({"name": name, "dimtags": dimtags, "priority": priority, "type": type})

    def addGmshVolumeObject(self, name, gmshObjectTag, priority=-1):
        _, gmshObjectBoundary = gmsh.model.occ.getSurfaceLoops(gmshObjectTag)
        dimtags = [(3, gmshObjectTag)]
        for tag in gmshObjectBoundary[0]:
            dimtags.append((2, tag))
        self.addGmshObjectUsingDimtags(name, dimtags, priority, "volume")

    def importStepFileAndGetAllNewEntities(self, step_file):

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

    def getGeometryObject(self, name) -> dict[str, list[tuple[int, int]], int] | None:
        for geometryObject in self.geometryObjectList:
            if geometryObject['name'] == name:
                return geometryObject

        return None

    def sortGeomtriesBasedOnPriority(self):
        """
        Sort geometries based on their priority from higher to lower priority.
        Returns:

        """
        print("Sort geometry object based on their priority...")
        self.geometryObjectList.sort(key=lambda x: x["priority"], reverse=True)

    def performFragmentationAndReassignTags(self, renewVolumeSurfaces=False):
        print("Performing fragmentation...")
        gmsh.model.occ.synchronize()

        self.sortGeomtriesBasedOnPriority()

        #
        # first do surface fragmentation
        #
        input_dimtags = gmsh.model.occ.getEntities(2)
        out_tags, out_map = gmsh.model.occ.fragment(input_dimtags, [])
        for geometryObject in self.geometryObjectList:
            geometryObject["dimtags"] = self.get_tag_after_fragment(geometryObject["dimtags"], input_dimtags, out_map)

        gmsh.model.occ.synchronize()

        input_dimtags = gmsh.model.occ.getEntities(3)
        if len(input_dimtags) > 0:
            out_tags, out_map = gmsh.model.occ.fragment(input_dimtags, [])
            for geometryObject in self.geometryObjectList:
                geometryObject["dimtags"] = self.get_tag_after_fragment(geometryObject["dimtags"], input_dimtags, out_map)

            gmsh.model.occ.synchronize()

        #
        # do volume fragmentation with surfaces
        #
        input_dimtags = gmsh.model.occ.getEntities(3)
        input_dimtags_tool = gmsh.model.occ.getEntities(2)
        out_tags, out_map = gmsh.model.occ.fragment(input_dimtags, input_dimtags_tool, removeObject=True, removeTool=True)
        for geometryObject in self.geometryObjectList:
            geometryObject["dimtags"] = self.get_tag_after_fragment(geometryObject["dimtags"], input_dimtags + input_dimtags_tool, out_map)

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

                for geometryObject in self.geometryList:
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

        #
        # For volume objects remove all 2D surfaces and renew them using gmsh.model.getAdjacencies(...)
        #
        if renewVolumeSurfaces:
            print("Renewing surface dimtags for volumes.")
            for geometryObject in self.geometryObjectList:

                #
                # renew surfaces just for volumes
                #
                if geometryObject["type"] in ["volume", "stepfile"]:

                    #
                    #   remove all 2D dimtags from current volume
                    #
                    for dimtag in geometryObject["dimtags"]:
                        if dimtag[0] == 2:
                            geometryObject["dimtags"].remove(dimtag)

                    #
                    #   get current 2D surfaces for volume and add them to geometries  objects manager
                    #
                    for dimtag in geometryObject["dimtags"]:
                        if dimtag[0] == 3:
                            upward, downward = gmsh.model.getAdjacencies(3, dimtag[1])
                            for tag in downward:
                                geometryObject["dimtags"].append((2, tag))

                    #
                    # TODO: Do also .getAdjacencies() also for 2D surfaces???
                    #

            #
            # Remove duplicate dimtags in lower priority objects
            #
            usedDimtagsInHigherPriorityObjectList = []
            for geometryObject in self.geometryObjectList:
                for dimtag in geometryObject["dimtags"]:
                    if dimtag in usedDimtagsInHigherPriorityObjectList:
                        geometryObject["dimtags"].remove(dimtag)
                    else:
                        usedDimtagsInHigherPriorityObjectList.extend(geometryObject["dimtags"])

        print("Fragmentation finished...")

    def createGroup(self, groupName, objectName, dimension, groupTag=-1):
        groupTag = gmsh.model.addPhysicalGroup(dimension, [tag for dim, tag in self.getGeometryObject(objectName)["dimtags"] if dim == dimension], tag=groupTag, name=groupName)
        return groupTag

    def cutVolumesInsideModel(self):
        self.sortGeomtriesBasedOnPriority()

        if len(self.geometryObjectList) < 2:
            return

        for k in range(len(self.geometryObjectList)-1):
            toolGeometryObject = self.geometryObjectList[k]

            for m in range(k+1, len(self.geometryObjectList)):
                baseGeometryObject = self.geometryObjectList[m]

                isToolObjectAbleToCut = False
                for dimtag in toolGeometryObject["dimtags"]:
                    if dimtag[0] in [3]:
                        isToolObjectAbleToCut = True

                isBaseObjectAbleToCut = False
                for dimtag in baseGeometryObject["dimtags"]:
                    if dimtag[0] in [2,3]:
                        isBaseObjectAbleToCut = True

                if (isToolObjectAbleToCut and isBaseObjectAbleToCut) == False:
                    continue

                #   Without this cutting all 3D objects between each other there is error in palace from MFEM library:
                #         Verification failed: (faces_info[gf].Elem2No < 0) is False:
                #          --> Invalid mesh topology.  Interior triangular face found connecting elements 20, 21 and 40.
                #          ... in function: void mfem::Mesh::AddTriangleFaceElement(int, int, int, int, int, int)
                #          ... in file: /opt/palace-build/extern/mfem/mesh/mesh.cpp:8198
                #   This error can be replicate just by loading mesh in python mfem library.

                print(f"Cutting '{toolGeometryObject["name"]}' from '{baseGeometryObject["name"]}'...")
                try:
                    baseDimtags = [ (gmshTuple[0], gmshTuple[1]) for gmshTuple in baseGeometryObject["dimtags"] if gmshTuple[0] in [2,3]]
                    toolDimtags = [(gmshTuple[0], gmshTuple[1]) for gmshTuple in toolGeometryObject["dimtags"] if gmshTuple[0] in [2,3]]
                    outDimtags, outDimtagsMap = gmsh.model.occ.cut(
                        baseDimtags,
                        toolDimtags,
                        removeObject=True,
                        removeTool=False
                    )
                    self.get_tag_after_fragment(baseGeometryObject["dimtags"], baseDimtags, outDimtagsMap)
                    gmsh.model.occ.synchronize()
                except Exception as e:
                    print(e)
                    pass

    def cutOnlyVolumesInModelBetweenEachOther(self, allowSurfacesToBeCutted=False):
        self.sortGeomtriesBasedOnPriority()

        if len(self.geometryObjectList) < 2:
            return

        for k in range(len(self.geometryObjectList)-1):
            toolGeometryObject = self.geometryObjectList[k]

            for m in range(k+1, len(self.geometryObjectList)):
                baseGeometryObject = self.geometryObjectList[m]

                isToolObjectAbleToCut = False
                for dimtag in toolGeometryObject["dimtags"]:
                    if dimtag[0] in [3]:
                        isToolObjectAbleToCut = True

                isBaseObjectAbleToCut = False
                baseObjectsAllowedDiemnsionToBeUsed = [2,3] if allowSurfacesToBeCutted else [3]
                for dimtag in baseGeometryObject["dimtags"]:
                    if dimtag[0] in baseObjectsAllowedDiemnsionToBeUsed:
                        isBaseObjectAbleToCut = True

                if (isToolObjectAbleToCut and isBaseObjectAbleToCut) == False:
                    continue

                #   Without this cutting all 3D objects between each other there is error in palace from MFEM library:
                #         Verification failed: (faces_info[gf].Elem2No < 0) is False:
                #          --> Invalid mesh topology.  Interior triangular face found connecting elements 20, 21 and 40.
                #          ... in function: void mfem::Mesh::AddTriangleFaceElement(int, int, int, int, int, int)
                #          ... in file: /opt/palace-build/extern/mfem/mesh/mesh.cpp:8198
                #   This error can be replicate just by loading mesh in python mfem library.

                print(f"Cutting '{toolGeometryObject["name"]}' from '{baseGeometryObject["name"]}'...")
                try:
                    baseDimtags = [(gmshTuple[0], gmshTuple[1]) for gmshTuple in baseGeometryObject["dimtags"] if gmshTuple[0] in baseObjectsAllowedDiemnsionToBeUsed]
                    toolDimtags = [(gmshTuple[0], gmshTuple[1]) for gmshTuple in toolGeometryObject["dimtags"] if gmshTuple[0] in [3]]
                    outDimtags, outDimtagsMap = gmsh.model.occ.cut(
                        baseDimtags,
                        toolDimtags,
                        removeObject=True,
                        removeTool=False
                    )
                    gmsh.model.occ.synchronize()
                    self.get_tag_after_fragment(baseGeometryObject["dimtags"], baseDimtags, outDimtagsMap)
                    gmsh.model.occ.synchronize()
                except Exception as e:
                    print(e)
                    pass


    def setSurfaceMeshSize(self, geometryObjectNameOrList: str | list[str], sizeMin: float=0.0, sizeMax: float=0.0, distanceMin: float=0.0, distanceMax: float=0.0):
        # Collect all surface tags
        all_surfaces = []
        if type(geometryObjectNameOrList) == str:
            all_surfaces.extend([tag for dim, tag in self.getGeometryObject(geometryObjectNameOrList)["dimtags"] if dim == 2])
        else:
            for geometryObjectName in geometryObjectNameOrList:
                all_surfaces.extend([tag for dim, tag in self.getGeometryObject(geometryObjectName)["dimtags"] if dim == 2])

        # Simple distance-based field
        field_dist = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(field_dist, "SurfacesList", all_surfaces)

        field_threshold = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(field_threshold, "InField", field_dist)
        gmsh.model.mesh.field.setNumber(field_threshold, "SizeMin", sizeMin)  # Fine near surfaces
        gmsh.model.mesh.field.setNumber(field_threshold, "SizeMax", sizeMax)  # Coarse far away
        gmsh.model.mesh.field.setNumber(field_threshold, "DistMin", distanceMin)
        gmsh.model.mesh.field.setNumber(field_threshold, "DistMax", distanceMax)

        self._meshFieldList.append(field_threshold)

        return field_threshold

    def setSizeOnFace(self, geometryObjectNameOrList: str | list[str], max_size: float=0.0):
        # Collect all surface tags
        all_surfaces = []
        if type(geometryObjectNameOrList) == str:
            all_surfaces.extend([tag for dim, tag in self.getGeometryObject(geometryObjectNameOrList)["dimtags"] if dim == 2])
        else:
            for geometryObjectName in geometryObjectNameOrList:
                all_surfaces.extend([tag for dim, tag in self.getGeometryObject(geometryObjectName)["dimtags"] if dim == 2])

        ctag = gmsh.model.mesh.field.add("Constant")
        gmsh.model.mesh.field.set_numbers(ctag, "SurfacesList", all_surfaces)
        gmsh.model.mesh.field.set_number(ctag, "VIn", max_size)

        self._meshFieldList.append(ctag)

        return ctag

    def setSizeForVolume(self, geometryObjectNameOrList: str | list[str], max_size: float=0.0):
        # Collect all surface tags
        all_volumes = []
        if type(geometryObjectNameOrList) == str:
            all_volumes.extend([tag for dim, tag in self.getGeometryObject(geometryObjectNameOrList)["dimtags"] if dim == 3])
        else:
            for geometryObjectName in geometryObjectNameOrList:
                all_volumes.extend([tag for dim, tag in self.getGeometryObject(geometryObjectName)["dimtags"] if dim == 3])

        ctag = gmsh.model.mesh.field.add("Constant")
        gmsh.model.mesh.field.set_numbers(ctag, "VolumesList", all_volumes)
        gmsh.model.mesh.field.set_number(ctag, "VIn", max_size)

        self._meshFieldList.append(ctag)

        return ctag

    def setBackgroundMinFieldUsingAllDefinedFields(self):
        f_min = gmsh.model.mesh.field.add("Min")
        gmsh.model.mesh.field.setNumbers(f_min, "FieldsList", self._meshFieldList)
        gmsh.model.mesh.field.setAsBackgroundMesh(f_min)