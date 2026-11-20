import argparse
import glob
import os

import pandas as pd

TYPE_MAP = {
    'SPLOŠNA DEJAVNOST - SPLOŠNA AMBULANTA': 'gp',
    'Splošna dejavnost - splošna ambulanta': 'gp',
    'Amb. specializanta družinske medicine': 'gp',
    'SPLOŠNA AMBULANTA - DODATNA AMBULANTA': 'gp-f',
    'SPLOŠNA AMB. ZA NEOPREDELJENE ZAV. OSEBE': 'gp-f',
    'SPLOŠNA DEJ.-OTROŠKI IN ŠOLSKI DISPANZER': 'ped',
    'Splošna dej.-otroški in šolski dispanzer': 'ped',
    'OTR. ŠOL. DISP.-BOLJŠA DOSTOPNOST DO IOZ': 'ped-x',
    'ZOBOZDR. DEJAVNOST-ZDRAVLJENJE ODRASLIH': 'den',
    'ZOBOZDR. DEJAVNOST-ZDRAVLJENJE MLADINE': 'den-y',
    'ZOBOZDR. DEJAVNOST-ZDRAVLJENJE ŠTUDENTOV': 'den-s',
    'SPLOŠNA DEJAVNOST - DISPANZER ZA ŽENSKE': 'gyn'
}

ACCEPTS_MAP = {
    'DA': 'y',
    'NE': 'n',
    'Y': 'y',
    'N': 'n',
    'y': 'y',
    'n': 'n',
}

TARGET_LOAD_BY_TYPE = {
    'gp': 1895.0,
    'ped': 1895.0,
    'gp-f': 5000.0,
    'gp-x': 5000.0,
    'gyn': 100.0,
    'den': 100.0,
    'den-y': 100.0,
    'den-s': 100.0,
}

HISTORICAL_GROUPS = (
    "zdravniki",
    "zobozdravniki",
    "ginekologi",
    "za-boljšo-dostopnost",
    "za-neopredeljene",
    "v-dodatnih-ambulantah",
)


def parse_snapshot_file(path: str, group: str) -> pd.DataFrame:
    filename = os.path.basename(path)
    source_date = pd.to_datetime(filename.split('_', 1)[0]).date()

    workbook = pd.ExcelFile(path)

    if group == 'zdravniki':
        if 'Splošna dejavnost' in workbook.sheet_names:
            sheet_name = 'Splošna dejavnost'
            skip_rows = 3
        elif 'Podatki' in workbook.sheet_names:
            sheet_name = 'Podatki'
            skip_rows = 9
        else:
            sheet_name = workbook.sheet_names[0]
            skip_rows = 9
    else:
        sheet_name = 'Podatki' if 'Podatki' in workbook.sheet_names else workbook.sheet_names[0]
        skip_rows = 9

    df = pd.read_excel(io=path, sheet_name=sheet_name, skiprows=skip_rows).dropna(how='all')

    if group in ('za-neopredeljene', 'v-dodatnih-ambulantah'):
        if len(df.columns) != 8:
            raise ValueError(f"Unsupported {group} source columns in {path}: {len(df.columns)}")
        df.columns = ['unit', 'institutionID', 'name', 'address', 'city', 'typeID', 'type', 'load']
        df['doctor'] = 'Dodatna ambulanta'
        df['availability'] = 1.0
        df['accepts'] = 'DA'

    elif group == 'za-boljšo-dostopnost':
        if len(df.columns) == 13:
            df.columns = ['unit', 'institutionID', 'name', 'address', 'city', 'doctorID', 'doctor', 'typeID', 'type', 'availability', 'load', 'accepts', 'acceptsOver']
            df.drop(columns=['institutionID', 'doctorID', 'typeID', 'acceptsOver'], inplace=True)
        elif len(df.columns) == 9:
            df.columns = ['unit', 'name', 'address', 'city', 'doctor', 'type', 'availability', 'load', 'accepts']
        else:
            raise ValueError(f"Unsupported {group} source columns in {path}: {len(df.columns)}")

    else:
        if 'Zdravnik še sprejema zavarovane osebe' in df.columns and 'Zdravnik še sprejema zavarovane osebe, saj ne dosega dogovorjenega števila glavarinskih količnikov na tim (obseg zaposlitve)' in df.columns:
            df.drop(columns=['Zdravnik še sprejema zavarovane osebe'], inplace=True)
        if 'Zdravnik še sprejema zavarovane osebe' in df.columns and 'Zdravnik je dolžan sprejemati zavarovane osebe, saj ne dosega dogovorjenega števila glavarinskih količnikov na tim (obseg zaposlitve)' in df.columns:
            df.drop(columns=['Zdravnik je dolžan sprejemati zavarovane osebe, saj ne dosega dogovorjenega števila glavarinskih količnikov na tim (obseg zaposlitve)'], inplace=True)
        for column in list(df.columns):
            if isinstance(column, str) and column.startswith('Zdravnik soglaša s sprejemom zavarovane osebe'):
                df.drop(columns=[column], inplace=True)

        for removable_column in (
            'Specializant',
            'Zdravnik mora  glede na št. opredeljenih oseb (stolpec M) sprejeti novorojenčke in dojenčke (otroci do enega leta)',
            'Število opredeljenih oseb  preračunano na 1 tim zaposlitve',
            'Zdravnik ima v ambulanto družinske medicine vključene dodatne 0,5 diplomirane medicinske sestre in je dolžan sprejemati zavarovane osebe, saj ne dosega dogovorjenega dodatnega števila 300 glavarinskih količnikov na tim (obseg zaposlitve)',
        ):
            if removable_column in df.columns:
                df.drop(columns=[removable_column], inplace=True)

        if len(df.columns) == 12:
            if 'Obseg zaposlitve' in str(df.columns[9]):
                df.columns = ['unit', 'institutionID', 'name', 'address', 'city', 'doctorID', 'doctor', 'typeID', 'type', 'availability', 'load', 'accepts']
            else:
                df.columns = ['unit', 'institutionID', 'name', 'address', 'city', 'doctorID', 'doctor', 'typeID', 'type', 'accepts', 'availability', 'load']
            df.drop(columns=['institutionID', 'doctorID', 'typeID'], inplace=True)
        elif len(df.columns) == 9:
            df.columns = ['unit', 'name', 'address', 'city', 'doctor', 'type', 'availability', 'load', 'accepts']
        else:
            raise ValueError(f"Unsupported {group} source columns in {path}: {len(df.columns)}")

    df = df.dropna(subset=[c for c in df.columns if c != 'availability'])
    df['type'] = df['type'].astype(str).str.strip().map(TYPE_MAP)
    df['accepts'] = df['accepts'].astype(str).str.strip().map(ACCEPTS_MAP)
    df['address'] = df['address'].astype(str).str.strip()
    df['city'] = df['city'].astype(str).str.strip()

    df = df[df['type'].notna()]
    df = df[df['accepts'].notna()]

    df['availability'] = pd.to_numeric(df['availability'], errors='coerce').fillna(1.0)
    df['load'] = pd.to_numeric(df['load'], errors='coerce')
    df = df[df['load'].notna()]

    df['target_load'] = df['type'].map(TARGET_LOAD_BY_TYPE).fillna(100.0)
    df['free_capitation'] = (df['target_load'] - df['load']).clip(lower=0) * df['availability']
    df.loc[df['accepts'] != 'y', 'free_capitation'] = 0.0
    df['date'] = source_date

    return df[['date', 'type', 'city', 'address', 'free_capitation']]


def build_free_capitation_time_series(max_files: int | None = None):
    file_map = []
    for group in HISTORICAL_GROUPS:
        for path in sorted(glob.glob(f"zzzs/*/*/*_{group}.xlsx")):
            if os.path.basename(path).startswith('~$'):
                continue
            file_map.append((group, path))

    if max_files is not None:
        file_map = file_map[:max_files]

    rows = []
    for group, path in file_map:
        rows.append(parse_snapshot_file(path, group))

    doctors = pd.concat(rows, ignore_index=True)

    geocoded = pd.read_csv('gurs/addresses.csv', usecols=['postZZZS', 'addressZZZS', 'municipality'])
    geocoded['postZZZS'] = geocoded['postZZZS'].astype(str).str.upper().str.strip()
    geocoded['addressZZZS'] = geocoded['addressZZZS'].astype(str).str.upper().str.strip()
    geocoded = geocoded.drop_duplicates(subset=['postZZZS', 'addressZZZS']).set_index(['postZZZS', 'addressZZZS'])

    doctors['postZZZS'] = doctors['city'].astype(str).str.upper().str.strip()
    doctors['addressZZZS'] = doctors['address'].astype(str).str.upper().str.strip()
    doctors = doctors.join(geocoded[['municipality']], on=['postZZZS', 'addressZZZS'])
    doctors['municipality'] = doctors['municipality'].fillna('???')

    time_series = (
        doctors.groupby(['date', 'type', 'municipality'], as_index=False)['free_capitation']
        .sum()
        .sort_values(by=['date', 'type', 'municipality'])
    )
    time_series['free_capitation'] = time_series['free_capitation'].round(2)
    time_series.to_csv('csv/free-capitation-timeseries.csv', index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-files', type=int, default=None)
    args = parser.parse_args()
    build_free_capitation_time_series(max_files=args.max_files)
