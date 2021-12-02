# Distributed Chat App

## Overview
This was developed as the final project for the course CS5523 Operating Systems. It attempts to develop a distributed chat application that is robust, scalable, and fault tolerant. The application comes with 4 components, the name service, the chat server, the database, and finally the client. 

## Prerequisites

`>=python3.8`

## Install
Download source code if not given

```
git clone https://github.com/scottcalebc/CS5523-final-project.git
```

Install requirements (recommend creating and runing the rest of the commands in a python virtual environtment before continuing)

``` 
pip3 install -r requirements.txt
```

Set helper script to executable
```
chmod +x buildProto.sh
```

## Building
After downloading the proto files need to be built. Navigate to the project's root directory and run one of the commands

```
./buildProto.sh build interfaces/
```
or
```
python3 -m grpc_tools.protoc -I. --python_out=interfaces/ --grpc_python_out=interfaces *.proto
```

## Running
To run the project the order of running the application is 

1. Name Server (src/name_server.py)
2. Database (src/database.py)
3. Chat server (src/server.py)
4. Client (src/client.py)

Run the following command

```
./buildProto run component -b
```

Or

```
PYTHONPATH=/path/to/project/root python3 component
```
where `component` is the components mentioned above

## Testing
A test script is provided to act like a fake client and send numerous messages during execution. To run ensure all components are running then run

```
./buildProto run test/test_client.py num -f test/wordlist.txt
```
wher `num` is the number of test clients you want to run in the background

Or
```
PYTHONPATH=/path/to/project/root python3 test/test_client.py -f test/wordlist.txt &
```
repeat for desired number of test clients
