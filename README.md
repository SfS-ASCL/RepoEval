# RepoEval

`repo_eval.py`: Script to check for availability of PIDs (are they online?) and to check all checksums + filesize.

How to use:
`$python -o OUTPUT_FILE -u USERNAME -p PASSWORD` (username and password are optional)

_____________

`create_html.py`: Script to create Statistics HTML for TALAR and plot generation of mimetype size and count.

How to use:
`$python -i OAI.xml -o OUTPUT_DIRECTORY/` (`-is` is optional. If not defined, OAI.xml will get downloaded first)

_____________

`acl_check.py`: Script to compare current ACL settings to previous ones. Creates `report.csv` (unavailable ACLs + changes to previous ACL) + `acl.json` (JSON with all resources + associated ACL).

______________

`check_checksums.sh` and `check_checksums_local2.py`: Python2 script to compare `sha1` checksums directly on TALAR.

How to use:
`$ bash check_checksums.sh TARGET_DIR/ OUTPUT_DIR/` 

Creates `affected_cmdis.cv` (listing CMDIs which `sha1` was not found) and `not_in_cmdi.csv` (files not found in any CMDI)

______________

`update_cmdi_with_IDs/` contains a strongly modified, simplified version of the BioDataNER tool.

`cmdi_extractor.py` extracts all authoritative IDs from any `Person`, `Author` or `Organization` component and adds it to a cache.

How to use:
`$ python cmdi_extractor.py PATH_TO_CACHE PATH_TO_CMDIs --new_cache` (`--new-cache` flag is optional)

`cmdi_updater.py` takes the cache and updates every CMDI with missing authoritative IDs

How to use:
`$ python cmdi_updater.py PATH_TO_CACHE PATH_TO_CMDIs`

The cache is not a CSV anymore, but a JSON file. IDs outside of VIAF are now supported as well.
______________
Validate `OAI.xml`: There is no command-line tool/Python library that can handle the validation of XML files as complex as the `OAI.xml` (to my knowledge). Using `Xerces` (http://xerces.apache.org/xerces-c/), however works and is also used by http://oai.clarin-pl.eu/.
`xmlValid.sh` contains a sample script in how this can be done:

`$ bash xmlValid.sh -v -n -np -s -f OAI_File` (requires Java to be installed)