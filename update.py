import requests
from bs4 import BeautifulSoup
import urllib.parse
import datetime
from datetime import date
import re
import os

# Število opredeljenih pri aktivnih zobozdravnikih na dan 01.11.2020
# Število opredeljenih pri aktivnih zdravnikih na dan 01.11.2020
# Število opredeljenih pri aktivnih ginekologih na dan 3.1.2021
nameRegex= r".* (zobozdravniki|zdravniki|ginekologi).* ([0-9]{1,2}\.[0-9]{1,2}\.20[0-9]{2})"

BaseURL = "https://zavarovanec.zzzs.si/wps/portal/portali/azos/ioz/ioz_izvajalci"
page = requests.get(BaseURL)
soup = BeautifulSoup(page.content, "html.parser")
ultag = soup.find("ul", class_="datoteke")

for litag in ultag.find_all('li'):
    atag=litag.find('a')
    title=atag.text
    print(title)

    match = re.match(nameRegex, title)
    if match == None:
        print(f"Unexpected title '{title}' not matching regex '{nameRegex}''.")
        raise

    date = datetime.datetime.strptime(match.group(2), '%d.%m.%Y').date()

    h=atag['href'].strip()
    url=urllib.parse.urljoin(BaseURL,h)

    r = requests.get(url, allow_redirects=True)
    r.raise_for_status()
    ct = r.headers.get('content-type')
    if ct.lower() != "application/xlsx":
        print(f"Unexpected content type '{ct}'.")
        raise

    vrsta = match.group(1).lower()
    filename = f"{date}_{vrsta}.xlsx"
    dest = os.path.join("zzzs/",filename)
    print(f"    Saving to: {dest}")

    open(dest, 'wb').write(r.content)
