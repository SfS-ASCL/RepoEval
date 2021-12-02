import argparse
import hashlib
import getpass
import json
from json.decoder import JSONDecodeError
import os
import requests
import urllib3

from datetime import datetime
import xml.etree.ElementTree as ET




class OAIEval:

    def __init__(self, username, password, acl_restricted='acl_restricted.txt'):
        self.username = username
        self.password = password 
        self.session_start = datetime.now()
        self.errors = {}

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

    # sometimes the connection to TALAR is suddenly lost
    # try connecting to an URL at least 3 times
    def connect_to_URL(self, url):
        for i in range(3):
            try:
                r = self.session.get(url)
                assert(r.status_code != 404)
                return r
            except Exception:
                #print("URL failure")
                self.login()
                continue
        self.add_error(f"{url};404", url)


    def add_error(self, error, cmdi):
        if self.errors.get(cmdi) is None:
            self.errors[cmdi] = []
        self.errors[cmdi].append(error)


    def validate_oai(self, xml):
        self.acl_dict = {}
        self.login()
        
        tree = ET.parse(xml)
        root = tree.getroot()
        all_cmdis = root.findall(".//{http://www.openarchives.org/OAI/2.0/}record")
        
        for cmdi in all_cmdis:
            # get the correct component namespace; (calling next(ite)) is not working for some reason
            header = cmdi.find(".//{http://www.clarin.eu/cmd/1}Components")
            c = 0
            for i in header.iter():
                if c == 1: break
                c += 1
            comp_ns = i.tag.split('}')[0][1:]

            cmdi_handle = cmdi.find(".//*{http://www.clarin.eu/cmd/1}MdSelfLink").text.strip()
            # print(cmdi_handle)
            
            resources_tmp = cmdi.findall(".//*{http://www.clarin.eu/cmd/1}ResourceProxy")
            resources = [ resource for resource in resources_tmp if resource.find("./{http://www.clarin.eu/cmd/1}ResourceType").text == 'Resource']
            res_proxy_list_info = cmdi.find(".//{"+comp_ns+"}ResourceProxyListInfo")            
            
            for res_proxy in resources:
                if res_proxy_list_info is None:
                    continue
                res_handle = res_proxy.find("{http://www.clarin.eu/cmd/1}ResourceRef").text.strip()
                try:
                    redirect_url = requests.head(res_handle, allow_redirects=True)
                except Exception:
                    self.add_error(f"{res_handle};too many redirects", res_handle)
                    continue 
                
                # print(redirect_url.url)
                self.acl_dict[res_handle] = self._validate_acl(cmdi, redirect_url.url, res_handle, cmdi_handle)
            #break
        return self.acl_dict
                


    def _validate_acl(self, cmdi, res_url, res_handle, cmdi_handle):
        acl_url = "https://talar.sfb833.uni-tuebingen.de:8443/" + res_url[38:].replace("//", "/") + "/fcr:accessroles?effective"
        r = self.connect_to_URL(acl_url) 

        if r is None: 
            self.add_error(f"{acl_url};ACL is None", cmdi_handle)
            return {"ERROR": "ACL is None"}
        try:      
            acl_dict = json.loads(r.content)
        except JSONDecodeError:
            print("JSONDecodeError")
            self.add_error(f"{acl_url};ACL can't be parsed ", cmdi_handle)
            return {"ERROR": ["ACL can't be parsed", str(r.content)]}
            
        return acl_dict

def compare_acls(cur_acl_dict, old_acl_dict):
    cur_set = set(cur_acl_dict.keys())
    old_set = set(old_acl_dict.keys())
    
    diff_cur_old = cur_set - old_set
    diff_old_cur = old_set - cur_set
    shared = cur_set.intersection(old_set)
    
    print("Resources added since last check:")
    for diff in diff_cur_old: print(diff)
    
    print()
    print("Resources missing from last check:")
    for diff in diff_old_cur: print(diff)
    
    print()
    print("ACLs that got changed:")
    for resource in shared:
        old_acl = old_acl_dict[resource]
        cur_acl = cur_acl_dict[resource]
        
        if old_acl != cur_acl:
            print(f"{resource} ACL changed:\n    OLD:{old_acl}\n    NEW:{cur_acl}")
  
    
def dump_acl(acl_dict, file="output/acl_dict.json"):
    path = ""
    if '/' in file:
        path = file.rpartition('/')
        dir = os.path.dirname(file)
        if not os.path.exists(dir):
            os.makedirs(dir)

    with open(file, 'w', encoding="utf-8") as out_f:
        json.dump(acl_dict, out_f)
        
    with open(f"{path}/acl_dict_{datetime.today().strftime('%Y-%m-%d')}", 'w', encoding="utf-8") as out_f:
        json.dump(acl_dict, out_f)
        
        
def load_acl(file):
    with open(file, 'r', encoding='utf-8') as in_f:
        acl_dict = json.load(in_f)
    return acl_dict


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create Statistics HTML Talar/Evaluate existing CMDIs')
    parser.add_argument("-o", "--output", help="Output ACL JSON")
    parser.add_argument("-a", "--acl", help="Old ACL JSON")
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
    acl_dict = e.validate_oai("oai_tmp.xml")
    
    if args.acl is not None:
        old_acl = load_acl(args.acl)
        compare_acls(acl_dict, old_acl)
    dump_acl(acl_dict, file=args.output)
    os.remove("oai_tmp.xml")