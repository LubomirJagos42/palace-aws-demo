## Simple package to create mesh for palace aws solver easier
author: Lubomir Jagos

date: March 2026

# BasicMfemMesher

Mesh creation utilities for Palace electromagnetic solver.

## Installation
```bash
pip install basicmfemmesher
```

## Usage
```python
from basicmfemmesher import BasicMfemMesher

mesher = BasicMfemMesher()
mesher.create_mesh(...)
mesher.export_to_palace("output.msh")
```