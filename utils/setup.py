from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="basicpalacesolverhelperpackage",
    version="0.0.1",
    author="Lubomir Jagos",
    author_email="lubomir.jagos.42@gmail.com",
    description="Mesh creation and plot utilities for Palace EM solver or other FEM solver.",
    long_description="Basic object to manage geometries inside gmsh and create proper continous mesh to be usable in palace aws solver",
    long_description_content_type="text/markdown",
    url="https://github.com/LubomirJagos42/palace-aws-demo/tree/main/utils",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "numpy",
        "gmsh",
        "scipy",
        "pandas",
        # "other-package>=1.0.0",
    ],
)