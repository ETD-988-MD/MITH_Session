#!/bin/bash

cd /Users/Ericdunford/Dropbox/Programing/Python/MITH/pyzo2015a_mac/bin/
CWD=`pwd`
export DYLD_LIBRARY_PATH=$CWD/local_lib:$DYLD_LIBRARY_PATH

#cd bin
$CWD/ipython notebook