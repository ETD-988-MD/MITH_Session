#!/bin/bash

cd $(dirname $0)

CWD=`pwd`
export DYLD_LIBRARY_PATH=$CWD/local_lib:$DYLD_LIBRARY_PATH

#cd bin
$CWD/bin/ipython notebook
