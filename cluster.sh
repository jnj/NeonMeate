#!/bin/bash

source venv/bin/activate

PYTHONPATH=$(pwd) python neonmeate/util/cluster.py "$1" -k 7 -e 200 --thresh 0.001 --space rgb

