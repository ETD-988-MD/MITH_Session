#!/bin/bash
mv $PREFIX/pythonapp $PREFIX/python.app
cd $PREFIX/python.app/Contents
ln -s ../../lib .
