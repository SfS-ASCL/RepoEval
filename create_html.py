import os

from datetime import datetime


def write_to_file(html_code, file="output/statistics.html"):
    dir = os.path.dirname(file)
    if not os.path.exists(dir):
        os.makedirs(dir)

    with open(file, 'w', encoding="utf-8") as out_f:
        out_f.write(html_code)


def _create_profile_list(profiles):
    html_list = ""
    for profile, count in profiles.items():
        html_list += f"          <li>{profile} ({count})</li>\n"
    
    return html_list


def create_statistics(stats, errors=[]):

    html_table = f"""
<!-- TABLE STATISTIK START -->
<div class="post-content">
  <table>
    <tr>
      <td>Number of files hosted</td>
      <td>{stats.get("resource_count")}</td>
    </tr>
    <tr>
      <td>Number of digital objects</td>
      <td>{stats.get("cmdi_count")}</td>
    </tr>
    <tr>
      <td>Number of persons involved</td>
      <td>{stats.get("person_count")}</td>
    </tr>
    <tr>
      <td>Number of metadata profiles</td>
      <td>{len(stats.get("profiles"))} - these are:
        <ul>
{_create_profile_list(stats.get("profiles"))}
        </ul>
      </td>
    </tr>
    <tr>
      <td>Number of (potential) erros</td>
      <td>{len(errors)}</td>
    </tr>
  </table>
  <p>Status of {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p>
</div>
<!-- TABLE STATISTIK END -->
"""
    return html_table


