import os
import sys

examplesDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(examplesDir, 'utils'))

from basicpalacesolverhelperpackage import PlotDiagramUtils

plotter = PlotDiagramUtils()
plotter.readFromFileComputeDirectivityRadiationDiagram("sim_result_farfield/farfield-rE.csv", outputfile="inverted_f_antenna_farfield.vtk")

