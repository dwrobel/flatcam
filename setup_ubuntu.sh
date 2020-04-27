#!/bin/sh -e

# Ubuntu packages

sudo apt-get install -y \
	libfreetype6 \
	libfreetype6-dev \
	libgeos-dev \
	libpng-dev \
	libspatialindex-dev \
	python3-dev \
	python3-gdal \
	python3-pip \
	python3-pyqt5 \
	python3-pyqt5.qtopengl \
	python3-simplejson \
	python3-tk


#python3-imaging \


# Python packages

sudo -H python3 -m pip install --upgrade \
	pip \
	numpy \
	scipy \
	shapely \
	rtree \
	tk \
	lxml \
	cycler \
	python-dateutil \
	kiwisolver \
	dill \
	vispy \
	pyopengl \
	setuptools \
	svg.path \
	ortools \
	freetype-py \
	fontTools \
	rasterio \
	ezdxf \
	matplotlib \
	qrcode \
	reportlab \
	svglib

sudo -H easy_install -U distribute
