#! /bin/bash
rm -r ./build
dub
python setup.py develop