##
# author: Lubomir Jagos
# descritpion: Additional function to plot EM structures results
#
import os.path

import numpy as np
import pandas as pd
import pyvista as pv
from scipy.spatial import Delaunay


class PlotDiagramUtils:

    def __init__(self):
        pass

    def compute_field_magnitude(self, df, useDecibels):
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

        E_mag = np.sqrt(
            Ex_re ** 2 + Ex_im ** 2 +
            Ey_re ** 2 + Ey_im ** 2 +
            Ez_re ** 2 + Ez_im ** 2
        )

        if useDecibels:
            E_mag = 20*np.log10(E_mag)

        return E_mag

    def plot_vtk_surface(self, data, label, filename="farfield_3d", useDecibels=False, useNormalization=True):
        """
        Simple: plot deformed sphere from phi, theta, E_mag data.
        """

        E_mag = self.compute_field_magnitude(data, useDecibels)
        if useNormalization:
            E_mag_normalized = E_mag / np.max(E_mag)
        else:
            E_mag_normalized = E_mag

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

    def plot_vtk_points(self, data, label, vtk_filename="farfield_3d_points.vtk", useDecibels=False):
        """
        Simpler VTK export using PyVista (easier to use than VTK directly).
        Install with: pip install pyvista
        """

        E_mag = self.compute_field_magnitude(data, useDecibels)
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

    def readFromFileAndPlotFarfield(self, filename, outputFile="farfield_3d.vtk", plotAsPoints=False, useDecibels=False, useNormalization=True):
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
            self.plot_vtk_surface(data, label, outputFile, useDecibels, useNormalization)
        if plotAsPoints == True:
            self.plot_vtk_points(data, label, outputFile, useDecibels)

    def readFromFileAndGetEfieldMagnitude(self, filename):
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

        return data

    def getRadiatedPowerFromFile(self, inputFile):
        s_df = pd.read_csv(inputFile)
        s_df.columns = [col.strip().split(' (')[0] for col in s_df.columns]
        print(s_df.to_string())

        # Palace outputs |S11| in dB and phase in degrees — not Re/Im
        S11_mag_dB = s_df['|S[1][1]|'].iloc[0]  # e.g. -7.797 dB
        S11_arg_deg = s_df['arg(S[1][1])'].iloc[0]  # e.g. -132.05 deg

        # Convert magnitude from dB to linear
        S11_mag = 10.0 ** (S11_mag_dB / 20.0)  # linear magnitude

        # |S11|² = S11_mag² (phase cancels out in magnitude squared)
        S11_sq = S11_mag ** 2

        # Palace unit incident voltage 1V into 50Ω
        P_inc = 1.0 / (2.0 * 50.0)  # 0.01 W
        P_input = P_inc * (1.0 - S11_sq)  # accepted power after reflection

        return P_input

    def getPowerFromVoltageFile(self, inputFile):
        v_df = pd.read_csv(inputFile)
        v_df.columns = [col.strip().split(' (')[0] for col in v_df.columns]
        print(v_df.to_string())

        V_inc = v_df['V_inc[1]'].iloc[0]  # incident voltage amplitude [V]
        V_re = v_df['Re{V[1]}'].iloc[0]  # total voltage real part [V]
        V_im = v_df['Im{V[1]}'].iloc[0]  # total voltage imag part [V]

        R_port = 50.0

        # Incident power — from incident voltage amplitude
        P_inc = V_inc ** 2 / (2.0 * R_port)

        # Total voltage magnitude
        V_mag = np.sqrt(V_re ** 2 + V_im ** 2)

        # Reflected voltage = V_inc - V_total (in terms of wave amplitudes)
        # S11 = V_ref / V_inc  where V_ref = V_inc - V_total...
        # simpler: use P_accepted = Re{V·I*}/2 = |V|²/(2R) for matched load
        # but most direct from this file:
        # P_accepted = P_inc - P_reflected = P_inc * (1 - |S11|²)
        # and |S11| = |V_inc - V_total| / V_inc  ...

        # Cleanest: accepted power directly from total V and port impedance
        # P_accepted = (V_inc² - V_ref²) / (2R)
        # V_ref = V_inc - V_re  (real part only since V_inc is real-valued amplitude)
        V_ref = np.sqrt((V_inc - V_re) ** 2 + V_im ** 2)  # |V_reflected|
        S11_sq = (V_ref / V_inc) ** 2

        P_accepted = P_inc * (1.0 - S11_sq)

        print(f"V_inc      : {V_inc:.4f} V")
        print(f"V_total    : {V_mag:.4f} V")
        print(f"V_ref      : {V_ref:.4f} V")
        print(f"|S11|      : {np.sqrt(S11_sq):.4f}  ({20 * np.log10(np.sqrt(S11_sq)):.2f} dB)")
        print(f"P_inc      : {P_inc:.4e} W")
        print(f"P_accepted : {P_accepted:.4e} W")
        print(f"Efficiency : {100 * (1 - S11_sq):.1f} % of incident power accepted")
        print()

        return P_accepted

    def readFromFileComputeDirectivityRadiationDiagram(self, filename, outputfile):
        """
        Generated by ClaudeAI and tested, for now seems to be good method to calculate graph, there are more graphs
        stored inside VTK file therefore to see directivity antenna diagram it must be changed inside paraview in
        select box.
        Args:
            filename:
            outputfile:

        Returns: None

        """

        # ── Load ─────────────────────────────────────────────────────────────────
        df = pd.read_csv(filename)
        df.columns = [col.strip().split(' (')[0] for col in df.columns]
        freq = df['f'].iloc[0]
        data = df[df['f'] == freq].copy()

        eta_0   = 376.730313
        R_port  = 50.0

        filenameToCalculatePowerInput = ""
        P_input = 1.0       #default value 1W
        try:
            # filenameToCalculatePowerInput = os.path.join(os.path.dirname(filename), "port-S.csv")
            # P_input = self.getRadiatedPowerFromFile(filenameToCalculatePowerInput)

            filenameToCalculatePowerInput = os.path.join(os.path.dirname(filename), "port-V.csv")
            P_input = self.getPowerFromVoltageFile(filenameToCalculatePowerInput)
        except Exception as e:
            print(f"Error during reading input power from file: {filenameToCalculatePowerInput}")
            print(e)
            print("Using input power: 1.0 / (2.0 * R_port)")
            P_input = 1.0 / (2.0 * R_port)   # 0.01W — Palace unit excitation into 50Ω  TODO: Need check and calculate input power from I or V file in simulation output
        print(f"P_input      : {P_input:.6e} W")

        # ── Angles as flat arrays ─────────────────────────────────────────────────
        theta_deg = data['theta'].values
        phi_deg   = data['phi'].values
        theta_rad = np.deg2rad(theta_deg)
        phi_rad   = np.deg2rad(phi_deg)

        # ── |rE|² and radiation intensity — all flat arrays ──────────────────────
        rE_sq = (data['r*Re{E_x}'].values**2 + data['r*Im{E_x}'].values**2 +
                 data['r*Re{E_y}'].values**2 + data['r*Im{E_y}'].values**2 +
                 data['r*Re{E_z}'].values**2 + data['r*Im{E_z}'].values**2)

        U = rE_sq / (2.0 * eta_0)   # radiation intensity [W/sr], flat array

        print(f"Points    : {len(U)}")
        print(f"|rE|² max : {rE_sq.max():.4e} V²")
        print(f"U max     : {U.max():.4e} W/sr")

        # ── Prad integration over scattered points ────────────────────────────────
        # Prad = ∫∫ U(θ,φ) sinθ dθ dφ
        #
        # For scattered points we estimate each point's solid angle weight
        # using Delaunay triangulation on the (θ,φ) plane — each triangle
        # contributes area × sin(θ_centroid) to the integral
        #
        points_2d = np.column_stack((theta_rad, phi_rad))
        tri       = Delaunay(points_2d)

        Prad = 0.0
        for simplex in tri.simplices:
            # triangle vertices in (θ,φ)
            t0, t1, t2 = theta_rad[simplex]
            p0, p1, p2 = phi_rad[simplex]

            # triangle area in (θ,φ) plane via cross product
            dt1, dp1 = t1 - t0, p1 - p0
            dt2, dp2 = t2 - t0, p2 - p0
            area = 0.5 * abs(dt1 * dp2 - dt2 * dp1)

            # centroid
            t_c = (t0 + t1 + t2) / 3.0
            sin_tc = np.sin(t_c)

            # average U over triangle
            U_avg = (U[simplex[0]] + U[simplex[1]] + U[simplex[2]]) / 3.0

            Prad += U_avg * sin_tc * area

        print(f"Prad      : {Prad:.6e} W")

        # ── Directivity and Gain (all flat arrays) ────────────────────────────────
        directivity     = 4.0 * np.pi * U / Prad
        gain            = 4.0 * np.pi * U / P_input
        efficiency      = Prad / P_input

        directivity_dBi = 10.0 * np.log10(np.maximum(directivity, np.max(directivity) * 1e-10))
        gain_dBi        = 10.0 * np.log10(np.maximum(gain,        np.max(gain)        * 1e-10))

        print(f"Directivity : {np.max(directivity):.3f}  ({np.max(directivity_dBi):.2f} dBi)")
        # print(f"Gain        : {np.max(gain):.3f}  ({np.max(gain_dBi):.2f} dBi)")
        print(f"Gain        : {np.max(gain):.10f}  ({np.max(gain_dBi):.2f} dBi)")
        # print(f"Efficiency  : {100 * efficiency:.1f} %")
        print(f"Efficiency  : {100 * efficiency:.10f} %")

        # ── Build VTK — reuse same triangulation ─────────────────────────────────
        # Shape = linear directivity as radius, color = gain_dBi
        r_norm = directivity / np.max(directivity)   # normalized to [0,1]

        x = r_norm * np.sin(theta_rad) * np.cos(phi_rad)
        y = r_norm * np.sin(theta_rad) * np.sin(phi_rad)
        z = r_norm * np.cos(theta_rad)

        points = np.column_stack((x, y, z))

        # Reuse tri from above — same point ordering
        faces = []
        for simplex in tri.simplices:
            faces.extend([3, simplex[0], simplex[1], simplex[2]])

        mesh = pv.PolyData(points, faces)
        mesh["gain_dBi"]        = gain_dBi
        mesh["directivity_dBi"] = directivity_dBi
        mesh["directivity_lin"] = directivity
        mesh["gain_lin"]        = gain
        mesh["U_W_per_sr"]      = U

        mesh.save(outputfile)
        print(f"✓ Saved: {outputfile}")
