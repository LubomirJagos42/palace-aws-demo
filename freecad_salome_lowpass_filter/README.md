# low-pass filter simulated in palace aws
Low-pass filter example, this filter was designed by random to be appr. lowpass at 2GHz. Simulated in palace to show how to do it right.

Here is what I have done:
	1. tried to do as it was in FreeCAD, model was complex and there were errors from MFEM library used by palace
	2. model reworked to have filter and ground as simple plane
	3. mesh was set to be coarse, also tolerance to reach set to 1e-3 to be coarse and have fast simulation with small count of iteration for each step
	
Here is result on picture below what was expected and also same example done in openEMS have same result :)

![image](https://github.com/user-attachments/assets/336fadb5-ddf6-4b8d-aafc-ab4f2bc4d479)

![image](https://github.com/user-attachments/assets/de6b41d4-1c32-4e13-81d3-97d26597ff81)
