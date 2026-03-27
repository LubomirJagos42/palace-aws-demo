##
# author: Lubomir Jagos
# descritpion: Additional function to plot EM structures results
#

import numpy as np
import pandas as pd
import pyvista as pv
from scipy.spatial import Delaunay

class PlotDiagramUtils:

    def __init__(self):
        pass

    def compute_field_magnitude(self, df):
        """
        Compute total electric field magnitude from real and imaginary components.

        Returns |E| = sqrt(|Ex|² + |Ey|² + |Ez|²) where |Ec|² = Re{Ec}² + Im{Ec}²
        """
        Ex_re = df['r*Re{E_x}'].values
        Ex_im = df['r*Im{E_x}'].values
        Ey_re = df['r*Re{E_y}'].values
        Ey_im = df['r*Im{E_y}'].values
        Ez_re = df['r*Re{E_z}'].values
        Ez_im = df['r*Im{E_z}'].values

        return np.sqrt(
            Ex_re ** 2 + Ex_im ** 2 +
            Ey_re ** 2 + Ey_im ** 2 +
            Ez_re ** 2 + Ez_im ** 2
        )

    def plot_vtk_surface(self, data, label, filename="farfield_3d"):
        """
        Simple: plot deformed sphere from phi, theta, E_mag data.
        """

        E_mag = self.compute_field_magnitude(data)
        E_mag_normalized = E_mag / np.max(E_mag)

        # Get your three variables
        theta = data['theta'].values  # degrees
        phi = data['phi'].values  # degrees
        r = E_mag_normalized  # radial distance

        # Convert spherical to Cartesian
        theta_rad = np.deg2rad(theta)
        phi_rad = np.deg2rad(phi)

        x = r * np.sin(theta_rad) * np.cos(phi_rad)
        y = r * np.sin(theta_rad) * np.sin(phi_rad)
        z = r * np.cos(theta_rad)

        # Create point cloud
        points = np.column_stack((x, y, z))

        # Create surface from points using Delaunay triangulation
        # Project to unit sphere first for better triangulation
        x_unit = np.sin(theta_rad) * np.cos(phi_rad)
        y_unit = np.sin(theta_rad) * np.sin(phi_rad)
        z_unit = np.cos(theta_rad)

        # Use 2D Delaunay in (theta, phi) space
        points_2d = np.column_stack((theta, phi))
        tri = Delaunay(points_2d)

        # Create triangular faces
        faces = []
        for simplex in tri.simplices:
            faces.extend([3, simplex[0], simplex[1], simplex[2]])

        # Create mesh
        mesh = pv.PolyData(points, faces)
        mesh["E_magnitude"] = E_mag

        # Save
        mesh.save(filename)
        print(f"✓ Saved: {filename}")

        return mesh

    def plot_vtk_points(self, data, label, vtk_filename="farfield_3d_points.vtk"):
        """
        Simpler VTK export using PyVista (easier to use than VTK directly).
        Install with: pip install pyvista
        """

        E_mag = self.compute_field_magnitude(data)
        # E_mag /= np.max(E_mag)                  #normalize

        theta_rad = np.deg2rad(data['theta'].values)
        phi_rad = np.deg2rad(data['phi'].values)

        x = E_mag * np.sin(theta_rad) * np.cos(phi_rad)
        y = E_mag * np.sin(theta_rad) * np.sin(phi_rad)
        z = E_mag * np.cos(theta_rad)

        # Get grid dimensions
        theta_unique = np.sort(data['theta'].unique())
        phi_unique = np.sort(data['phi'].unique())
        n_theta = len(theta_unique)
        n_phi = len(phi_unique)

        # Point cloud fallback
        points = np.column_stack((x, y, z))
        cloud = pv.PolyData(points)
        cloud["E_magnitude"] = E_mag

        cloud.save(vtk_filename)
        print(f"Saved point cloud: {vtk_filename}")

    def readFromFileAndPlotFarfield(self, filename, outputFile="farfield_3d.vtk", plotAsPoints=False):
        # Read CSV file
        df = pd.read_csv(filename)

        # Remove spaces and units from column names
        df.columns = [col.strip().split(' (')[0] for col in df.columns]

        # Process the first frequency/mode we find
        if 'm' in df.columns:  # Eigenmode
            mode = df['m'].iloc[0]
            print(f"Processing mode: {mode}")
            label = f"m = {mode}"
            data = df[df['m'] == mode]
        else:
            freq = df['f'].iloc[0]
            print(f"Processing frequency: {freq} GHz")
            label = f"freq = {freq} GHz"
            data = df[df['f'] == freq]

        if plotAsPoints == False:
            self.plot_vtk_surface(data, label, outputFile)
        if plotAsPoints == True:
            self.plot_vtk_points(data, label, outputFile)

