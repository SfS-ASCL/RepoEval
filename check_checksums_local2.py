import argparse
import os
import requests
from lxml import etree
import codecs

def check_checksums(root_dir, checksum_dict):
    visited_resources = set()
    not_in_cmdi = []
    affected_cmdis = []
    
    for dir in os.walk(root_dir):
        cur_dir = dir[0]
        if "trash" in cur_dir:
            continue
        
        files = dir[2]
        full_path = os.path.abspath(cur_dir)
        
        for file in files:
            if str(file) in checksum_dict:
                if file in visited_resources:
                    not_in_cmdi.append(file + ";" + full_path + ";sha1sum exists twice or more on server")
                    #print(f"{file};{full_path};sha1sum exists twice or more")
                visited_resources.add(str(file))
            else:
                not_in_cmdi.append(file + ";" + full_path + ";not in any CMDI")
                #print(f"File: {file} in DIR: {full_path} not in any CMDI")
                
    for sha1_sum, res_handle in checksum_dict.items():
        if sha1_sum not in visited_resources:
            affected_cmdis.append(res_handle + ";" + sha1_sum + ";missing or faulty")
            #print(f"{res_handle};{sha1_sum};missing or faulty")
                
    return not_in_cmdi, affected_cmdis
                
            
def collect_checksums(xml):
    checksum_dict = {} # form {resource_handle: sha1_sum}
    ns = {'ns1': 'http://www.clarin.eu/cmd/1'}
    
    tree = etree.parse(xml)
    all_cmdis = tree.xpath("//*[local-name()='record']")
    
    
    for cmdi in all_cmdis:
        cmdi_handle = cmdi.xpath(".//*[local-name()='MdSelfLink']")[0].text.strip()
        resources = cmdi.xpath(".//*[local-name()='ResourceProxy'][(contains(*[local-name()='ResourceType'],  'Resource'))]")
        #print(cmdi_handle)
        
        for res_proxy in resources:
            res_handle = res_proxy.xpath(".//*[local-name()='ResourceRef']")[0].text.strip()
            res_proxy_list = cmdi.xpath(".//*[local-name()='ResourceProxyInfo'][@ns1:ref='" + 
                res_proxy.attrib["id"] +"']", namespaces=ns)
            #print("    ", res_handle)
            
            
            if len(res_proxy_list) > 0:
                resource = res_proxy_list[0]
                sha1_sum = _cmdi_checksums(resource, "sha1")
                #print("    ", sha1_sum) 
                if sha1_sum is not None and len(sha1_sum) > 1:               
                    checksum_dict[sha1_sum] = res_handle
                    
    return checksum_dict

        
def _cmdi_checksums(resource, value):
        checksum = resource.xpath(".//*[local-name()='" + value + "']")
        if len(checksum) > 0:
            try:
                return checksum[0].text.strip()
            except AttributeError:
                return None
        return None        


def write_to_csv(not_in_cmdi, affected_cmdis, output_dir="output/"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
                
    with codecs.open(output_dir+"not_in_cmdi.csv", 'w', 'utf-8') as f:
        f.write("File;Directory;Error\n")
        for element in not_in_cmdi:
            f.write(element + "\n")
            
    with codecs.open(output_dir+"affected_cmdis.csv", 'w', 'utf-8') as f:
        f.write("ResourceHandle;Sha1;Error\n")
        for element in affected_cmdis:
            f.write(element + "\n")
    
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create Statistics HTML Talar/Evaluate existing CMDIs')
    # parser.add_argument("-i", "--input", help="Input OAI XML")
    parser.add_argument("-d", "--dir", help="Root directory")
    parser.add_argument("-o", "--output", help="Output directory")
    args = parser.parse_args()
    
    #input_file = "test_files/demo_oai2.xml"
    #root_dir = "./test_dir/"
    input_file = 'oai_tmp.xml'
    root_dir = args.dir
    output = args.output
    
    req = requests.get("https://talar.sfb833.uni-tuebingen.de/erdora/rest/oai?verb=ListRecords&metadataPrefix=cmdi")
    with open('oai_tmp.xml', 'wb') as f:
        f.write(req.content)
    
    checksum_dict = collect_checksums(input_file)
    not_in_cmdi, affected_cmdis = check_checksums(root_dir, checksum_dict)
    write_to_csv(not_in_cmdi, affected_cmdis, output_dir=output)
    #print(checksum_dict)