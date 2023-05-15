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
from zipfile import ZipFile
from io import BytesIO
import email.utils

load_dotenv()
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
SHEET_OVERRIDES = "1gsIkUsvO-2_atHTsU9UcH2q69Js9PuvskTbtuY3eEWQ"
RANGE_OVERRIDES = "Overrides!A1:AA"

type_map = {
    'SPLOŠNA DEJAVNOST - SPLOŠNA AMBULANTA': 'gp',
    'SPLOŠNA AMB. - BOLJŠA DOSTOPNOST DO IOZ': 'gp-x',
    'SPLOŠNA AMB. ZA NEOPREDELJENE ZAV. OSEBE': 'gp-f', 
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
    for group in ["zdravniki", "zobozdravniki", "ginekologi", "za-boljšo-dostopnost", "za-neopredeljene"]:
        filename = max(glob.glob(f"zzzs/*_{group}.xlsx"))
        print(f"Source: {group} - {filename}")

        df = pd.read_excel(io=filename, sheet_name='Podatki', skiprows=9).dropna()

        if group == "za-neopredeljene":
            print("Converting za neopredeljene")
            if len(df.columns) == 8:
                print("...introduced with 2023-02-10")
                df.columns = ['unit', 'institutionID', 'name', 'address', 'city', 'typeID', 'type', 'load']
                # TODO: Use the new columns instead of dropping them:
                df.drop(columns=['institutionID', 'typeID'], inplace=True)

                # add missing columns with default values
                df['doctor'] = 'Ambulanta za neopredeljene'
                df['availability'] = None
                df['accepts'] = 'DA'
                
            else:
                print(f"Unsupported za neopredeljene source columns! count={len(df.columns)}: {df.columns}")
                raise

        else:
            print("Converting doctors list")
            if len(df.columns) == 13:
                print("...version after 2023-02-10")
                df.columns = ['unit', 'institutionID', 'name', 'address', 'city', 'doctorID', 'doctor', 'typeID', 'type', 'availability', 'load', 'mustAccept', 'accepts']
                df['doctor'] = df['doctor'].str.title()

                diff_accepts_NE_DA=df.loc[(df['mustAccept'] == 'NE') & (df['accepts'] == 'DA'), ['name', 'doctor', 'type', 'mustAccept', 'accepts']]
                if not diff_accepts_NE_DA.empty:
                    print("Doctors that accept according to ZZZS even if they don't have to:")
                    print(diff_accepts_NE_DA)

                diff_accepts_DA_NE=df.loc[(df['mustAccept'] == 'DA') & (df['accepts'] == 'NE'), ['name', 'doctor', 'type', 'mustAccept', 'accepts']]
                if not diff_accepts_DA_NE.empty:
                    print("Doctors that don't accept according to ZZZS but they should have to:")
                    print(diff_accepts_DA_NE)

                # TODO: Use the new ID columns instead of dropping them:
                df.drop(columns=['institutionID', 'doctorID', 'typeID', 'mustAccept'], inplace=True)

            elif len(df.columns) == 9:
                print("Detected early version, prior to 2023-02-10")
                df.columns = ['unit', 'name', 'address', 'city', 'doctor', 'type', 'availability', 'load', 'accepts']
                df['doctor'] = df['doctor'].str.title()
                # TODO: insert dummy new ID columns if needed.

            else:
                print(f"Unsupported za opredeljene source columns! count={len(df.columns)}: {df.columns}")
                raise


        df['doctor'] = df['doctor'].str.strip().replace('\s+', ' ', regex=True)
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
    overrides = pd.read_csv('csv/overrides.csv', index_col=['doctor','type','id_inst'], parse_dates=['date_override'])

    if not overrides.index.is_unique:
        print ("============= DUPLICATES ============")
        duplicates = overrides[overrides.index.duplicated(keep=False)]
        print (duplicates)
        exit(1)

    doctors = doctors.join(overrides)

    doctors.to_csv('csv/doctors.csv')

    used_overrides_accepts=doctors.loc[doctors['accepts_override'].notna() & (doctors['accepts'] != doctors['accepts_override']), ['accepts', 'accepts_override', 'date_override']]
    used_overrides_accepts.sort_values(by=['date_override'], inplace=True)
    print(f"Doctors with used accept override: {len(used_overrides_accepts)}")
    if not used_overrides_accepts.empty:
        with pd.option_context('display.max_rows', None,'display.max_columns', None):
            print(used_overrides_accepts.to_string())

    redundant_overrides_accepts=doctors.loc[doctors['accepts'] == doctors['accepts_override'], ['accepts', 'accepts_override', 'date_override']]
    redundant_overrides_accepts.sort_values(by=['date_override'], inplace=True)
    print(f"Doctors with redundant accept override: {len(redundant_overrides_accepts)}")
    if not redundant_overrides_accepts.empty:
        with pd.option_context('display.max_rows', None,'display.max_columns', None):
            print(redundant_overrides_accepts.to_string())

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
        subprocess.run(["geocode", "csv", "--in", "gurs/addresses-zzzs.csv", "--out", "gurs/addresses.csv", "--zipCol", "1", "--addressCol", "2", "--appendAll"])
    except FileNotFoundError:
        print("geocode not found, skipping.")

    addresses = pd.read_csv('csv/doctors.csv', usecols=['post', 'address', 'city']).rename(columns={'post':'postOver', 'address':'addressOver', 'city':'cityOver'}).dropna(subset=['postOver','addressOver'])
    addresses.sort_values(by=['postOver', 'addressOver', 'cityOver'], inplace=True)
    addresses.drop_duplicates(inplace=True)
    addresses.set_index(['postOver', 'addressOver', 'cityOver'], inplace=True)
    addresses.to_csv('gurs/addresses-overrides.csv')

    try:
        subprocess.run(["geocode", "csv", "--in", "gurs/addresses-overrides.csv", "--out", "gurs/addresses-overrides-geocoded.csv", "--zipCol", "1", "--addressCol", "2", "--cityCol", "3", "--appendAll"])
    except FileNotFoundError:
        print("geocode not found, skipping.")


def add_gurs_geodata():
    institutions = pd.read_csv('csv/institutions.csv', index_col=['id_inst'])
    dfgeo=pd.read_csv('gurs/addresses.csv', index_col=['cityZZZS','addressZZZS'], dtype=str)
    dfgeo.fillna('', inplace=True)
    dfgeo['address'] = dfgeo.apply(lambda x: f'{x.street} {x.housenumber}{x.housenumberAppendix}'.strip() if x.housenumber else x.name[1], axis = 1)
    dfgeo['post'] = dfgeo.apply(lambda x: f'{x.zipCode} {x.zipName}'.strip() if x.zipCode else x.name[0], axis = 1)
    dfgeo['municipality'] = dfgeo.apply(lambda x: x.municipality if x.municipality else '???', axis = 1)

    institutions = institutions.merge(dfgeo[['address','post','city','municipalityPart','municipality','lat','lon']], how = 'left', left_on = ['city','address'], right_index=True, suffixes=['_zzzs', ''])
    institutions.drop(['address_zzzs','city_zzzs'], axis='columns', inplace=True)
    institutions.to_csv('csv/institutions.csv')

    doctors = pd.read_csv('csv/doctors.csv', index_col=['doctor', 'type', 'id_inst'])
    dfgeo=pd.read_csv('gurs/addresses-overrides-geocoded.csv', index_col=['postOver','addressOver','cityOver'], dtype=str)
    dfgeo.fillna('', inplace=True)
    dfgeo['address'] = dfgeo.apply(lambda x: f'{x.street} {x.housenumber}{x.housenumberAppendix}'.strip() if x.housenumber else x.name[1], axis = 1)
    dfgeo['post'] = dfgeo.apply(lambda x: f'{x.zipCode} {x.zipName}'.strip() if x.zipCode else x.name[0], axis = 1)
    dfgeo['city'] = dfgeo.apply(lambda x: x.city if x.city else x.name[2], axis = 1)
    dfgeo['municipality'] = dfgeo.apply(lambda x: x.municipality if x.municipality else '???', axis = 1)

    doctors = doctors.merge(dfgeo[['address','post','city','municipalityPart','municipality','lat','lon']], how = 'left', left_on = ['post','address','city'], right_index=True, suffixes=['Over', ''])
    doctors.drop(['postOver','addressOver','cityOver'], axis='columns', inplace=True)
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
        # 'DOLINAR- KRESE HERMINA - ZASEBNA OTROŠKA IN ŠOLSKA ORDINACIJA': "8524237",
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
    # 28.03.2023, Število opredeljenih v ambulantah za neopredeljene (za osebe nad 19 let brez splošnega zdravnika)
    # 28.03.2023, Število opredeljenih v ambulantah za boljšo dostopnost (splošni zdravnik)
    # 28.03.2023, Število opredeljenih pri ginekologih
    # 28.03.2023, Število opredeljenih pri zobozdravnikih
    # 28.03.2023, Število opredeljenih pri splošnih zdravnikih (družinski, otroški oz. šolski zdravniki)
    nameRegex= r".* (zobozdravniki|zdravniki|ginekologi|za boljšo dostopnost|za neopredeljene).*"
    dateRegex= r"([0-9]{1,2}\.[0-9]{1,2}\.20[0-9]{2})"

    BaseURL = "https://zavarovanec.zzzs.si/wps/portal/portali/azos/ioz/ioz_izvajalci"
    page = requests.get(BaseURL)
    page.raise_for_status()
    soup = BeautifulSoup(page.content, "html.parser")
    ultag = soup.find("ul", class_="datoteke")

    for litag in ultag.find_all('li'):
        dateMatch=match = re.match(dateRegex, litag.text)
        atag=litag.find('a')
        title=atag.text
        print(title)

        match = re.match(nameRegex, title)
        if match == None:
            print(f"Unexpected title '{title}' not matching regex '{nameRegex}'', skipping.")
            # raise
            continue

        date = datetime.datetime.strptime(dateMatch.group(1), '%d.%m.%Y').date()
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

def download_zzzs_address_book():
    srcUrl = "http://api.zzzs.si/lokacijeOC/LokacijeZdrDelavcevOC.xlsx"
    print(f'Downloading ZZZS address book from: {srcUrl}')

    r = requests.get(srcUrl, allow_redirects=True)
    r.raise_for_status()
    ct = r.headers.get('content-type')
    if ct.lower() != "application/xlsx" and ct.lower() != "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        print(f"Unexpected content type '{ct}'.")
        raise

    # Excel: "Datum in čas priprave: 13.05.2023 16:33:37"
    # HTTP header: 'Last-Modified': 'Sat, 13 May 2023 14:33:51 GMT'
    ts=email.utils.parsedate_to_datetime(r.headers.get('Last-Modified'))
    print("    HTTP Last Modified: ", ts)
    destDirXlsx = f"zzzs/{ts.year:04}/{ts.month:02}"
    os.makedirs(destDirXlsx, mode = 0o755, exist_ok = True)

    destXlsx = f"{destDirXlsx}/{ts.year:04}-{ts.month:02}-{ts.day:02}_LokacijeZdrDelavcevOC.xlsx"
    print(f"    Saving to: {destXlsx}")
    open(destXlsx, 'wb').write(r.content)

    destCsv = "csv/address-book.csv"
    # TODO: rename columns and set proper index
    addressBook = pd.read_excel(io=destXlsx, sheet_name='Podatki', skiprows=5, index_col=None)
    print(f"    Saving to: {destCsv}")
    addressBook.to_csv(destCsv, index = False)

def download_zzzs_RIZDDZ():
    baseUrl = "https://api.zzzs.si/"
    page = requests.get(baseUrl + "ZZZS/pao/bpi.nsf/index", allow_redirects=True)
    page.raise_for_status()
    soup = BeautifulSoup(page.content, "html.parser")
    atag = soup.find_all("a", string=re.compile("bpi\.zip"))
    if len(atag) != 1:
        print("Problem finding unique link to bpi.zip")
        raise
    url = baseUrl + atag[0]['href'].strip()
    print(f'Downloading RIZDDZ zip from: {url}')
    r = requests.get(url, allow_redirects=True)
    r.raise_for_status()

    ct = r.headers.get('content-type')
    if ct.lower() != "application/x-zip":
        print(f"Unexpected content type '{ct}'.")
        raise

    cl = int(r.headers.get('content-length'))
    if cl < 300000:
        print(f"Too short content length {cl} bytes.")
        raise

    downloadedZip = ZipFile(BytesIO(r.content))
    if downloadedZip.namelist() != ['BPI.XML']:
        print(f"Unexpected files in zip: {downloadedZip.namelist()}.")
        raise

    file = downloadedZip.open('BPI.XML')
    soup = BeautifulSoup(file, 'html.parser')
    open("zzzs/rizddz.xml", 'wb').write(soup.prettify().encode())


if __name__ == "__main__":
    fname_inst = 'csv/institutions.csv'
    old_hash_inst = sha1sum(fname_inst)
    fname_doctors = 'csv/doctors.csv'
    old_hash_doctors = sha1sum(fname_doctors)

    download_zzzs_xlsx_files()
    download_zzzs_RIZDDZ()
    download_zzzs_address_book()
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
