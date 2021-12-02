#!/bin/bash

# These are set in shell when sourcing

proj_path=$(pwd)
py_path="$(which python)"
pyenvpath=${WORKON_HOME:-""}

venv() {
    if [[ -z $pyenvpath || $pyenvpath == "" ]]; then
        return
    fi
    if [[ "$py_path" == "$pyenvpath"* ]]; then
        return
    fi
    
    echo "Getting virtualenv path: $pyenvpath"
    pyenv="$(find $pyenvpath -iname "*final*" -depth 1)"
    echo "Finding project environment: $pyenv"

    source "$pyenv/bin/activate"
}

venvleave() {
    if [[ -z $pyenvpath || $pyenvpath == "" ]]; then
        return
    fi
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

runProgram() {
    echo "${@:3}"
    prog=$1
    logname="$2.log"
    bg="false"
    num=1
    args=()
    for var in "${@:3}"; do
        echo "Testing: $var"
        if [[ $var == "-b" ]]; then
            echo "Will run process in background"
            bg="true"
            shift
        elif [[ $var =~ [0-9]+ ]]; then
            echo "Setting number processes to run: $var"
            num=$var
            shift
        else
            echo "Adding $var to args"
            args+=( $var )
        fi
    done

    venv

    if [[ $bg == "true" || num -gt 1 ]]; then
        echo "Starting $prog ${args[@]} in background with log $logname..."
        for i in $(seq 1 $num); do
            python $prog "${args[@]}"&> $logname &
        done
    else
        echo "Running $prog ${args[@]}"
        python "$prog" "${args[@]}"
    fi

    venvleave
    
}

usage() {

    echo "Usage: ./buildProto.sh command"
    echo "  Commands:"
    echo "      build (proto_directory|proto_file) [out_directory]"
    echo "          Args:"
    echo "              proto_directory - Directory containin all proto files you want to compile"
    echo "              proto_file - Path and name of proto file you wish to copmile"
    echo "              out_directory - Directory where all compiled python files will be generated"
    echo "      run (path_to_file|name) [[num_of_process] [-b]] [[arg1] [arg2] ... [argN]]"
    echo "          Args:"
    echo "              path_to_file - file with path that should be run"
    echo "              name - name of standard chat components (i.e. name_server, server, client, database)"
    echo "              num_of_process - number of processes to spawn with component (implicitly signals background)"
    echo "              -b (background) - starts the request component in the background"
    echo "              args - arguments that need to be passed to the program"
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
            export PYTHONPATH="${PYTHONPATH}"
        else 
            echo "Setting python path for project for easy imports to $proj_path..."
            export PYTHONPATH="${PYTHONPATH}:$proj_path"
        fi
        ;;
    *)
        case $1 in
            "build")
                # ignore the first two arguments (i.e. the file name and the "build" subcommand)
                shift
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
            "run")
                if [[ "$PYTHONPATH" != *"$proj_path"* ]]; then
                    export PYTHONPATH="${PYTHONPATH}:$proj_path"
                fi
                if [[ -f $2 ]]; then
                    name="$(basename $2 | sed -r 's/\..*//')"
                    runProgram $2 $name "${@:3}"
                else
                    runProgram "src/$2.py" $2 "${@:3}"
                fi
                ;;
            "stop")
                ps aux | grep $2 | grep -v grep | awk '{print $2}' | xargs kill -9 -- 
                ;;
            *)
                usage
                ;;
        esac
    ;;
esac

