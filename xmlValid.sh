#!/bin/bash
wget -O OAI.xml "https://talar.sfb833.uni-tuebingen.de/erdora/rest/oai?verb=ListRecords&metadataPrefix=cmdi"
XERCES_HOME=./xerces-2_12_1/
echo $XERCES_HOME
java -classpath $XERCES_HOME/xercesImpl.jar:$XERCES_HOME/xml-apis.jar:$XERCES_HOME/xercesSamples.jar sax.Counter $*