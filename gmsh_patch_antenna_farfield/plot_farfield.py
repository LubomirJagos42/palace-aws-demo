"""
Generate polar plots on the E and B planes and 3D relative radiation pattern
from the Palace farfield output data (`farfield-rE.csv`). Only plot the first
frequency found in the file.

The 3D relative radiation pattern plot depicts a 3D surface whose distance from
the center is proportional to the strength of the electric field.

Usage:
    python plot_farfield.py --model <model_type> --file <filename>

Arguments:
    --model <model_type>  - Dipole model type: "short_dipole" or "halfwave_dipole"
    --file <filename>     - Path to farfield file

Both arguments are required.

Requires pandas, numpy, and matplotlib.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import argparse
import sys
from pathlib import Path


def compute_field_magnitude(df):
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


def extract_eplane(df, tolerance_deg=1):
    """
    Extract E-plane (xz-plane) radiation pattern data.

    This is done by identifying points with φ = 0° and φ = 180° within the given
    tolerance.

    We have to be a little careful here because we need to offset the θs by 180°
    to make sure we cover the entire circumference.
    """
    angles_list = []
    magnitude_list = []

    # phi ≈ 0°, no theta offset
    mask1 = np.abs(df['phi'].values - 0) < tolerance_deg
    if mask1.any():
        data1 = df[mask1]
        angles_list.extend(data1['theta'].values)
        magnitude_list.extend(compute_field_magnitude(data1))

    # phi ≈ 180°, theta offset by 180°
    mask2 = np.abs(df['phi'].values - 180) < tolerance_deg
    if mask2.any():
        data2 = df[mask2]
        offset_angles = (data2['theta'].values + 180) % 360
        angles_list.extend(offset_angles)
        magnitude_list.extend(compute_field_magnitude(data2))

    # Sort by angle
    angles_array = np.array(angles_list)
    magnitude_array = np.array(magnitude_list)
    sort_idx = np.argsort(angles_array)

    return angles_array[sort_idx], magnitude_array[sort_idx]


def extract_hplane(df, tolerance_deg=1):
    """
    Extract H-plane (xy-plane) radiation pattern data.

    This is done by identifying points with θ = 90° within the given tolerance.
    """
    mask = np.abs(df['theta'].values - 90) < tolerance_deg
    hplane_data = df[mask]

    return hplane_data['phi'].values, compute_field_magnitude(hplane_data)


def compute_db(magnitude):
    """
    Convert field magnitude to normalized dB scale and return values normalized
    to 0 dB maximum.
    """
    # Floor values 10 orders of magnitude below maximum to avoid log(0)
    magnitude = np.maximum(magnitude, np.max(magnitude) * 1e-10)
    db_values = 20 * np.log10(magnitude)
    return db_values - np.max(db_values)


def generate_theoretical_dipole(model_type="halfwave_dipole"):
    """
    Return angles and patterns for theoretical dipole radiation pattern.

    Arguments:
    model_type - "short_dipole" for electrical current dipole or
                 "halfwave_dipole" for half-wave dipole

    For short_dipole (z-oriented electrical current dipole):
    Based on geosci.xyz far-field analytical solution for z-oriented dipole.

      - E-plane (xz): |E_θ|² ∝ |sin(θ)|² (nulls along dipole axis, maxima perpendicular)
      - H-plane (xy): |H_φ|² ∝ constant (omnidirectional)

    For halfwave_dipole:

      - E-plane: [cos(π/2 * cos(θ)) / sin(θ)]²
      - H-plane: omnidirectional (constant)
    """
    angles = np.arange(0, 361)

    if model_type == "short_dipole":
        # E-plane: sin(θ)²
        eplane = np.zeros(len(angles))
        for i, theta_deg in enumerate(angles):
            theta_rad = np.deg2rad(theta_deg)
            sin_theta = np.sin(theta_rad)
            if abs(sin_theta) > 1e-6:
                eplane[i] = abs(sin_theta)

    elif model_type == "halfwave_dipole":
        # E-plane: [cos(π/2 * cos(θ)) / sin(θ)]²
        eplane = np.zeros(len(angles))
        for i, theta_deg in enumerate(angles):
            theta_rad = np.deg2rad(theta_deg)
            sin_theta = np.sin(theta_rad)
            if abs(sin_theta) > 1e-6:
                eplane[i] = abs(np.cos(np.pi / 2 * np.cos(theta_rad)) / sin_theta)

    else:
        raise ValueError(f"Unknown model_type: {model_type}. Use 'short_dipole' or 'halfwave_dipole'")

    # H-plane: omnidirectional
    hplane = np.ones(len(angles))

    return angles, eplane, angles, hplane


def polar_plots(data, label, model_type="halfwave_dipole", filename="farfield_polar.png"):
    """
    Plot the polar radiation patterns and the expected dipole pattern.
    """
    e_angles, e_mag = extract_eplane(data)
    h_angles, h_mag = extract_hplane(data)

    theo_angles, theo_eplane, _, theo_hplane = generate_theoretical_dipole(model_type)
    theo_e_db = compute_db(theo_eplane)
    theo_h_db = compute_db(theo_hplane)

    fig = plt.figure(figsize=(12, 5))

    if len(e_mag) > 1:
        e_db = compute_db(e_mag)

        # E-plane plot
        ax1 = fig.add_subplot(121, projection='polar')
        ax1.set_title(f"E-plane ({label})")
        ax1.set_ylim(-25, 2)
        ax1.set_theta_zero_location('N')
        ax1.set_theta_direction(-1)
        ax1.grid(True, color='lightgray')

        # Theoretical pattern
        ax1.plot(np.deg2rad(theo_angles), theo_e_db,
                 linewidth=1, linestyle='--', color='black', label='Theoretical')
        # Simulated pattern
        ax1.plot(np.deg2rad(e_angles), e_db,
                 linewidth=2, color='blue', label='Simulated')
        ax1.legend(loc='upper right')
    else:
        print("No point found on the E-plane")

    if len(h_mag) > 1:
        h_db = compute_db(h_mag)

        # H-plane plot
        ax2 = fig.add_subplot(122, projection='polar')
        ax2.set_title(f"H-plane ({label})")
        ax2.set_ylim(-25, 2)
        ax2.set_theta_zero_location('N')
        ax2.set_theta_direction(-1)
        ax2.grid(True, color='lightgray')

        # Theoretical pattern
        ax2.plot(np.deg2rad(theo_angles), theo_h_db,
                 linewidth=1, linestyle='--', color='black', label='Theoretical')
        # Simulated pattern
        ax2.plot(np.deg2rad(h_angles), h_db,
                 linewidth=2, color='blue', label='Simulated')
        ax2.legend(loc='upper right')
    else:
        print("No point found on the H-plane")

    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    print(f"Saved {filename}")
    plt.close()


def three_d_plot(data, label, filename="farfield_3d.png"):
    """
    Plot a 3D representation of the strength of the electric field.

    The plot represents the normalized magnitude of electric field with a surface
    where the radial distance is proportional to the magnitude itself.
    """
    E_mag = compute_field_magnitude(data)
    E_mag /= np.max(E_mag)

    theta_rad = np.deg2rad(data['theta'].values)
    phi_rad = np.deg2rad(data['phi'].values)

    x = E_mag * np.sin(theta_rad) * np.cos(phi_rad)
    y = E_mag * np.sin(theta_rad) * np.sin(phi_rad)
    z = E_mag * np.cos(theta_rad)

    # Reshape for surface plot if data is structured
    theta_unique = np.sort(data['theta'].unique())
    phi_unique = np.sort(data['phi'].unique())
    n_theta = len(theta_unique)
    n_phi = len(phi_unique)

    try:
        # Try to reshape for surface plot
        X = x.reshape(n_theta, n_phi)
        Y = y.reshape(n_theta, n_phi)
        Z = z.reshape(n_theta, n_phi)
        E_grid = E_mag.reshape(n_theta, n_phi)

        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection='3d')
        ax.set_title(f"Relative E-field magnitude ({label})")

        # Surface plot
        surf = ax.plot_surface(X, Y, Z, facecolors=plt.cm.viridis(E_grid),
                               rstride=1, cstride=1, antialiased=True, shade=False)

        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_box_aspect([1, 1, 1])

        # Add colorbar
        mappable = plt.cm.ScalarMappable(cmap='viridis')
        mappable.set_array(E_mag)
        plt.colorbar(mappable, ax=ax, shrink=0.5, label='Normalized |E|')

    except ValueError:
        # Fallback to scatter plot if data isn't structured
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection='3d')
        ax.set_title(f"Relative E-field magnitude ({label})")

        scatter = ax.scatter(x, y, z, c=E_mag, cmap='viridis', s=20)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_box_aspect([1, 1, 1])

        plt.colorbar(scatter, ax=ax, shrink=0.5, label='Normalized |E|')

    # plt.show()
    plt.savefig(filename, dpi=150)
    print(f"Saved {filename}")
    plt.close()


def print_usage():
    """Print usage information"""
    print(f"Usage: python {sys.argv[0]} --model <model_type> --file <filename>")
    print()
    print("Arguments:")
    print("  --model <model_type>  Dipole model type: 'short_dipole' or 'halfwave_dipole'")
    print("  --file <filename>     Path to farfield file")
    print()
    print("Both arguments are required.")
    print()
    print("Examples:")
    print(f"  python {sys.argv[0]} --model halfwave_dipole --file postpro/antenna_halfwave_dipole/farfield-rE.csv")
    print(f"  python {sys.argv[0]} --model short_dipole --file postpro/antenna_short_dipole/farfield-rE.csv")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Generate radiation pattern plots from Palace farfield data',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--model', type=str, required=True,
                        choices=['short_dipole', 'halfwave_dipole'],
                        help="Dipole model type")
    parser.add_argument('--file', type=str, required=True,
                        help="Path to farfield file")

    args = parser.parse_args()

    # Check if file exists
    if not Path(args.file).is_file():
        print(f"Error: File '{args.file}' not found")
        print_usage()
        return

    print(f"Reading farfield data from: {args.file}")
    print(f"Using dipole model: {args.model}")

    # Read CSV file
    df = pd.read_csv(args.file)

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

    polar_filename = f"farfield_polar_{args.model}.png"
    three_d_filename = f"farfield_3d_{args.model}.png"

    polar_plots(data, label, args.model, polar_filename)
    three_d_plot(data, label, three_d_filename)

    #
    # Export .vtk, .vtu for Paraview
    #
    three_d_plot_vtk_simple(data, label, f"farfield_3d_{args.model}.vtk")

###############################################################################################################################
# Additional code from ClaudeAI to export diagram as VTK or VTU
###############################################################################################################################
def three_d_plot_vtk_simple(data, label, filename="farfield_3d"):
    """
    Simpler VTK export using PyVista (easier to use than VTK directly).
    Install with: pip install pyvista
    """
    import pyvista as pv

    E_mag = compute_field_magnitude(data)
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

    try:
        # Reshape for structured grid
        X = x.reshape(n_theta, n_phi)
        Y = y.reshape(n_theta, n_phi)
        Z = z.reshape(n_theta, n_phi)
        E_grid = E_mag.reshape(n_theta, n_phi)

        # Create structured grid with PyVista (much easier!)
        grid = pv.StructuredGrid(X, Y, Z)
        grid["E_magnitude"] = E_grid.flatten(order='F')  # PyVista uses Fortran order
        grid["theta"] = np.tile(theta_unique, n_phi)
        grid["phi"] = np.repeat(phi_unique, n_theta)

        # Save to VTK
        vtk_filename = f"{filename}.vtk"
        grid.save(vtk_filename)
        print(f"Saved VTK file: {vtk_filename}")

        # Optional: Create quick preview
        plotter = pv.Plotter(off_screen=True)
        plotter.add_mesh(grid, scalars="E_magnitude", cmap="viridis",
                         show_edges=False, lighting=True)
        plotter.add_scalar_bar("E magnitude", vertical=True)
        preview_filename = f"{filename}_preview.png"
        plotter.screenshot(preview_filename)
        print(f"Saved preview: {preview_filename}")

    except ValueError:
        # Point cloud fallback
        points = np.column_stack((x, y, z))
        cloud = pv.PolyData(points)
        cloud["E_magnitude"] = E_mag

        vtk_filename = f"{filename}_points.vtk"
        cloud.save(vtk_filename)
        print(f"Saved point cloud: {vtk_filename}")

###############################################################################################################################
# Main code to run
###############################################################################################################################

if __name__ == '__main__':
    main()
