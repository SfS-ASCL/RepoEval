import argparse
import hashlib
import json
from json.decoder import JSONDecodeError
import os
import requests
import urllib3

from datetime import datetime
from lxml import etree
from create_html import write_to_file, create_statistics

class OAIEval:

    def __init__(self, acl_restricted='acl_restricted.txt'):
        with open(acl_restricted, 'r', encoding='utf-8') as in_f:
            self.acl_restricted = in_f.read().splitlines()


    def _add_error(self, error, cmdi):
        if self.errors.get(cmdi) is None:
            self.errors[cmdi] = []
        self.errors[cmdi].append(error)


    def _login(self, username, password):
        with requests.Session() as session:
            post = session.post('https://talar.sfb833.uni-tuebingen.de/erdora/login', 
                data = {"username": username, "password": password})
            self.session = session


    # def _session_duration(self, username, password):
    #     now = datetime.now()
    #     diff = now - self.session_start
    #     #print(diff.total_seconds()/3600)
    #     if diff.total_seconds()/3600 >= 1:
    #         print("RENEWED SESSION")
    #         self.session_start = datetime.now()
    #         self._login(username, password)


    # sometimes the connection to TALAR is suddenly lost
    # try connecting to an URL at least 3 times
    def _connect_to_URL(self, url, file=False):
        for i in range(3):
            try:
                if file:
                    # Download file as stream
                    with self.session.get(url, stream=True) as r:
                        r.raise_for_status()
                        with open("tmp_file", "wb") as f:
                            for chunk in r.iter_content(chunk_size=1024):
                                f.write(chunk)
                        return r.url
                else:
                    return self.session.get(url) # CMDI.xml
            except urllib3.exceptions.ProtocolError:
                print("http.client.RemoteDisconnected")
                continue
        self._add_error(f"Error {url} - No server response", url)


    def validate_oai(self, xml, evaluation, username, password):
        self.cmdi_counter = 0
        self.resource_counter = 0
        self.profiles = {}
        self.person_set = set()
        self.errors = {}
        self.session_start = datetime.now()

        tree = etree.parse(xml)
        

        self._login(username, password)
        
        all_cmdis = tree.xpath("//*[local-name()='record']")   
        self.cmdi_counter = len(all_cmdis) 

        # retrieve every ns4:record
        for cmdi in all_cmdis:
            handle = cmdi.xpath(".//*[local-name()='MdSelfLink']")[0]
            profile = cmdi.xpath(".//*[local-name()='Components']/*[1]")[0].tag.split('}')[-1]
            resources = cmdi.xpath(".//*[local-name()='ResourceProxy'][(contains(*[local-name()='ResourceType'],  'Resource'))]")
            persons = cmdi.xpath(".//*[local-name()='Person']")
            cmdi_page = self._connect_to_URL(handle.text)

            print(handle.text)   
            if evaluation and cmdi_page.status_code == 404:
                self._add_error(f"Error {handle.text} - 404", handle.text)
                # print(f"Error {handle.text} - 404")

            self.resource_counter += len(resources)
            self.count_profiles(profile)            
            self.get_person(persons)

            if evaluation:
                self._validate_resources(cmdi, handle, resources, username, password)
    
        # print stuff
        print("CMDIs:", self.cmdi_counter)
        print("Resources:", self.resource_counter)
        print("Persons:", len(self.person_set))
        print("Profiles:")
        for k,v in self.profiles.items():
            print(f"  {k}: {v}")

        if evaluation:
            return self.errors, {"cmdi_count": self.cmdi_counter,
                                    "resource_count": self.resource_counter,
                                    "person_count": len(self.person_set),
                                    "profiles": self.profiles}
        else:
            return {"cmdi_count": self.cmdi_counter,
                    "resource_count": self.resource_counter,
                    "person_count": len(self.person_set),
                    "profiles": self.profiles}


    def _validate_resources(self, cmdi, handle, resources, username, password):
        ns = {'ns1': 'http://www.clarin.eu/cmd/1'}
        for res_proxy in resources:
            resource_dict = {"size": None, "md5": None, "sha1": None, "sha256": None}
            res_handle = res_proxy.xpath(".//*[local-name()='ResourceRef']")[0].text
            print("    ", res_handle)

            # Check if Resource is online
            res_url = self._connect_to_URL(res_handle, file=True) # session.get(res_handle)
            #if res_status != 404:
            #    self._add_error(f"Error {res_handle} - 404", handle.text)
            #    continue
            
            # Check ACL settings of resource
            if not self._validate_acl(cmdi, res_url, username, password):
                self._add_error(f"Error {res_handle} - Access Control Settings incorrect", handle.text)
                print(f"Error {res_handle} - Access Control Settings incorrect", handle.text)
            
            # Check Checksums, if available
            res_proxy_list = cmdi.xpath(".//*[local-name()='ResourceProxyInfo'][@ns1:ref='" + 
                res_proxy.attrib["id"] +"']", namespaces=ns)
            
            if len(res_proxy_list) > 0:
                resource = res_proxy_list[0]
                #print("    ", resource.attrib['{http://www.clarin.eu/cmd/1}ref'])
                resource_dict["size"] = self._cmdi_checksums(resource, "Size")
                resource_dict["md5"] = self._cmdi_checksums(resource, "md5")
                resource_dict["sha1"] = self._cmdi_checksums(resource, "sha1")
                resource_dict["sha256"] = self._cmdi_checksums(resource, "sha256")

                if not self._validate_checksum(resource_dict):
                    self._add_error(f"Error {res_handle} - Checksums wrong", handle.text)
                    print(f"     Error {res_handle} - Checksums wrong", handle.text)
            
            os.remove("tmp_file")


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


    def _validate_checksum(self, checksums):  
        # extract size of file, seems more reliable than Content-Length, since the later
        # is not included if a resource is an XML file
        c_size = os.path.getsize("tmp_file")
        real_statistics = {
            "size": c_size,
            "md5": self._compute_checksum("md5"),
            "sha1": self._compute_checksum("sha1"),
            "sha256": self._compute_checksum("sha256")
        }

        for k, v in checksums.items():
            real_v = real_statistics[k]

            if v is not None and str(real_v) != str(v):
                return False   
        return True


    def _validate_acl(self, cmdi, page, username, password):
        availability = cmdi.xpath(".//*[local-name()='Access'][not(ancestor::*[local-name()='Source'])]/*[local-name()='Availability']")
        acl_url = "https://talar.sfb833.uni-tuebingen.de:8443/" + page[38:] + "/fcr:accessroles?effective"
        r = self._connect_to_URL(acl_url) # session.get(acl_url)  
        try:      
            acl_dict = json.loads(r.content)
        # often, the session got logged out and restricted ACL can't get downloaded
        except JSONDecodeError:
            print("JSONDecodeError")
            print(r.content)
            print("___")
            self._login(username, password)
            r = self._connect_to_URL(acl_url) 

            # in some instances, the URL does really not work
            try:
                acl_dict = json.loads(r.content)
            except JSONDecodeError:
                print("JSONDecodeError")
                return False
            
        # CMDI is restricted if ACL contains no "EVERYONE" key
        try:
            acl = availability[0].text.strip()
            if acl == "free for academic use, restricted use of videos": return True
            if acl in self.acl_restricted:
                t = acl_dict["EVERYONE"]
            else:
                t = acl_dict.get("EVERYONE")
                return len(t) > 0
        except:
            return True
        return False


    def _cmdi_checksums(self, resource, value):
        checksum = resource.xpath(".//*[local-name()='" + value + "']")
        if len(checksum) > 0:
            try:
                return checksum[0].text.strip()
            except AttributeError:
                return None
        return None


    def get_person(self, persons):
        for person in persons:
            first_name = person.xpath("./*[local-name()='firstName']")
            last_name = person.xpath("./*[local-name()='lastName']")
            try:
                name =  f"{first_name[0].text.strip()} {last_name[0].text.strip()}"
                self.person_set.add(name)
            except:
                pass    


    def count_profiles(self, profile):
        if self.profiles.get(profile) is None:
            self.profiles[profile] = 0

        self.profiles[profile] += 1


    def dump_error_log(self, file="output/error_log.txt"):
        dir = os.path.dirname(file)
        if not os.path.exists(dir):
            os.makedirs(dir)

        with open(file, 'w', encoding="utf-8") as out_f:
            for _, error_messages in self.errors.items():
                for error_message in error_messages:
                    out_f.write(f"{error_message}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create Statistics HTML Talar/Evaluate existing CMDIs')
    parser.add_argument("-s", "--statistics", help="Create Statistics HTML",
                    action="store_true")
    parser.add_argument("-e", "--eval", help="Evaluate all CMDIs Talar",
                    action="store_true")
    parser.add_argument("-o", "--output", help="Output Statistics HTML")
    parser.add_argument("-l", "--error", help="Output error log")
    parser.add_argument("-u", "--user", help="Talar username")
    parser.add_argument("-p", "--password", help="Talar password")
    args = parser.parse_args()

    if args.user is None or args.password is None:
        username = input("Username: ")
        password = input("Password: ")
    else:
        username = args.user
        password = args.password

    req = requests.get("https://talar.sfb833.uni-tuebingen.de/erdora/rest/oai?verb=ListRecords&metadataPrefix=cmdi")
    with open('oai_tmp.xml', 'wb') as f:
        f.write(req.content)

    e = OAIEval()
    errors, stats = e.validate_oai("oai_tmp.xml", evaluation=args.eval, username=username, password=password)
    e.dump_error_log(file=args.error)

    if args.statistics:
        html_code = create_statistics(stats, errors)
        write_to_file(html_code, file=args.output)

    os.remove("oai_tmp.xml")


    