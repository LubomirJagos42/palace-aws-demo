# palace-aws-demo
Running palace AWD demo projects for EM simulations which are verified.

Workflow for working with FreeCAD->Salome->Gmsh->palace
  1. create model in FreeCAD
  2. export files as .step files
  3. import them into Salome (I used v2023 version)
  4. make partition object from them (this is needed to create right fragmented and continuous mesh object)
  5. explode partitioned object
  6. rename needed object (this is really picky step since you need explode volumes and shells)
  7. change for mesh view
  8. create mesh object over partitioned object (whole object which own all subojects)
  9. create submeshes for all child object and define tolerancies for submeshes
  10. recompute whole mesh
  11. observe mesh
  12. export mesh as .med file for Gmsh
  13. open mesh .med file in Gmsh
  14. export mesh as .msh file version 2.x is NEEDED!!!
  13. create .json simulation configurations (let's inspire already done simulation profiles) using .msh file
  14. run palace simulation over configuration .json file
  15. create plot result python script (mine is using panda library to print S11 params)

This is how my environment in pycharm looks like when using palace which is running inside virtual box, this way I can edit all files at one place and not to be confused:
![pycharm_environment_for_simulation](https://github.com/user-attachments/assets/4064a9c0-a182-4d25-92b8-b42bfa09062f)

This is how editing mesh looks like in Salome MECA:
![image](https://github.com/user-attachments/assets/381c61ec-a815-4530-915e-6fdfe2646736)
