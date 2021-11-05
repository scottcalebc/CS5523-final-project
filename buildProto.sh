#!/bin/bash


build_proto() {
    python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. $1
}

usage() {

    echo "Usage: ./buildProto.sh proto"
    echo "      proto - Name of the proto file you wish to copmile"
    echo ""
    echo "Note:"
    echo "      Must be run within root directory of project"
}

if [ $# -gt 2 ]; then
    usage
fi

echo "Building proto file $1 ..."
build_proto $1
echo "Finished building"
proj_path=$(pwd)
echo "Setting python path for project for easy imports to $proj_path..."
export PYTHONPATH="$proj_path:$PTYHONPATH"

