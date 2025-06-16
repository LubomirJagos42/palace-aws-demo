import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv

# Load the file without header (columns will be numbered 0, 1, 2...)
df = pd.read_csv("sim_results/radiation_pattern/radiation_pattern.csv")

#df.loc[:, "Points:0"]  #example how to address column in pandas

points_cartesian = df[['Points:0', 'Points:1', 'Points:2']].values

# Extract x, y, z
x = points_cartesian[:, 0]
y = points_cartesian[:, 1]
z = points_cartesian[:, 2]

# Convert to spherical
r = np.sqrt(x**2 + y**2 + z**2)
theta = np.arccos(z / r)             # inclination angle (0 to π)
phi = np.arctan2(y, x)               # azimuthal angle (−π to π)

# Combine if needed
spherical_coords = np.vstack((r, theta, phi)).T  # shape (N, 3)

###############################################################################################################
# PROCESS DATA
###############################################################################################################
E_imag_mag = np.sqrt(df.loc[:, "E_imag:0"]**2 + df.loc[:, "E_imag:1"]**2 + df.loc[:, "E_imag:2"]**2)
E_real_mag = np.sqrt(df.loc[:, "E_real:0"]**2 + df.loc[:, "E_real:1"]**2 + df.loc[:, "E_real:2"]**2)
E_mag = np.sqrt(E_imag_mag**2 + E_real_mag**2)
E_mag_norm = E_mag / max(E_mag)

scale_factor = 100.0

#store original points
x_orig = r * np.sin(theta) * np.cos(phi) * scale_factor
y_orig = r * np.sin(theta) * np.sin(phi) * scale_factor
z_orig = r * np.cos(theta) * scale_factor

# r = r*E_mag_norm
r = r*E_mag * scale_factor   #random good enough constant it was too small compare to pach, this is ok

###############################################################################################################
# PLOT POINTS
###############################################################################################################
x = r * np.sin(theta) * np.cos(phi)
y = r * np.sin(theta) * np.sin(phi)
z = r * np.cos(theta)

# fig = plt.figure()
# ax = fig.add_subplot(111, projection='3d')
# ax.scatter(x, y, z, c=r, cmap='viridis')  # color by radius
#
# ax.set_xlabel('X')
# ax.set_ylabel('Y')
# ax.set_zlabel('Z')
# ax.set_title('Points Colored by Radius (Spherical Coordinates)')
#
# plt.show()

###############################################################################################################
# EXPORT FOR PARAVIEW - points original sphere with E magnitude
###############################################################################################################

# Assuming you have points as Nx3 NumPy array
points = np.column_stack((x_orig, y_orig, z_orig))

# Create a point cloud
cloud = pv.PolyData(points)

# Optional: add scalar values (e.g., E-field magnitude, radius)
cloud["Magnitude"] = E_mag_norm  # must be same length as points

# Export to VTU file
cloud.save("sim_results/radiation_pattern/calculated_radiation_pattern_points_original.vtk")

###############################################################################################################
# EXPORT FOR PARAVIEW - points
###############################################################################################################

# Assuming you have points as Nx3 NumPy array
points = np.column_stack((x, y, z))

# Create a point cloud
cloud = pv.PolyData(points)

# Optional: add scalar values (e.g., E-field magnitude, radius)
cloud["Magnitude"] = E_mag_norm  # must be same length as points

# Export to VTU file
cloud.save("sim_results/radiation_pattern/calculated_radiation_pattern_points.vtk")

###############################################################################################################
# EXPORT FOR PARAVIEW - surface - wrong not working properly
###############################################################################################################

# # Perform Delaunay 3D triangulation
# surface = cloud.delaunay_2d()
#
# # Visualize it (optional)
# surface.plot(show_edges=True)
#
# # Save for use in ParaView
# surface.save("sim_results/radiation_pattern/calculated_radiation_pattern_surface.vtk")

###############################################################################################################
# Displace spherical points
###############################################################################################################
# Load the VTK surface mesh (e.g., a sphere.vtp or .vtk file)
mesh = pv.read("sim_results/radiation_pattern/sphere_boundaries_data_2.vtk")  # or .vtk


# Check available field names
print(mesh.point_data.keys())  # Ensure your field (e.g. "E") is here

import math
# Get field data (e.g., electric field vector)
E = np.sqrt(mesh.point_data["E_real"]**2 + mesh.point_data["E_imag"]**2)

# Compute magnitude of the field at each point
E_magnitude = np.linalg.norm(E, axis=1)

# Get original points and compute radial direction
points = mesh.points
radii = np.linalg.norm(points, axis=1)
directions = points / radii[:, np.newaxis]

# Displace points along radial direction by field magnitude
scale_factor_2 = 20
displaced_points = points + directions * E_magnitude[:, np.newaxis] * scale_factor_2

# Update mesh
mesh.points = displaced_points

# Save or visualize
mesh.save("sim_results/radiation_pattern/displaced_by_field.vtk")
mesh.plot(show_edges=True)