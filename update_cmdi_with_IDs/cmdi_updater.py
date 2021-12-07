from cmdi_extractor import load_cache, read_cmdi, get_name
from unicodedata import name
from lxml import etree as ET
import argparse
import os


def add_id(parent_node, cur_ids, namespace, cache_ids):
    # if ID not already in CMDI, add it from the cache
    for id_tuple in cache_ids:
        id = id_tuple[0]
        issuing_auth = id_tuple[1]
        
        if id in cur_ids:
            continue
        
        auth_id = ET.SubElement(parent_node, "{"+namespace+"}AuthoritativeID")
        auth_id_child = ET.SubElement(auth_id, "{"+namespace+"}id").text = id
        auth_id_child2 = ET.SubElement(auth_id, "{"+namespace+"}issuingAuthority").text = issuing_auth


def cache_to_cmdi(cmdi, cache):
    tags = ["Person", "Author", "Organisation"]
    for tag in tags:
        for entity in cmdi.xpath(f".//*[local-name()='{tag}']"):
            namespace = entity.tag.split('}')[0][1:]
            name = get_name(entity)
            
            # skip if no name/no authoritative IDs in cache
            if name not in cache:
                continue
            auth_ids = cache[name]
            if len(auth_ids) == 0:
                continue
            
            parent_auth = entity.xpath(".//*[local-name()='AuthoritativeIDs']")
            
            # create <AuthoritativeIDs> if necessary
            if len(parent_auth) == 0:
                auths_ids_tag = ET.SubElement(entity, "{"+namespace+"}AuthoritativeIDs")
            else:
                auths_ids_tag = parent_auth[0]
                
            # get IDs already in CMDI
            cur_ids = []
            for id_node in auths_ids_tag.xpath(".//*[local-name()='id']"):
                if id_node.text is not None:
                    cur_ids.append(id_node.text)
            
            add_id(auths_ids_tag, cur_ids, namespace, auth_ids)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("path_to_cache",
                        help="the path for the cache that stores the entities and their authorative IDs.", type=str)
    parser.add_argument("cmdi_files", type=str,
                        help="the path to the directory that contains all cmdi files. can be a complex hierachy.")
    args = parser.parse_args()

    cache = load_cache(args.path_to_cache)
    c = 0
    # traverse through directory structure
    for subdir, dirs, files in os.walk(args.cmdi_files):
        if files:
            for file in files:
                cmdi = read_cmdi(subdir + "/" + file)
                cache_to_cmdi(cmdi, cache)
                # create the path (mirroring the original one) and save the modified CMDI there
                new_save_path = "updated_cmdis" + "/" + subdir[len(args.cmdi_files):] + "/" + file
                os.makedirs(os.path.dirname(new_save_path), exist_ok=True)
                et = ET.ElementTree(cmdi)
                et.write(new_save_path, pretty_print=True, encoding="utf-8")
                print(new_save_path)
                c += 1
    print("CMDIs found:", c)