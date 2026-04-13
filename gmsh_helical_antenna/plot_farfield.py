from basicpalacesolverhelperpackage import PlotDiagramUtils

plotter = PlotDiagramUtils()
plotter.readFromFileAndPlotFarfield("sim_result/farfield-rE.csv", outputFile="farfield_3d_decibels.vtk", useDecibels=True, useNormalization=False)
plotter.readFromFileComputeDirectivityRadiationDiagram("sim_result_thin_wire/farfield-rE.csv", outputfile="farfield_3d_thin_wire_dB.vtk")
