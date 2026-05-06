# palace-aws-demo
Running palace AWD demo projects for EM simulations which are verified.

Workflow for working with FreeCAD->Salome->Gmsh->palace
  1. create model in FreeCAD
  2. export files as .step files
  3. import them into Salome (I used v2023 version)
  4. make partition object from them (this is needed to create right fragmented and continuous mesh object)
  5. explode partitioned object (https://www.youtube.com/watch?v=EcA5I9orOCg)
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

Palace AWS help page url: https://awslabs.github.io/palace/stable

This is how my environment in pycharm looks like when using palace which is running inside virtual box, this way I can edit all files at one place and not to be confused:
![pycharm_environment_for_simulation](https://github.com/user-attachments/assets/4064a9c0-a182-4d25-92b8-b42bfa09062f)

This is how editing mesh looks like in Salome MECA:
![image](https://github.com/user-attachments/assets/381c61ec-a815-4530-915e-6fdfe2646736)

Errors - explanation
====================
MFEM abort: (r,c,f) = (24,25,254)
 ... in function: int mfem::STable3D::operator()(int, int, int) const
 ... in file: /opt/palace-build/extern/mfem/general/stable3d.cpp:112

 This error means there is some error in mesh. Mostly overlapping meshlines or something else, rework it.

 Ports should be defined on planar flat region, not curved face or similar!!!

Linux palace solver compile from source
=======================================
- download Xubuntu installer
- create new virtual machine in VirtualBox
	- assign .iso file to virtual machine
	- make sure uncheck install VirtualGuest image to be able share folder from host pc (this failed during xubuntu installation on my pc, but after restart it's possible to install it from virtualbox menu)
		- left it unchecked, this causing problems, install later manualy
	- start machine

- install dependencies:
	> sudo apt install git
	> sudo apt install g++
	> sudo apt install openmpi-bin openmpi-common libopenmpi-dev
	> sudo apt install libblas64-dev libopenblas-dev
	> sudo apt install pkg-config

- to install virtualbox guest iso:
	> sudo apt install bzip2 tar
	> cd /run/media/johndoe/VBox.../
	> sudo ./VBoxLinuxAdditions.run

- install palace using tutorial: https://awslabs.github.io/palace/stable/install/#Build-from-source
	> git clone https://github.com/awslabs/palace.git
	> mkdir build && cd build
	> cmake ..
	> sudo make -j 6
	
- create cmd to run palace inside container??? (is this needed when palace is compiled from source?)
	> export PATH=$PATH:~/Documents/palace/build/palace-build

- add shared folder from host machine to virtual machine in virtualbox
- add current user to vbox group to be able access share folder
	> sudo usermod -aG vboxsf $USER
	
- enable ssh access:
	> sudo apt install openssh-server
- verify it's running
	> sudo systemctl status ssh
	
- install net-tools to be able get ethernet info like ifconfig:
	> sudo apt install net-tools

- my public exported virtual machine (name: johndoe, password: johndoe)
	> https://drive.google.com/drive/folders/1pA1Nmw41c2nvH8Xr1N0B96BZC-I-bx-f?usp=sharing