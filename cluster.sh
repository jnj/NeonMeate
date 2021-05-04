#!/bin/bash

source venv/bin/activate

PYTHONPATH=$(pwd) python neonmeate/util/cluster.py "$1" -k 9 -p 50 --thresh 0.001 --space rgb

