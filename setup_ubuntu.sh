#!/bin/sh -e

apt-get install libpng-dev libfreetype6 libfreetype6-dev python-dev python-simplejson python-qt4 python-numpy python-scipy python-matplotlib libgeos-dev python-shapely python-pip libspatialindex-dev
easy_install -U distribute
pip install --upgrade matplotlib Shapely
pip install rtree
pip install svg.path
