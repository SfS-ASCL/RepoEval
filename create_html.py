import argparse
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests
import seaborn as sns

from datetime import datetime
from lxml import etree

class CreateStatistics :

    # returns dict with all statistics from OAI.xml
    def collect_stats(self, xml):
        ns = {'ns1': 'http://www.clarin.eu/cmd/1'}
        self.cmdi_counter = 0
        self.resource_counter = 0
        self.total_size = 0
        self.profiles = {}
        self.mimetypes = {}
        self.person_set = set()
        tree = etree.parse(xml)

        all_cmdis = tree.xpath("//*[local-name()='record']") 
        self.cmdi_counter = len(all_cmdis)

        for cmdi in all_cmdis:
            profile = cmdi.xpath(".//*[local-name()='Components']/*[1]")[0].tag.split('}')[-1]
            resources = cmdi.xpath(".//*[local-name()='ResourceProxy'][(contains(*[local-name()='ResourceType'],  'Resource'))]")
            persons = cmdi.xpath(".//*[local-name()='Person']")
            print(cmdi)
            self.resource_counter += len(resources)
            self.count_profiles(profile)            
            self.get_person(persons)

            for res_proxy in resources:
                res_proxy_list = cmdi.xpath(".//*[local-name()='ResourceProxyInfo'][@ns1:ref='" + 
                    res_proxy.attrib["id"] +"']", namespaces=ns)
                
                if len(res_proxy_list) > 0:
                    resource = res_proxy_list[0]
                    size = resource.xpath(".//*[local-name()='Size']")
                    mimetype = res_proxy.xpath(".//*[local-name()='ResourceType']/@mimetype")
                    
                    if len(size) > 0:
                        try:
                            size = int(size[0].text.strip())
                        except AttributeError:
                            size = 0
                    else:
                        size = 0
                    self.total_size += size

                    if (len(mimetype) > 0):
                        mimetype = mimetype[0].strip()
                        self.add_mimetype(mimetype, size)
            
        return {"cmdi_count": self.cmdi_counter,
                "resource_count": self.resource_counter,
                "person_count": len(self.person_set),
                "profiles": self.profiles,
                "TotalSize": self.total_size,
                "Mimetypes": self.mimetypes}


    def add_mimetype(self, mimetype, size):
        if self.mimetypes.get(mimetype) is None:
            self.mimetypes[mimetype] = {"size": 0, "count": 0}
        if size is not None:
            self.mimetypes[mimetype]["size"] += size
        self.mimetypes[mimetype]["count"] += 1

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


    def create_profile_list(self, profiles):
        html_list = "\n"
        for profile, count in profiles.items():
            html_list += f"            <li>{profile} ({count})</li>\n"
        
        return html_list[:-1]

    def create_mimetype_list(self, mimetypes):
        html_list = "\n"
        sorted_mimetypes = sorted(mimetypes.keys(), key=lambda x: mimetypes[x]["count"], reverse=True)
        #print("____________________")
        #print(sorted_mimetypes)
        for mimetype in sorted_mimetypes:
            v = mimetypes[mimetype]
            count = v["count"]
            t = "MB"
            mime_size = round(v["size"] / 1024 / 1024, 3)
            if len(str(mime_size).split('.')[0]) >= 4:
                mime_size = round(mime_size / 1021, 3)
                t = "GB"
                 
            html_list += f"            <li>{mimetype}</li>\n"
            html_list += f"              <ul><li>{count} Files</li><li>{mime_size} ({t}) Total</li></ul>\n"
            
        return html_list[:-1]
        

    # return HTML string for TALAR Statistics
    def create_statistics(self, stats, errors=[]):

        html_table = f"""
  <!-- TABLE STATISTIK START -->
  <div class="post-content">
    <table>
      <tr>
        <td>Number of files hosted</td>
        <td>{self.resource_counter}</td>
      </tr>
      <tr>
        <td>Number of digital objects</td>
        <td>{self.cmdi_counter}</td>
      </tr>
      <tr>
        <td>Number of persons involved</td>
        <td>{len(self.person_set)}</td>
      </tr>
      <tr>
        <td>Number of metadata profiles</td>
        <td>{len(self.profiles)} - these are:
          <ul> {self.create_profile_list(self.profiles)}
          </ul>
        </td>
      </tr>
      <tr>
        <td>Total size</td>
        <td>{round(self.total_size / 1024 / 1024 /1024, 3)} (GB)</td>
      </tr>
      <tr>
        <td>Mimetypes</td>
        <td>
          <ul>{self.create_mimetype_list(self.mimetypes)}
          </ul>             
        </td>
      </tr>
    </table>
    <p>Status of {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p>
  </div>
  <!-- TABLE STATISTIK END -->
  """
        return html_table
    
    def create_histogram(self, dir="output"):
        sorted_mimetypes_names = sorted(self.mimetypes.keys(), key=lambda x: self.mimetypes[x]["count"], reverse=True)
        sorted_mimetypes_names2 = sorted(self.mimetypes.keys(), key=lambda x: self.mimetypes[x]["size"], reverse=True)
        sorted_mimetypes_count = [self.mimetypes[k]["count"] for k in sorted_mimetypes_names]
        sorted_mimetypes_size = [self.mimetypes[k]["size"] for k in sorted_mimetypes_names2]
        #print(sorted_mimetypes_count)
        #exit()
        
        mime_names = [ x.split('/')[-1].split('.')[-1] for x in sorted_mimetypes_names ]
        mime_count = [x for x in sorted_mimetypes_count]
        mime_size = [int(round(x / 1024 / 1024, 4)) for x in sorted_mimetypes_size]


        plt.bar(mime_names, mime_count)
        plt.ylabel('Count')
        plt.xlabel('Mimetype')
        plt.yticks(range(0, int(max(mime_count)+1.0), 500))
        plt.xticks(rotation=45, ha="right")
        fig = plt.gcf()
        fig.set_size_inches(18.5, 10.5)
        #plt.show()
        #plt.tight_layout()
        plt.savefig(dir + "/count_plot.png", dpi=100)
        
        plt.clf()
        
        plt.bar(mime_names, mime_size)
        plt.ylabel('Size (MB)')
        plt.xlabel('Mimetype')
        plt.yticks(range(0, max(mime_size)+1, 7500))
        plt.xticks(rotation=45, ha="right")
        fig = plt.gcf()
        fig.set_size_inches(18.5, 10.5)
        plt.savefig(dir + "/size_plot.png")


    def write_to_file(self, html_code, file="output/statistics.html"):
        dir = os.path.dirname(file)
        if not os.path.exists(dir):
            os.makedirs(dir)

        with open(file, 'w', encoding="utf-8") as out_f:
            out_f.write(html_code)

if __name__ == '__main__':    
    parser = argparse.ArgumentParser(description='Create Statistics HTML Talar existing CMDIs')
    parser.add_argument("-i", "--input", help="OAI.xml")
    parser.add_argument("-o", "--output", help="Output Statistics HTML/plots directory")
    args = parser.parse_args()
    e = CreateStatistics()
    if args.input is None:
        req = requests.get("https://talar.sfb833.uni-tuebingen.de/erdora/rest/oai?verb=ListRecords&metadataPrefix=cmdi")
        with open('oai_tmp.xml', 'wb') as f:
            f.write(req.content)
        stats = e.collect_stats("oai_tmp.xml")
    
    stats = e.collect_stats(args.input)
    html_code = e.create_statistics(stats)
    print(html_code)
    e.create_histogram(args.output)
    e.write_to_file((args.output + "statistics.html"))
    
    if args.input is None:
        os.remove("oai_tmp.xml")
