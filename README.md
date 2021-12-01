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