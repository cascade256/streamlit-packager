#!/usr/bin/bash

#Setup paths so this script can be run from a different working directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
START_DIR=$PWD
STREAMLIT_SCRIPT=$(readlink -e $1)
cd $SCRIPT_DIR

python package.py $STREAMLIT_SCRIPT --name MyAwesomeApp --distpath $START_DIR --noconfirm