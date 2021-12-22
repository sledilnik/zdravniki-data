import requests
from bs4 import BeautifulSoup
import urllib.parse
import datetime
from datetime import date
import re
import os
import glob
import pandas as pd
import subprocess
import sheet2csv

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
SHEET_OVERRIDES = "1gsIkUsvO-2_atHTsU9UcH2q69Js9PuvskTbtuY3eEWQ"
RANGE_OVERRIDES = "Overrides!A1:AA"

type_map = {
    'SPLOŠNA DEJAVNOST - SPLOŠNA AMBULANTA': 'gp',
    'SPLOŠNA DEJ.-OTROŠKI IN ŠOLSKI DISPANZER': 'ped',
    'ZOBOZDR. DEJAVNOST-ZDRAVLJENJE ODRASLIH': 'den',
    'ZOBOZDR. DEJAVNOST-ZDRAVLJENJE MLADINE': 'den-y',
    'ZOBOZDR. DEJAVNOST-ZDRAVLJENJE ŠTUDENTOV': 'den-s',
    'SPLOŠNA DEJAVNOST - DISPANZER ZA ŽENSKE': 'gyn'
}

accepts_map = {
    'DA': 'y',
    'NE': 'n'
}

def get_overrides():
    filename = "csv/overrides.csv"
    print(f"Get overrides from GSheet to {filename}")
    try:
        sheet2csv.sheet2csv(id=SHEET_OVERRIDES, range=RANGE_OVERRIDES, api_key=GOOGLE_API_KEY, filename=filename)
    except Exception as e:
        print("Failed to import {}".format(filename))
        raise e


def convert_to_csv():
    doctors = []
    for group in ["zdravniki", "zobozdravniki", "ginekologi"]:
        filename = max(glob.glob(f"zzzs/*_{group}.xlsx"))
        print(f"Source: {group} - {filename}")

        df = pd.read_excel(io=filename, sheet_name='Podatki', skiprows=9).dropna()
        df.columns = ['unit', 'name', 'address', 'city', 'doctor', 'type', 'availability', 'load', 'accepts']
        df['doctor'] = df['doctor'].str.strip().replace('\s+', ' ', regex=True)
        df['doctor'] = df['doctor'].str.title()
        df['type'] = df['type'].str.strip().map(type_map)
        df['accepts'] = df['accepts'].str.strip().map(accepts_map)
        df['name'] = df['name'].str.strip()
        df['address'] = df['address'].str.strip()
        df['city'] = df['city'].str.strip()
        df['unit'] = df['unit'].str.strip()
        df = df.reindex(['doctor', 'type', 'accepts', 'availability', 'load', 'name', 'address', 'city', 'unit'], axis='columns')
        doctors.append(df)

    doctors = pd.concat(doctors, ignore_index=True)

    institutions = doctors.groupby(['name','address','city', 'unit'])['doctor'].apply(list).reset_index()
    institutions.drop("doctor", axis='columns', inplace=True)

    institutions.index.rename('id_inst', inplace=True)
    institutions.to_csv('csv/dict-institutions.csv')

    doctors.drop(['address', 'city', 'unit'], axis='columns', inplace=True)
    institutions.drop(['address', 'city', 'unit'], axis='columns', inplace=True)
    institutions = institutions.reset_index().set_index('name')
    doctors = doctors.join(institutions, on='name')
    doctors.drop('name', axis='columns', inplace=True)

    doctors.sort_values(by=[*doctors], inplace=True) # sort by all columns

    # reindex:
    doctors.set_index(['doctor','type','id_inst'], inplace=True)

    doctors.to_csv('csv/doctors.csv')

def geocode_addresses():
    xlsxAddresses = pd.read_csv('csv/dict-institutions.csv', usecols=['city','address']).rename(columns={'city':'cityZZZS','address':'addressZZZS'})
    apiAddresses = pd.read_csv('zzzs/institutions-all.csv', usecols=['posta','naslov']).rename(columns={'posta':'cityZZZS','naslov':'addressZZZS'})
    addresses = pd.concat([xlsxAddresses, apiAddresses], ignore_index=True)

    addresses['cityZZZS'] = addresses['cityZZZS'].str.upper()
    addresses['addressZZZS'] = addresses['addressZZZS'].str.upper()
    addresses.sort_values(by=['cityZZZS','addressZZZS'], inplace=True)
    addresses.drop_duplicates(inplace=True)
    addresses.set_index(['cityZZZS','addressZZZS'], inplace=True) 

    addresses.to_csv('gurs/addresses-zzzs.csv')

    try:
        subprocess.run(["geocodecsv", "-in", "gurs/addresses-zzzs.csv", "-out", "gurs/addresses.csv", "-zipCol", "1", "-addressCol", "2", "-appendAll"])
    except FileNotFoundError:
        print("geocodecsv not found, skipping.")


def add_gurs_geodata():
    institutions = pd.read_csv('csv/dict-institutions.csv', index_col=['id_inst'])
    dfgeo=pd.read_csv('gurs/addresses.csv', index_col=['cityZZZS','addressZZZS'], dtype=str)
    dfgeo.fillna('', inplace=True)
    dfgeo['address'] = dfgeo.apply(lambda x: f'{x.street} {x.housenumber}{x.housenumberAppendix}', axis = 1)
    dfgeo['post'] = dfgeo.apply(lambda x: f'{x.zipCode} {x.zipName}', axis = 1)

    institutions = institutions.merge(dfgeo[['address','post','city','municipalityPart','municipality','lat','lon']], how = 'left', left_on = ['city','address'], right_index=True, suffixes=['_zzzs', ''])
    institutions.drop(['address_zzzs','city_zzzs'], axis='columns', inplace=True)

    institutions.to_csv('csv/dict-institutions.csv')


def get_zzzs_api_data_all():
    # https://api.zzzs.si/covid-sledilnik/0 ... 1600 by pages (of 100 records)
    apiInstitutions = []
    idx = 0
    maxIdx = 1
    while idx < maxIdx:
        print(f"Fetching page from ZZZS API at index: {idx}")
        apiUrl = f"https://api.zzzs.si/covid-sledilnik/{idx}"
        r = requests.get(apiUrl)
        r.raise_for_status()
        j = r.json()
        df = pd.DataFrame.from_dict(j)

        df.drop(['@entryid'], axis='columns', inplace=True)
        df.set_index('zzzsSt', inplace=True)

        apiInstitutions.append(df)

        contentRangeHeader = r.headers['Content-Range']
        contentRangeNumbers = re.findall(r'\d+', contentRangeHeader)
        idx = int(contentRangeNumbers[1])+1
        maxIdx = int(contentRangeNumbers[2])

    df = pd.concat(apiInstitutions).drop_duplicates()
    df.sort_values(by=[*df], inplace=True) # sort by all columns
    df.to_csv('zzzs/institutions-all.csv')

def get_zzzs_api_data_by_category():
    # keys for ZZZS API calls, add as needed, see https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/
    zzzsApiKeys=[
        'Splošna ambulanta',
        'Otroški in šolski dispanzer',
        'Zobozdravstvo za odrasle',
        'Zobozdravstvo za mladino',
        'Zobozdravstvo za študente',
        'Dispanzer za ženske'
    ]

    apiInstitutions = []
    for key in zzzsApiKeys:
        print(f"Fetching from ZZZS API: {key}")
        apiUrl = f"https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key={key}"
        r = requests.get(apiUrl)
        r.raise_for_status()
        j = r.json()
        df = pd.DataFrame.from_dict(j)

        df.drop(['@entryid'], axis='columns', inplace=True)
        df.set_index('zzzsSt', inplace=True)

        apiInstitutions.append(df)

    df = pd.concat(apiInstitutions).drop_duplicates()
    df.sort_values(by=[*df], inplace=True) # sort by all columns
    df.to_csv('zzzs/institutions-by-category.csv')

def add_zzzs_api_data():
    # apiInstitutions = pd.read_csv('zzzs/institutions-all.csv', index_col=['naziv'])
    apiInstitutions = pd.read_csv('zzzs/institutions-by-category.csv', index_col=['naziv'])
    apiInstitutions['zzzsSt'] = apiInstitutions['zzzsSt'].astype(int).astype(str)
    print(apiInstitutions)

    institutions = pd.read_csv('csv/dict-institutions.csv', index_col=['id_inst'])
    institutions = institutions.merge(apiInstitutions[['zzzsSt','tel','splStran']], how = 'left', left_on = ['name'], right_index=True, suffixes=['', '_api'])
    institutions.index.rename('id_inst', inplace=True)
    institutions.rename(columns={"tel": "phone", "splStran": "website"}, inplace=True)
    colZzzsSt = institutions.pop("zzzsSt")
    institutions.insert(0, colZzzsSt.name, colZzzsSt)

    print(institutions)
    institutions.to_csv('csv/dict-institutions.csv')


def download_zzzs_xlsx_files():
    # Število opredeljenih pri aktivnih zobozdravnikih na dan 01.11.2020
    # Število opredeljenih pri aktivnih zdravnikih na dan 01.11.2020
    # Število opredeljenih pri aktivnih ginekologih na dan 3.1.2021
    nameRegex= r".* (zobozdravniki|zdravniki|ginekologi).* ([0-9]{1,2}\.[0-9]{1,2}\.20[0-9]{2})"

    BaseURL = "https://zavarovanec.zzzs.si/wps/portal/portali/azos/ioz/ioz_izvajalci"
    page = requests.get(BaseURL)
    page.raise_for_status()
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
        group = match.group(1).lower()
        filename = f"{date}_{group}.xlsx"
        dest = os.path.join("zzzs/",filename)

        if os.path.exists(dest):
            print(f"    Already downloaded: {dest}")
        else:
            h=atag['href'].strip()
            url=urllib.parse.urljoin(BaseURL,h)

            r = requests.get(url, allow_redirects=True)
            r.raise_for_status()
            ct = r.headers.get('content-type')
            if ct.lower() != "application/xlsx":
                print(f"Unexpected content type '{ct}'.")
                raise

            print(f"    Saving to: {dest}")

            open(dest, 'wb').write(r.content)


if __name__ == "__main__":
    get_overrides()
    download_zzzs_xlsx_files()
    get_zzzs_api_data_by_category()
    get_zzzs_api_data_all()
    convert_to_csv()
    geocode_addresses()
    add_gurs_geodata()
    add_zzzs_api_data()
