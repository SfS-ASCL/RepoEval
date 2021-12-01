import argparse
import os
from collections import OrderedDict
import xml.etree.ElementTree as ET
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
    checksum_dict = OrderedDict() # form {resource_handle: sha1_sum}
    ns = {'ns1': 'http://www.clarin.eu/cmd/1',
          'ns4': 'http://www.openarchives.org/OAI/2.0/'}
    
    tree = ET.parse(xml)
    root = tree.getroot()
    all_cmdis = root.findall(".//{"+ns['ns4']+"}record")
    
    for cmdi in all_cmdis:
        # get the correct component namespace; (calling next(ite)) is not working for some reason
        header = cmdi.find(".//{http://www.clarin.eu/cmd/1}Components")
        c = 0
        for i in header.iter():
            if c == 1: break
            c += 1
        comp_ns = i.tag.split('}')[0][1:]

        cmdi_handle = cmdi.find(".//*{http://www.clarin.eu/cmd/1}MdSelfLink").text.strip()
        print(cmdi_handle)
        
        resources_tmp = cmdi.findall(".//*{http://www.clarin.eu/cmd/1}ResourceProxy")
        resources = [ resource for resource in resources_tmp if resource.find("./{http://www.clarin.eu/cmd/1}ResourceType").text == 'Resource']
        res_proxy_list_info = cmdi.find(".//{"+comp_ns+"}ResourceProxyListInfo")            
        
        for res_proxy in resources:
            if res_proxy_list_info is None:
                continue
            res_handle = res_proxy.find("{http://www.clarin.eu/cmd/1}ResourceRef").text.strip()
            res_id = res_proxy.attrib["id"]
            resource = res_proxy_list_info.find("{"+comp_ns+"}ResourceProxyInfo[@{http://www.clarin.eu/cmd/1}ref='"+res_id+"']")
            
            if resource is not None:
                sha1_sum = _cmdi_checksums(resource, "sha1", comp_ns)
                if sha1_sum is not None and len(sha1_sum) > 1:
                    checksum_dict[sha1_sum] = res_handle
                    
    return checksum_dict

        
def _cmdi_checksums(resource, value, comp_ns):
        checksum = resource.find(".//{"+comp_ns+"}" + value)
        if checksum is not None:
            try:
                return checksum.text.strip()
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
    parser.add_argument("-i", "--input", help="Input OAI XML")
    parser.add_argument("-d", "--dir", help="Root directory")
    parser.add_argument("-o", "--output", help="Output directory")
    args = parser.parse_args()
    
    input_file = args.input
    root_dir = args.dir
    output = args.output
    
    checksum_dict = collect_checksums(input_file)
    not_in_cmdi, affected_cmdis = check_checksums(root_dir, checksum_dict)
    write_to_csv(not_in_cmdi, affected_cmdis, output_dir=output)