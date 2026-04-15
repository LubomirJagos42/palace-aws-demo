import pygmsh
import gmsh

with pygmsh.occ.Geometry() as geo:
    sphere = geo.add_ball([0,0,125], 50)
    box    = geo.add_box([-90,-90,-10], [180,180,260])

    # Fragment automatically
    geo.boolean_fragments(box, sphere)

    geo.set_mesh_size_callback(
        lambda dim, tag, x, y, z, lc: min(lc, 2.0 if x**2+y**2 < 50**2 else 10.0)
    )

    mesh = geo.generate_mesh(dim=3)
    # mesh.write("antenna.msh")

    gmsh.fltk.run()


