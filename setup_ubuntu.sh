#!/bin/sh -e

# Ubuntu packages

sudo apt-get install -y \
	libfreetype6 \
	libfreetype6-dev \
	libgeos-dev \
	libpng-dev \
	libspatialindex-dev \
	qt5-style-plugins \
	python3-dev \
	python3-gdal \
	python3-pip \
	python3-pyqt5 \
	python3-pyqt5.qtopengl \
	python3-simplejson \
	python3-tk


# Python packages

sudo -H python3 -m pip install --upgrade \
	pip \
	numpy \
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
	pyqt5 \
	reportlab \
	svglib \
	pyserial \
	testresources

sudo -H easy_install -U distribute
