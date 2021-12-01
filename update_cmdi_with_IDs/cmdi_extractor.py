#import xml.etree.ElementTree as ET
from lxml import etree as ET
from entity_cache import EntityCache
import json
import re
import argparse
import os

class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


def read_cmdi(cmdi_path):
    with open(cmdi_path, encoding="utf-8") as in_f:
        try:
            parser = ET.XMLParser(remove_blank_text=True)
            tree = ET.parse(in_f, parser)
        except ET.ParseError as e:
            print("error while parsing xml -- valid CMDI file?")
            return str(e)
    root = tree.getroot()
    return root


def read_cmdi_fromsource(cmdi_source):
    parser = ET.XMLParser(remove_blank_text=True)
    tree = ET.fromstring(cmdi_source, parser)
    return tree


def get_name(node):
    name = ""
    for child in node:
        if "name" in child.tag.lower() or "agency" in child.tag.lower():
            if name != "":
                name += " " + child.text
            else:
                if child.text:
                    name += child.text
    if name == "":
        return None
    return name

def add_name(cache, name):
    if name not in cache and name is not None:
        cache[name] = set()
                          
def cmdi_to_cache(cmdi, cache):
    tags = ["Person", "Author", "Organisation"]
    for tag in tags:
        print(tag)
        for entity in cmdi.xpath(f".//*[local-name()='{tag}']"):
            name = get_name(entity)
            print(name)
            add_name(cache, name)
            for auth_id in entity.xpath(".//*[local-name()='AuthoritativeID']"):
                a_id = auth_id.xpath("./*[local-name()='id']")
                if len(a_id) > 0: a_id = a_id[0].text
                
                iss_auth = auth_id.xpath("./*[local-name()='issuingAuthority']")
                if len(iss_auth) > 0: 
                    iss_auth = iss_auth[0].text
                else:
                    iss_auth = ""
                
                if type(a_id) == type(""):
                    cache[name].add((a_id, iss_auth))

    #print(cache)
    

def cache_to_file(output, cache):
    with open(output, 'w', encoding="utf-8") as out_f:
        json.dump(cache, out_f, cls=SetEncoder)
        
def load_cache(input):
    cache = {}
    with open(input, 'r', encoding="utf-8") as in_f:
        tmp = json.load(in_f)
    for k, v in tmp.items():
        s = set()
        for i in v:
            s.add((i[0], i[1]))
        cache[k] = s
    return cache

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("path_to_cache",
                        help="the path for the cache that stores the entities and their authorative IDs. If there is "
                             "no existing cache under the specified path, set the flac new_cache to create a new "
                             "cache. if the cache is already present do not set the flag. the cache will be used and "
                             "updated.", type=str)
    parser.add_argument("cmdi_files", type=str,
                        help="the path to the directory that contains all cmdi files. can be a complex hierachy.")
    parser.add_argument("--new_cache", help="set this flag if you want to create a new cache",
                        action="store_true")
    args = parser.parse_args()
    
    if args.new_cache:
        cache = {}
    else:
        cache_to_file(args.path_to_cache)
    
    for subdir, dirs, files in os.walk(args.cmdi_files):
        if files:
            for file in files:
                cmdi = read_cmdi(subdir + "/" + file)
                print(file)
                cmdi_to_cache(cmdi, cache)
                
    cache_to_file(args.path_to_cache, cache)
    print(len(cache))
    