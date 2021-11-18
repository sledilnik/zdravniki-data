# Podatki o razpoložljivosti zdravnikov

[![Doctors update](https://github.com/sledilnik/zdravniki-data/actions/workflows/update.yaml/badge.svg)](https://github.com/sledilnik/zdravniki-data/actions/workflows/update.yaml)

## How to run scripts

___
Triggeer the [update workflow](https://github.com/sledilnik/zdravniki-data/actions/workflows/update.yaml) or to run it locally run in this folder:

1. `python3 -m venv venv` or `virtualenv -p python3 venv`
1. `source venv/bin/activate`
1. `pip install -r requirements.txt`
1. `python update.py`

___

## Viri

### ZZZS

* https://zavarovanec.zzzs.si/wps/portal/portali/azos/ioz/ioz_izvajalci
* ZZZS API https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/
  * [Splošna ambulanta](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Splo%C5%A1na%20ambulanta)
  * [Otroški in šolski dispanzer](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Otro%C5%A1ki%20in%20%C5%A1olski%20dispanzer)
  * [Zobozdravstvo za odrasle](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Zobozdravstvo%20za%20odrasle)
  * [Zobozdravstvo za mladino](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Zobozdravstvo%20za%20mladino)
  * [Zobozdravstvo za študente](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Zobozdravstvo%20za%20%C5%A1tudente)
  * [Dispanzer za ženske](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Dispanzer%20za%20%C5%BEenske)
* http://api.zzzs.si/ZZZS/pao/bpi.nsf/index

### NIJZ

* https://www.nijz.si/podatki/izvajalci-zdravstvene-dejavnosti

### GURS

* [Register Prostorskih Enot (RPE)](https://podatki.gov.si/dataset/register-prostorskih-enot)

## Podatki

### Inštitucije

Struktura datoteke [dict-institutions.csv](csv/dict-institutions.csv):

| Stolpec        | Pomen                                 | Tip     | NULL?    | Vir                 | Opomba                                      |
|----------------|---------------------------------------|---------|----------|---------------------|---------------------------------------------|
| `id_inst`      | ID, PK :key:                          | int     | NOT NULL | auto increment      | se ga da zamenjati z zzzsSt iz ZZZS API-ja? |
| `name`         | Ime inštitucije                       | string  | NOT NULL | NIJZ xlsx           |                                             |
| `unit`         | ZZZS enota                            | string  | NOT NULL | NIJZ xlsx           | ni uporabljen, bo verjetno opuščen          |
| `address`      | Naslov sedeža inštitucije             | string  | NOT NULL | NIJZ xlsx, GURS RPE |                                             |
| `post`         | Pošta sedeža inštitucije              | string  | NOT NULL | NIJZ xlsx, GURS RPE | Poštna številka in naziv poštnega okoliše   |
| `city`         | Naselje sedeža inštitucije            | string  | NOT NULL | GURS RPE            |                                             |
| `municipality` | Občina sedeža inštitucije             | string  | NOT NULL | GURS RPE            | Bi šlo lahko v šifrant                      |
| `lat`          | Geografska širina sedeža inštitucije  | decimal | NOT NULL | GURS RPE            | 5 decimalk, cca 1m natančnost               |
| `lon`          | Geografska dolžina sedeža inštitucije | decimal | NOT NULL | GURS RPE            | 5 decimalk, cca 1m natančnost               |
| `phone`        | Telefon sedeža inštitucije            | string  | NULL     | ZZZS API            | Lahko jih je več, ločenih z vejicami        |
| `website`      | Spletno mesto sedeža inštitucije      | string  | NULL     | ZZZS API            | Lahko jih je več, ločenih z vejicami        |

### Zdravniki

Struktura datoteke [doctors.csv](csv/doctors.csv):

| Stolpec        | Pomen                                 | Tip     | NULL?    | Vir            | Opomba                                      |
|----------------|---------------------------------------|---------|----------|----------------|---------------------------------------------|
| `id`           | ID, PK :key:                          | int     | NOT NULL | auto increment |                                             |
| `doctor`       | Ime zdravnika                         | string  | NOT NULL | NIJZ xlsx      | ALL CAPS pretvorjen v `.title()` case       |
| `type`         | Vrsta zdravnika FK `dict-doctors.csv` | enum    | NOT NULL | NIJZ xlsx      |                                             |
| `accepts`      | Ali sprejema nove paciente (y/n)      | enum    | NOT NULL | NIJZ xlsx      |                                             |
| `availability` |                                       | decimal | NOT NULL | NIJZ xlsx      |                                             |
| `load`         |                                       | decimal | NOT NULL | NIJZ xlsx      |                                             |
| `id_inst`      | ID, FK na `dict-institutions.csv`     | int     | NOT NULL |                | se ga da zamenjati z zzzsSt iz ZZZS API-ja? |

### Šifranti

Struktura datoteke [dict-doctors.csv](csv/dict-doctors.csv):

| Stolpec          | Pomen                        | Tip    | NULL?    | Vir | Opomba |
|------------------|------------------------------|--------|----------|-----|--------|
| `id`             | ID vrste zdravnika, PK :key: | string | NOT NULL |     |        |
| `description`    | Opis vrste zdravnika (EN)    | string | NOT NULL |     |        |
| `description-sl` | Opis vrste zdravnika (SL)    | string | NOT NULL |     |        |

Struktura datoteke [dict-geodata.csv](csv/dict-geodata.csv):

Temporary, generated using:

```bash
$ geocodecsv -in csv/dict-institutions.csv -out csv/dict-institutions-geodata.csv -addressCol 3 -zipCol 4 -appendAll
$ #make the columns in csv/dict-institutions-geodata.csv unique
$ mlr --csv cut -f cityZZZS,addressZZZS,lat,lon,street,streetAlt,housenumber,housenumberAppendix,city,cityAlt,municipality,zipCode,zipName \
   then reorder -f cityZZZS,addressZZZS,lat,lon,street,streetAlt,housenumber,housenumberAppendix,city,cityAlt,municipality,zipCode,zipName \
      then uniq -f cityZZZS,addressZZZS,lat,lon,street,streetAlt,housenumber,housenumberAppendix,city,cityAlt,municipality,zipCode,zipName \
      then sort -f cityZZZS,addressZZZS,lat,lon,street,streetAlt,housenumber,housenumberAppendix,city,cityAlt,municipality,zipCode,zipName \
   csv/dict-institutions-geodata.csv > csv/dict-geodata.csv
$ rm csv/dict-institutions-geodata.csv
```

| Stolpec               | Pomen                              | Tip     | NULL?    | Vir       | Opomba                                       |
|-----------------------|------------------------------------|---------|----------|-----------|----------------------------------------------|
| `cityZZZS`            | Poštna številka in naziv, PK :key: | string  | NOT NULL | NIJZ xlsx |                                              |
| `addressZZZS`         | Ulica in hišna številka PK :key:   | string  | NOT NULL | NIJZ xlsx |                                              |
| `lat`                 | Geografska širina naslova          | decimal | NOT NULL | GURS RPE  | 5 decimalk, cca 1m natančnost                |
| `lon`                 | Geografska dolžina naslova         | decimal | NOT NULL | GURS RPE  | 5 decimalk, cca 1m natančnost                |
| `street`              | Ime ulice                          | string  | NOT NULL | GURS RPE  | Vsebuje ime naselja kjer ni uličnega sistema |
| `streetAlt`           | Ime ulice dvojezično               | string  | NULL     | GURS RPE  | Se še ne uporablja                           |
| `housenumber`         | Hišna številka                     | int     | NOT NULL | GURS RPE  |                                              |
| `housenumberAppendix` | Dodakek                            | string  | NOT NULL | GURS RPE  |                                              |
| `city`                | Ime naselja                        | string  | NOT NULL | GURS RPE  |                                              |
| `cityAlt`             | Ime naselja dvojezično             | string  | NULL     | GURS RPE  | Se še ne uporablja                           |
| `municipality`        | Ime občine                         | string  | NOT NULL | GURS RPE  |                                              |
| `zipCode`             | Poštna številka                    | string  | NOT NULL | GURS RPE  |                                              |
| `zipName`             | Naziv pošte                        | string  | NOT NULL | GURS RPE  |                                              |
