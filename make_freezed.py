# ##########################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 12/20/2018                                         #
# MIT Licence                                              #
#                                                          #
# Creates a portable copy of FlatCAM, including Python     #
# itself and all dependencies.                             #
#                                                          #
# This is not an aid to install FlatCAM from source on     #
# Windows platforms. It is only useful when FlatCAM is up  #
# and running and ready to be packaged.                    #
# ##########################################################

# ##########################################################
# File Modified: Marius Adrian Stanciu                     #
# Date: 3/10/2019                                          #
# ##########################################################


# Files not needed: Qt, tk.dll, tcl.dll, tk/, tcl/, vtk/,
#   scipy.lib.lapack.flapack.pyd, scipy.lib.blas.fblas.pyd,
#   numpy.core._dotblas.pyd, scipy.sparse.sparsetools._bsr.pyd,
#   scipy.sparse.sparsetools._csr.pyd, scipy.sparse.sparsetools._csc.pyd,
#   scipy.sparse.sparsetools._coo.pyd

import os
import site
import sys
import platform
from cx_Freeze import setup, Executable

# this is done to solve the tkinter not being found
PYTHON_INSTALL_DIR = os.path.dirname(os.path.dirname(os.__file__))
os.environ['TCL_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tcl8.6')
os.environ['TK_LIBRARY'] = os.path.join(PYTHON_INSTALL_DIR, 'tcl', 'tk8.6')

# Get the site-package folder, not everybody will install
# Python into C:\PythonXX
site_dir = site.getsitepackages()[1]

include_files = []

include_files.append((os.path.join(site_dir, "shapely"), "shapely"))
include_files.append((os.path.join(site_dir, "svg"), "svg"))
include_files.append((os.path.join(site_dir, "svg/path"), "svg"))
include_files.append((os.path.join(site_dir, "vispy"), "vispy"))
include_files.append((os.path.join(site_dir, "vispy/app"), "vispy/app"))
include_files.append((os.path.join(site_dir, "vispy/app/backends"), "vispy/app/backends"))
# include_files.append((os.path.join(site_dir, "matplotlib"), "matplotlib"))
include_files.append((os.path.join(site_dir, "rtree"), "rtree"))

if platform.architecture()[0] == '64bit':
    include_files.append((os.path.join(site_dir, "google"), "google"))
    include_files.append((os.path.join(site_dir, "google/protobuf"), "google/protobuf"))
    include_files.append((os.path.join(site_dir, "ortools"), "ortools"))

include_files.append(("locale", "lib/locale"))
include_files.append(("postprocessors", "lib/postprocessors"))
include_files.append(("share", "lib/share"))
include_files.append(("flatcamGUI/VisPyData", "lib/vispy"))
include_files.append(("config", "lib/config"))

include_files.append(("README.md", "README.md"))
include_files.append(("LICENSE", "LICENSE"))

base = None

# Lets not open the console while running the app
if sys.platform == "win32":
    base = "Win32GUI"

if platform.architecture()[0] == '64bit':
    buildOptions = dict(
        include_files=include_files,
        excludes=['scipy', 'pytz'],
        # packages=['OpenGL','numpy','vispy','ortools','google']
        # packages=['numpy','google', 'rasterio'] # works for Python 3.7
        packages=['opengl', 'numpy', 'google', 'rasterio'],   # works for Python 3.6.5 and Python 3.7.1
    )
else:
    buildOptions = dict(
        include_files=include_files,
        excludes=['scipy', 'pytz'],
        # packages=['OpenGL','numpy','vispy','ortools','google']
        # packages=['numpy', 'rasterio']  # works for Python 3.7
        packages=['opengl', 'numpy', 'rasterio'],   # works for Python 3.6.5 and Python 3.7.1
    )

if sys.platform == "win32":
    buildOptions["include_msvcr"] = True

print("INCLUDE_FILES", include_files)


def getTargetName():
    my_OS = platform.system()
    if my_OS == 'Linux':
        return "FlatCAM"
    elif my_OS == 'Windows':
        return "FlatCAM.exe"
    else:
        return "FlatCAM.dmg"


exe = Executable("FlatCAM.py", icon='share/flatcam_icon48.ico', base=base, targetName=getTargetName())

setup(
    name="FlatCAM",
    author="Juan Pablo Caram",
    version="8.9",
    description="FlatCAM: 2D Computer Aided PCB Manufacturing",
    options=dict(build_exe=buildOptions),
    executables=[exe]
)
