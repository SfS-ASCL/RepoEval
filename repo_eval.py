import argparse
import hashlib
import getpass
import json
from json.decoder import JSONDecodeError
import os
import requests
#import urllib3

from datetime import datetime
from lxml import etree
#from create_html import write_to_file, create_statistics



class OAIEval:

    def __init__(self, username, password, acl_restricted='acl_restricted.txt'):
        self.username = username
        self.password = password 
        self.session_start = datetime.now()
        self.errors = {}

        with open(acl_restricted, 'r', encoding='utf-8') as in_f:
            self.acl_restricted = in_f.read().splitlines()

    def login(self):
        with requests.Session() as session:
            post = session.post('https://talar.sfb833.uni-tuebingen.de/erdora/login', 
                data = {"username": self.username, "password": self.password})
            self.session = session

    def _session_duration(self):
        now = datetime.now()
        diff = now - self.session_start
        if diff.total_seconds()/3600 >= 1:
            self.session_start = datetime.now()
            self.login()

    def _download_file(self, url):
        with self.session.get(url, stream=True) as r:
            r.raise_for_status()
            with open("tmp_file", "wb") as f:
                for chunk in r.iter_content(chunk_size=1024):
                    f.write(chunk)
            return r.url

    # sometimes the connection to TALAR is suddenly lost
    # try connecting to an URL at least 3 times
    def connect_to_URL(self, url, file=False):
        for i in range(3):
            try:
                if file:
                    return self._download_file(url)
                else:
                    r = self.session.get(url) # CMDI.xml
                    assert(r.status_code != 404)
                    return r
            except Exception:
                print("URL failure")
                self.login()
                continue
        self.add_error(f"{url};404", url)


    def add_error(self, error, cmdi):
        if self.errors.get(cmdi) is None:
            self.errors[cmdi] = []
        self.errors[cmdi].append(error)

    def add_mimetype(self, mimetype, size):
        if self.mimetypes.get(mimetype) is None:
            self.mimetypes[mimetype] = {"size": 0, "count": 0}

        if size is not None:
            self.mimetypes[mimetype]["size"] += int(size)
            self.total_size += int(size)
        self.mimetypes[mimetype]["count"] += 1


    def validate_oai(self, xml):
        self.cmdi_counter = 0
        self.resource_counter = 0
        self.profiles = {}
        self.person_set = set()
        self.errors = {}
        tree = etree.parse(xml)

        self.login()
        
        all_cmdis = tree.xpath("//*[local-name()='record']")   

        # retrieve every ns4:record
        for cmdi in all_cmdis:
            cmdi_handle = cmdi.xpath(".//*[local-name()='MdSelfLink']")[0].text.strip()
            resources = cmdi.xpath(".//*[local-name()='ResourceProxy'][(contains(*[local-name()='ResourceType'],  'Resource'))]")
            cmdi_page = self.connect_to_URL(cmdi_handle)
            print(cmdi_handle)

            if cmdi_page is None:
                continue
   
            if cmdi_page.status_code == 404:
                self.add_error(f"{cmdi_handle};404", cmdi_handle)

            self._validate_resources(cmdi, cmdi_handle, resources)
    
        print(f"Finished, {len(self.errors)} CMDI files affected")
        return self.errors

    def _validate_resources(self, cmdi, cmdi_handle, resources):
        ns = {'ns1': 'http://www.clarin.eu/cmd/1'}
        for res_proxy in resources:
            res_handle = res_proxy.xpath(".//*[local-name()='ResourceRef']")[0].text.strip()
            res_proxy_list = cmdi.xpath(".//*[local-name()='ResourceProxyInfo'][@ns1:ref='" + 
                res_proxy.attrib["id"] +"']", namespaces=ns)
            print("    ", res_handle)

            # Check if Resource is online
            self._session_duration()
            res_url = self.connect_to_URL(res_handle, file=True)
            if res_url is None:
                continue
            
            # Check ACL settings of resource - use check_acl.py; checking for Availabilty label is unreliable
            # self._validate_acl(cmdi, res_url, res_handle, cmdi_handle)
            
            # Extract checksums
            if len(res_proxy_list) > 0:
                resource = res_proxy_list[0]
                self._validate_checksum(resource, res_handle, cmdi_handle)

            os.remove("tmp_file")

    # use check_acl.py; checking for Availabilty label is unreliable
    """
    def _validate_acl(self, cmdi, res_url, res_handle, cmdi_handle):
        availability = cmdi.xpath(".//*[local-name()='Access'][not(ancestor::*[local-name()='Source'])]/*[local-name()='Availability']")
        acl_url = "https://talar.sfb833.uni-tuebingen.de:8443/" + res_url[38:].replace("//", "/") + "/fcr:accessroles?effective"
        r = self.connect_to_URL(acl_url) 

        if r is None: 
            self.add_error(f"{acl_url}ACL is None", cmdi_handle)
            return
        try:      
            acl_dict = json.loads(r.content)
        except JSONDecodeError:
            print("JSONDecodeError")
            self.add_error(f"{acl_url};ACL can't be parsed", cmdi_handle)
            return
            
        # CMDI is restricted if ACL contains no "EVERYONE" key
        try:
            acl = availability[0].text.strip()
            if acl == "free for academic use, restricted use of videos": return
            if acl in self.acl_restricted:
                t = acl_dict["EVERYONE"]
            else:
                t = acl_dict.get("EVERYONE", [])

                if len(t) == 0:
                    self.add_error(f"{res_handle};ACL incorrect", cmdi_handle)
                return
        except:
            return # True
        self.add_error(f"{res_handle};ACL incorrect", cmdi_handle)
        """

    def _validate_checksum(self, resource, res_handle, handle):  
        valid = True
        cmdi_checksums = {}        
        cmdi_checksums["size"] = self._cmdi_checksums(resource, "Size")
        cmdi_checksums["md5"] = self._cmdi_checksums(resource, "md5")
        cmdi_checksums["sha1"] = self._cmdi_checksums(resource, "sha1")
        cmdi_checksums["sha256"] = self._cmdi_checksums(resource, "sha256")

        c_size = os.path.getsize("tmp_file")
        calc_checksums = {
            "size": c_size,
            "md5": self._compute_checksum("md5"),
            "sha1": self._compute_checksum("sha1"),
            "sha256": self._compute_checksum("sha256")
        }

        for k, v in cmdi_checksums.items():
            calc_v = calc_checksums[k]

            if v is not None and str(calc_v) != str(v) and str(v).strip() != "":
                self.add_error(f"{res_handle};Checksums wrong;CMDI: {str(v)};Computed: {str(calc_v)} [{k}]", handle)
                valid = False   
        return valid


    def _cmdi_checksums(self, resource, value):
        checksum = resource.xpath(".//*[local-name()='" + value + "']")
        if len(checksum) > 0:
            try:
                return checksum[0].text.strip()
            except AttributeError:
                return None
        return None

    def _compute_checksum(self, checksum):
        with open("tmp_file", "rb") as f:
            file_hash = hashlib.sha256()
            if checksum == "md5":
                file_hash = hashlib.md5()
            elif checksum == "sha1":
                file_hash = hashlib.sha1()     
            while chunk := f.read(8192):
                file_hash.update(chunk)
        return file_hash.hexdigest()

    
    def dump_error_log(self, file="output/error_log.txt"):
        if '/' in file:
            dir = os.path.dirname(file)
            if not os.path.exists(dir):
                os.makedirs(dir)

        with open(file, 'w', encoding="utf-8") as out_f:
            for cmdi_url, error_messages in self.errors.items():
                out_f.write(cmdi_url + "\n")
                for error_message in error_messages:
                    out_f.write(f"    {error_message}\n")
                out_f.write("\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create Statistics HTML Talar/Evaluate existing CMDIs')
    parser.add_argument("-o", "--output", help="Output error log")
    parser.add_argument("-u", "--user", help="Talar username")
    parser.add_argument("-p", "--password", help="Talar password")
    args = parser.parse_args()

    if args.user is None or args.password is None:
        username = input("Username: ")
        password = getpass.getpass("Password: ")
    else:
        username = args.user
        password = args.password

    req = requests.get("https://talar.sfb833.uni-tuebingen.de/erdora/rest/oai?verb=ListRecords&metadataPrefix=cmdi")
    with open('oai_tmp.xml', 'wb') as f:
        f.write(req.content)

    e = OAIEval(username=username, password=password)
    errors = e.validate_oai("oai_tmp.xml")
    e.dump_error_log(file=args.output)

    os.remove("oai_tmp.xml")