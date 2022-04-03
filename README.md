# GraphDef
This repository intended to transfer def/lef file format into GraphDef which needed by the Circuit Learning model
step 1: install python-protoc: protobuf-python-3.6.0.tar.gz
step 2: generate graph_pb2.py :protoc tensorflow/core/framework/*.proto --python_out=.
step 3: build circuit learning docker : docker build --tag circuit_training:core -f tools/docker/ubuntu_circuit_training tools/docker/
step 4: in docker env :python read_file.py --lefin smic.lef --defin smic.def 
output: netlist.pbtxt and initial.plc
