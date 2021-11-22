#!/bin/bash

proj_path=$(pwd)
py_path="$(which python)"
pyenvpath=${WORKON_HOME:-"/Users/calebcscott/.virtualenvs"}

venv() {
    if [[ "$py_path" == "$pyenvpath"* ]]; then
        return
    fi
    
    echo "Getting virtualenv path: $pyenvpath"
    pyenv="$(find $pyenvpath -iname "*final*" -depth 1)"
    echo "Finding project environment: $pyenv"

    source "$pyenv/bin/activate"
}

venvleave() {
    if [[ "$py_path" == "$pyenvpath"* ]]; then
        return
    fi
    deactivate
}

build_proto() {

    if [[ $# == 2 ]]; then
        out_dir=$2
    else 
        out_dir="."
    fi

    venv

    if [[ -f $1 ]]; then
        echo "Building proto file $1..."
        python3 -m grpc_tools.protoc -I. --python_out=$out_dir --grpc_python_out=$out_dir $1
    else
        echo "Attempting to build all proto files in $1 directory"
        for proto_file in $1/*.proto; do
            echo "Building $(basename $proto_file)..."
            python3 -m grpc_tools.protoc -I. --python_out=$out_dir --grpc_python_out=$out_dir $proto_file
        done
    fi

    venvleave
    echo "Finished building"
}

usage() {

    echo "Usage: ./buildProto.sh command"
    echo "  Commands:"
    echo "      build (proto_directory|proto_file) [out_directory]"
    echo "          Args:"
    echo "              proto_directory - Directory containin all proto files you want to compile"
    echo "              proto_file - Path and name of proto file you wish to copmile"
    echo "              out_directory - Directory where all compiled python files will be generated"
    echo "      clean (directory)"
    echo "          Args:"
    echo "              directory - Directory containing all generated python files you want to remove"
    echo ""
    echo "Examples:"
    echo "  ./buildProto build interfaces"
    echo "      This will build all the proto files within the interfaces directory"
    echo "  ./buildProto build interfaces/chatserver.proto"
    echo "      This will build the chatserver proto file"
    echo "  ./buildProto clean interfaces"
    echo "      This will remove all generated python files under interfaces directory"
    echo "Note:"
    echo "      Must be run within root directory of project"
    echo "      gRPC protoc will generated an interfaces directory under out_directory if compiling out of source"

}


case $# in
    0)
        if [[ "$PYTHONPATH" == *"$proj_path"* ]]; then
            echo "Python path already set for project root"
        else 
            echo "Setting python path (must be sourced) for project for easy imports to $proj_path..."
            export PYTHONPATH="${PYTHONPATH}:$proj_path"
        fi
        ;;
    *)
        case $1 in
            "build")
                # ignore the first two arguments (i.e. the file name and the "build" subcommand)
                shift
                echo "Cmd args: ${@}"
                
                build_proto "${@}"
                ;;
            "clean")
                if [[ -d $2 ]]; then
                    echo "Cleaning out $2 directory for generated python files"
                    for py_file in $2/*pb2*.py; do 
                        echo "Removing $(basename $py_file)"
                        rm $py_file &> /dev/null
                    done
                fi
                ;;
            *)
                usage
                ;;
        esac
    ;;
esac

