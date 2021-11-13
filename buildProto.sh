#!/bin/bash

proj_path=$(pwd)

build_proto() {
    if [[ -f $1 ]]; then
        echo "Building proto file $1..."
        python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. $1
    else
        echo "Attempting to build all proto files in $1 directory"
        for proto_file in "$1*.proto"; do
            python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. $proto_file
        done
    fi
}

usage() {

    echo "Usage: ./buildProto.sh (proto_file|proto_path)"
    echo "      proto - Name of the proto file you wish to copmile"
    echo ""
    echo "Note:"
    echo "      Must be run within root directory of project"
}

build() {

    build_proto $1
    echo "Finished building"
    
    
}


case $# in
    0)
        echo "Setting python path (must be sourced) for project for easy imports to $proj_path..."
        export PYTHONPATH="$proj_path:$PTYHONPATH"
        ;;
    1)
        build $1
        ;;
    *)
        usage
    ;;
esac

