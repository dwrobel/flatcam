#!/bin/bash
sudo apt install --reinstall libpng-dev libfreetype6 libfreetype6-dev libgeos-dev libspatialindex-dev
sudo apt install --reinstall python3-dev python3-pyqt5 python3-pyqt5.qtopengl python3-gdal python3-simplejson
sudo apt install --reinstall python3-pip python3-tk

sudo python3 -m pip install --upgrade pip numpy scipy shapely rtree tk lxml cycler python-dateutil kiwisolver dill
sudo python3 -m pip install --upgrade vispy pyopengl setuptools svg.path ortools freetype-py fontTools rasterio ezdxf
sudo python3 -m pip install --upgrade matplotlib qrcode