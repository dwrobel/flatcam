# ###########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
#                                                          #
# Creates a portlable copy of FlatCAM, including Python    #
# itself and all dependencies.                             #
#                                                          #
# This is not an aid to install FlatCAM from source on     #
# Windows platforms. It is only useful when FlatCAM is up  #
# and running and ready to be packaged.                    #
# ###########################################################

# Files not needed: Qt, tk.dll, tcl.dll, tk/, tcl/, vtk/,
#   scipy.lib.lapack.flapack.pyd, scipy.lib.blas.fblas.pyd,
#   numpy.core._dotblas.pyd, scipy.sparse.sparsetools._bsr.pyd,
#   scipy.sparse.sparsetools._csr.pyd, scipy.sparse.sparsetools._csc.pyd,
#   scipy.sparse.sparsetools._coo.pyd

import os
import site
import sys
from cx_Freeze import setup, Executable

# this is done to solve the tkinter not being found (Python3)
# still the DLL's need to be copied to the lib folder but the script can't do it
PYTHON_INSTALL_DIR = os.path.dirname(os.path.dirname(os.__file__))
os.environ['TCL_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tcl8.6')
os.environ['TK_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tk8.6')

# # Get the site-package folder, not everybody will install
# # Python into C:\PythonXX
site_dir = site.getsitepackages()[1]

include_files = [
    (os.path.join(site_dir, "shapely"), "shapely"),
    (os.path.join(site_dir, "svg"), "svg"),
    (os.path.join(site_dir, "svg/path"), "svg"),
    (os.path.join(site_dir, "matplotlib"), "matplotlib"),
    ("share", "share"), (os.path.join(site_dir, "rtree"), "rtree"),
    ("README.md", "README.md"),
    ("LICENSE", "LICENSE")
]

base = None

# # Lets not open the console while running the app
if sys.platform == "win32":
    base = "Win32GUI"

buildOptions = dict(
    include_files=include_files,
    # excludes=['PyQt5', 'tk', 'tcl']
    excludes=['scipy.lib.lapack.flapack.pyd',
              'scipy.lib.blas.fblas.pyd',
              'QtOpenGL4.dll']
)

print(("INCLUDE_FILES", include_files))

exec(compile(open('clean.py').read(), 'clean.py', 'exec'))

setup(
    name="FlatCAM",
    author="Juan Pablo Caram",
    version="8.5",
    description="FlatCAM: 2D Computer Aided PCB Manufacturing",
    options=dict(build_exe=buildOptions),
    executables=[Executable("FlatCAM.py", icon='share/flatcam_icon48.ico', base=base)]
)
