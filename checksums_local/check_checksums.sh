#!/bin/bash
echo "Target Dir: $1"
echo "Output Dir: $2"
wget -O OAI.xml "https://talar.sfb833.uni-tuebingen.de/erdora/rest/oai?verb=ListRecords&metadataPrefix=cmdi"
python2 check_checksums_local2.py -i OAI.xml -d "$1" -o "$2"