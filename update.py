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
import hashlib,time
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
SHEET_OVERRIDES = "1gsIkUsvO-2_atHTsU9UcH2q69Js9PuvskTbtuY3eEWQ"
RANGE_OVERRIDES = "Overrides!A1:AA"

type_map = {
    'SPLOŠNA DEJAVNOST - SPLOŠNA AMBULANTA': 'gp',
    'SPLOŠNA AMB. - BOLJŠA DOSTOPNOST DO IOZ': 'gp-x',
    'SPLOŠNA DEJ.-OTROŠKI IN ŠOLSKI DISPANZER': 'ped',
    'OTR. ŠOL. DISP.-BOLJŠA DOSTOPNOST DO IOZ': 'ped-x',
    'ZOBOZDR. DEJAVNOST-ZDRAVLJENJE ODRASLIH': 'den',
    'ZOBOZDR. DEJAVNOST-ZDRAVLJENJE MLADINE': 'den-y',
    'ZOBOZDR. DEJAVNOST-ZDRAVLJENJE ŠTUDENTOV': 'den-s',
    'SPLOŠNA DEJAVNOST - DISPANZER ZA ŽENSKE': 'gyn'
}

accepts_map = {
    'DA': 'y',
    'NE': 'n'
}

def sha1sum(fname):
    h = hashlib.sha1()
    try:
        with open(fname, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return None

def write_timestamp_file(filename: str, old_hash: str):
    if old_hash != sha1sum(filename):
        with open(f'{filename}.timestamp', 'w', newline='') as f:
            f.write(f'{int(time.time())}\n')


def convert_to_csv(zzzsid_map):
    doctors = []
    for group in ["zdravniki", "zobozdravniki", "ginekologi", "za-boljšo-dostopnost"]:
        filename = max(glob.glob(f"zzzs/*_{group}.xlsx"))
        print(f"Source: {group} - {filename}")

        df = pd.read_excel(io=filename, sheet_name='Podatki', skiprows=9).dropna()
        df.columns = ['unit', 'institutionID', 'name', 'address', 'city', 'doctorID', 'doctor', 'typeID', 'type', 'availability', 'load', 'accepts', 'agreesToAcceptOver']

        # TODO: Use the new columns instead of dropping them:
        df.drop(columns=['institutionID', 'doctorID', 'typeID', 'agreesToAcceptOver'], inplace=True)

        df['doctor'] = df['doctor'].str.strip().replace('\s+', ' ', regex=True)
        df['doctor'] = df['doctor'].str.title()
        df['type'] = df['type'].str.strip().map(type_map)
        df['accepts'] = df['accepts'].str.strip().map(accepts_map)
        df['name'] = df['name'].str.strip()
        df['address'] = df['address'].str.strip()
        df['city'] = df['city'].str.strip()
        df['unit'] = df['unit'].str.strip()
        df['zzzsid'] = df['name'].map(zzzsid_map)
        df = df.reindex(['doctor', 'type', 'zzzsid', 'accepts', 'availability', 'load', 'name', 'address', 'city', 'unit'], axis='columns')
        doctors.append(df)

    doctors = pd.concat(doctors, ignore_index=True)

    institutions = doctors.groupby(['zzzsid', 'name','address','city', 'unit'])['doctor'].apply(list).reset_index()
    institutions.drop("doctor", axis='columns', inplace=True)

    institutions.set_index('zzzsid', inplace=True)
    institutions.index.rename('id_inst', inplace=True)
    institutions.sort_values(by=['name','unit'], inplace=True)
    institutions.to_csv('csv/institutions.csv')

    doctors.drop(['name', 'address', 'city', 'unit'], axis='columns', inplace=True)
    doctors.rename(columns={'zzzsid': 'id_inst'}, inplace=True)
    doctors.sort_values(by=[*doctors], inplace=True) # sort by all columns

    # reindex:
    doctors.set_index(['doctor','type','id_inst'], inplace=True)
    doctors.to_csv('csv/doctors.csv')

    doctors.query('id_inst != id_inst').to_csv('csv/doctors-without-institution.csv')

def append_overrides():
    filename = "csv/overrides.csv"
    print(f"Get overrides from GSheet to {filename}")
    try:
        sheet2csv.sheet2csv(id=SHEET_OVERRIDES, range=RANGE_OVERRIDES, api_key=GOOGLE_API_KEY, filename=filename)
    except Exception as e:
        print("Failed to import {}".format(filename))
        raise e

    doctors = pd.read_csv('csv/doctors.csv', index_col=['doctor','type','id_inst'])
    overrides = pd.read_csv('csv/overrides.csv', index_col=['doctor','type','id_inst'])

    if not overrides.index.is_unique:
        print ("============= DUPLICATES ============")
        duplicates = overrides[overrides.index.duplicated(keep=False)]
        print (duplicates)
        exit(1)

    doctors = doctors.join(overrides)

    doctors.to_csv('csv/doctors.csv')

    overrides.count().to_csv('csv/stats-overrides.csv')
    overrides.groupby(['date_override']).count().to_csv('csv/stats-overrides-by-day.csv')
    overrides.groupby(['note_override','accepts_override'])['accepts_override'].count().to_csv('csv/stats-overrides-accepts.csv')


def geocode_addresses():
    xlsxAddresses = pd.read_csv('csv/institutions.csv', usecols=['city','address']).rename(columns={'city':'cityZZZS','address':'addressZZZS'})
    apiAddresses = pd.read_csv('zzzs/institutions-all.csv', usecols=['posta','naslov']).rename(columns={'posta':'cityZZZS','naslov':'addressZZZS'})
    addresses = pd.concat([xlsxAddresses, apiAddresses], ignore_index=True)

    addresses['cityZZZS'] = addresses['cityZZZS'].str.upper()
    addresses['addressZZZS'] = addresses['addressZZZS'].str.upper()
    addresses.sort_values(by=['cityZZZS','addressZZZS'], inplace=True)
    addresses.drop_duplicates(inplace=True)
    addresses.set_index(['cityZZZS','addressZZZS'], inplace=True)

    addresses.to_csv('gurs/addresses-zzzs.csv')

    try:
        subprocess.run(["geocode", "-in", "gurs/addresses-zzzs.csv", "-out", "gurs/addresses.csv", "-zipCol", "1", "-addressCol", "2", "-appendAll"])
    except FileNotFoundError:
        print("geocode not found, skipping.")

    addresses = pd.read_csv('csv/doctors.csv', usecols=['post', 'address']).rename(columns={'post':'postOver','address':'addressOver'}).dropna()
    addresses.sort_values(by=['postOver', 'addressOver'], inplace=True)
    addresses.drop_duplicates(inplace=True)
    addresses.set_index(['postOver', 'addressOver'], inplace=True)
    addresses.to_csv('gurs/addresses-overrides.csv')

    try:
        subprocess.run(["geocode", "-in", "gurs/addresses-overrides.csv", "-out", "gurs/addresses-overrides-geocoded.csv", "-zipCol", "1", "-addressCol", "2", "-appendAll"])
    except FileNotFoundError:
        print("geocode not found, skipping.")


def add_gurs_geodata():
    institutions = pd.read_csv('csv/institutions.csv', index_col=['id_inst'])
    dfgeo=pd.read_csv('gurs/addresses.csv', index_col=['cityZZZS','addressZZZS'], dtype=str)
    dfgeo.fillna('', inplace=True)
    dfgeo['address'] = dfgeo.apply(lambda x: f'{x.street} {x.housenumber}{x.housenumberAppendix}', axis = 1)
    dfgeo['post'] = dfgeo.apply(lambda x: f'{x.zipCode} {x.zipName}', axis = 1)

    institutions = institutions.merge(dfgeo[['address','post','city','municipalityPart','municipality','lat','lon']], how = 'left', left_on = ['city','address'], right_index=True, suffixes=['_zzzs', ''])
    institutions.drop(['address_zzzs','city_zzzs'], axis='columns', inplace=True)
    institutions.to_csv('csv/institutions.csv')

    doctors = pd.read_csv('csv/doctors.csv', index_col=['doctor', 'type', 'id_inst'])
    dfgeo=pd.read_csv('gurs/addresses-overrides-geocoded.csv', index_col=['postOver','addressOver'], dtype=str)
    dfgeo.fillna('', inplace=True)
    dfgeo['address'] = dfgeo.apply(lambda x: f'{x.street} {x.housenumber}{x.housenumberAppendix}', axis = 1)
    dfgeo['post'] = dfgeo.apply(lambda x: f'{x.zipCode} {x.zipName}', axis = 1)

    doctors = doctors.merge(dfgeo[['address','post','city','municipalityPart','municipality','lat','lon']], how = 'left', left_on = ['post','address'], right_index=True, suffixes=['Over', ''])
    doctors.drop(['addressOver','postOver'], axis='columns', inplace=True)
    doctors.to_csv('csv/doctors.csv')


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

def get_zzzs_id_map():
    df = pd.read_csv('zzzs/institutions-by-category.csv', index_col=['naziv'])

    # create lookup dictionary for ZZZS ID
    zzzsid_map = df.reset_index()[['zzzsSt', 'naziv']].set_index('naziv').to_dict()['zzzsSt']

    missing_zzzsid = {
        # renamed, needed temporary until new .xlsx arepublished with same new names:
        # 'ZDRAVSTVENI DOM TRBOVLJE TRBOVLJE, RUDARSKA CESTA 12': "102320", # was renamed
        # 'MDENT, ZOBOZDRAVSTVENE STORITVE, MIHAJLO FRANGOV S.P.': "7155880",
        'DOLINAR- KRESE HERMINA - ZASEBNA OTROŠKA IN ŠOLSKA ORDINACIJA': "8524237",
        #'ZASEBNI ŠOLSKI DISPANZER JELKA HOSTNIK, DR. MED., SPEC. ŠOL. MED.': "", # TODO

        # larger, split providers
        'OSNOVNO ZDRAVSTVO GORENJSKE, OE ZDRAVSTVENI DOM BLED, ZDRAVSTVENI DOM BOHINJ': 'ozgbb',
        'OSNOVNO ZDRAVSTVO GORENJSKE, OE ZDRAVSTVENI DOM JESENICE': 'ozgje',
        'OSNOVNO ZDRAVSTVO GORENJSKE, OE ZDRAVSTVENI DOM KRANJ': 'ozgkr',
        'OSNOVNO ZDRAVSTVO GORENJSKE, OE ZDRAVSTVENI DOM RADOVLJICA': 'ozgra',
        'OSNOVNO ZDRAVSTVO GORENJSKE, OE ZDRAVSTVENI DOM TRŽIČ': 'ozgtr',
        'OSNOVNO ZDRAVSTVO GORENJSKE, OE ZDRAVSTVENI DOM ŠKOFJA LOKA': 'ozgsl',
        'ZD LJUBLJANA - BEŽIGRAD': 'zdlbe',
        'ZD LJUBLJANA - CENTER': 'zdlce',
        'ZD LJUBLJANA - MOSTE - POLJE': 'zdlmp',
        'ZD LJUBLJANA - VIČ - RUDNIK': 'zdlvr',
        'ZD LJUBLJANA - ŠENTVID': 'zdlse',
        'ZD LJUBLJANA - ŠIŠKA': 'zdlsi',
    }
    for key, value in dict(missing_zzzsid).items():
        if not key in zzzsid_map:
            zzzsid_map[key] = value

    return zzzsid_map


def add_zzzs_api_data():
    # apiInstitutions = pd.read_csv('zzzs/institutions-all.csv', index_col=['naziv'])
    apiInstitutions = pd.read_csv('zzzs/institutions-by-category.csv', index_col=['naziv'])
    apiInstitutions['zzzsSt'] = apiInstitutions['zzzsSt'].astype(int).astype(str)

    institutions = pd.read_csv('csv/institutions.csv', index_col=['id_inst'])
    institutions = institutions.merge(apiInstitutions[['zzzsSt','tel','splStran']], how = 'left', left_on = ['name'], right_index=True, suffixes=['', '_api'])
    institutions.index.rename('id_inst', inplace=True)
    institutions.rename(columns={"tel": "phone", "splStran": "website"}, inplace=True)
    colZzzsSt = institutions.pop("zzzsSt")
    institutions.insert(0, colZzzsSt.name, colZzzsSt)

    institutions.to_csv('csv/institutions.csv')


def download_zzzs_xlsx_files():
    # Število opredeljenih pri aktivnih zobozdravnikih na dan 01.11.2020
    # Število opredeljenih pri aktivnih zdravnikih na dan 01.11.2020
    # Število opredeljenih pri aktivnih ginekologih na dan 3.1.2021
    nameRegex= r".* (zobozdravniki|zdravniki|ginekologi|za boljšo dostopnost).* ([0-9]{1,2}\.[0-9]{1,2}\.20[0-9]{2})"

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
            print(f"Unexpected title '{title}' not matching regex '{nameRegex}'', skipping.")
            # raise
            continue

        date = datetime.datetime.strptime(match.group(2), '%d.%m.%Y').date()
        group = match.group(1).lower().replace(' ', '-')
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
    fname_inst = 'csv/institutions.csv'
    old_hash_inst = sha1sum(fname_inst)
    fname_doctors = 'csv/doctors.csv'
    old_hash_doctors = sha1sum(fname_doctors)

    download_zzzs_xlsx_files()
    get_zzzs_api_data_all()
    get_zzzs_api_data_by_category()
    zzzsid_map = get_zzzs_id_map()
    convert_to_csv(zzzsid_map)
    append_overrides()
    geocode_addresses()
    add_gurs_geodata()
    add_zzzs_api_data()

    write_timestamp_file(fname_inst, old_hash_inst)
    write_timestamp_file(fname_doctors, old_hash_doctors)
