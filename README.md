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

* :white_check_mark: xlsx [Seznami zdravnikov, ki so lahko osebni zdravniki](https://zavarovanec.zzzs.si/wps/portal/portali/azos/ioz/ioz_izvajalci)
* :white_check_mark: API [Izvajalci zdravstvenih storitev po dejavnosti](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/)
  * [Splošna ambulanta](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Splo%C5%A1na%20ambulanta)
  * [Otroški in šolski dispanzer](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Otro%C5%A1ki%20in%20%C5%A1olski%20dispanzer)
  * [Zobozdravstvo za odrasle](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Zobozdravstvo%20za%20odrasle)
  * [Zobozdravstvo za mladino](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Zobozdravstvo%20za%20mladino)
  * [Zobozdravstvo za študente](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Zobozdravstvo%20za%20%C5%A1tudente)
  * [Dispanzer za ženske](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Dispanzer%20za%20%C5%BEenske)
  * Saved to [zzzs/institutions-by-category.csv](zzzs/institutions-by-category.csv)
* :white_check_mark: API [Izvajalci zdravstvenih storitev](https://api.zzzs.si/covid-sledilnik)
  * Saved to [zzzs/institutions-all.csv](zzzs/institutions-all.csv)
* :white_check_mark: RIZDDZ [Register izvajalcev zdravstvene dejavnosti](http://api.zzzs.si/ZZZS/pao/bpi.nsf/index)
  * Saved to [zzzs/rizddz.xml](zzzs/rizddz.xml)

### NIJZ

* :question: Potencialno: [Izvajalci zdravstvene dejavnosti](https://www.nijz.si/podatki/izvajalci-zdravstvene-dejavnosti)

### ZZS (Zdravniška zbornica Slovenije)

* :question: Potencialno: [Javni iskalnik zdravnikov in zobozdravnikov](https://www.zdravniskazbornica.si/informacije-publikacije-in-analize/javni-iskalnik-zdravnikov-in-zobozdravnikov)
* :question: Potencialno: Register zdravnikov ([metapodatki](https://www.zdravniskazbornica.si/docs/default-source/default-document-library/register-zdravnikov.pdf))
* :question: Potencialno: Ostale [informacije javnega značaja](https://www.zdravniskazbornica.si/informacije-publikacije-in-analize/informacije-javnega-znacaja)

### GURS

* :white_check_mark: [Register Prostorskih Enot (RPE)](https://podatki.gov.si/dataset/register-prostorskih-enot)
  * Extract saved to [gurs/addresses.csv](gurs/addresses.csv)
  * Description [gurs/README.md](gurs/README.md)

## Podatki

### Inštitucije

Struktura datoteke [institutions.csv](csv/institutions.csv):

| Stolpec            | Pomen                                 | Tip     | NULL?    | Vir                 | Opomba                                      |
|--------------------|---------------------------------------|---------|----------|---------------------|---------------------------------------------|
| `id_inst`          | :key:ID, PK                           | int     | NOT NULL | ZZZS API            | zzzsSt iz ZZZS API-ja (ali nadomestek)      |
| `zzzsSt`           | ZZZS ID                               | int     | NULL     | ZZZS API            | Nekateri vnosi ga še nimajo                 |
| `name`             | Ime inštitucije                       | string  | NOT NULL | NIJZ xlsx           |                                             |
| `unit`             | ZZZS enota                            | string  | NOT NULL | NIJZ xlsx           | ni uporabljen, bo verjetno opuščen          |
| `address`          | Naslov sedeža inštitucije             | string  | NOT NULL | NIJZ xlsx, GURS RPE | Ulični naslov. Iz RPE če geocoding uspe, sicer iz xlsx |
| `post`             | Pošta sedeža inštitucije              | string  | NOT NULL | NIJZ xlsx, GURS RPE | Poštna številka in naziv poštnega okoliše. Iz RPE če geocoding uspe, sicer iz xlsx |
| `city`             | Naselje sedeža inštitucije            | string  | NOT NULL | GURS RPE            | Ime naselja, če geocoding uspe, sicer "???" |
| `municipalityPart` | Del občine sedeža inštitucije         | string  | NULL     | GURS RPE            | Mestna, vaška četrt, krajevna skupnost, če geocoding uspe |
| `municipality`     | Občina sedeža inštitucije             | string  | NULL     | GURS RPE            | Bi šlo lahko v šifrant, če geocoding uspe                 |
| `lat`              | Geografska širina sedeža inštitucije  | decimal | NULL     | GURS RPE            | 5 decimalk, cca 1m natančnost, če geocoding uspe          |
| `lon`              | Geografska dolžina sedeža inštitucije | decimal | NULL     | GURS RPE            | 5 decimalk, cca 1m natančnost, če geocoding uspe          |
| `phone`            | Telefon sedeža inštitucije            | string  | NULL     | ZZZS API            | Lahko jih je več, ločenih z vejicami        |
| `website`          | Spletno mesto sedeža inštitucije      | string  | NULL     | ZZZS API            | Lahko jih je več, ločenih z vejicami        |

### Zdravniki

Struktura datoteke [doctors.csv](csv/doctors.csv):

| Stolpec                 | Pomen                                      | Tip     | NULL?    | Vir       | Opomba                                      |
|-------------------------|--------------------------------------------|---------|----------|-----------|---------------------------------------------|
| `doctor`                | :key:Ime zdravnika                         | string  | NOT NULL | ZZZS xlsx | ALL CAPS pretvorjen v `.title()` case. Pri *Ambulantah za neopredeljene* hardcoded |
| `type`                  | :key:Vrsta zdravnika FK `dict-doctors.csv` | enum    | NOT NULL | ZZZS xlsx |                                             |
| `id_inst`               | :key:ID, FK na `institutions.csv`          | int     | NOT NULL |           | zzsSt iz ZZZS API-ja                        |
| `accepts`               | Ali sprejema nove paciente (y/n)           | enum    | NOT NULL | ZZZS xlsx |                                             |
| `availability`          | Obseg zaposlitve (delež v tej ambulanti)   | decimal | NOT NULL | ZZZS xlsx |                                             |
| `load`                  | Glavarinski količnik                       | decimal | NOT NULL | ZZZS xlsx | Preračunan na 100% obseg zaposlitve. Pri *Ambulantah za neopredeljene* število oseb |
| `date_override`         | Datum popravka preko Sporoči napako        | date    | NULL     | ReportErr |                                             |
| `note_override`         | Opomba popravka za prikaz                  | string  | NULL     | ReportErr |                                             |
| `accepts_override`      | Popravek: sprejema paciente                | enum    | NULL     | ReportErr |                                             |
| `availability_override` | Popravek: obseg zaposlitve/delež v amb.    | decimal | NULL     | ReportErr |                                             |
| `phone`                 | Telefon ambulante                          | string  | NULL     | ReportErr | Lahko jih je več, ločenih z vejicami        |
| `website`               | Spletno mesto ambulante/inštitucije        | string  | NULL     | ReportErr | Lahko jih je več, ločenih z vejicami        |
| `email`                 | E-pošta ambulante                          | string  | NULL     | ReportErr |                                             |
| `orderform`             | Spletni naslov za naročanje                | string  | NULL     | ReportErr |                                             |
| `address`               | Naslov ambulante                           | string  | NULL     | ReportErr |                                             |
| `post`                  | Pošta ambulante                            | string  | NULL     | ReportErr |                                             |
| `city`                  | Naselje ambulante                          | string  | NULL     | GURS RPE  |                                             |
| `municipalityPart`      | Del občine ambulante                       | string  | NULL     | GURS RPE  | Mestna, vaška četrt, krajevna skupnost      |
| `municipality`          | Občina ambulante                           | string  | NULL     | GURS RPE  | Bi šlo lahko v šifrant                      |
| `lat`                   | Geografska širina ambulante                | decimal | NULL     | GURS RPE  | 5 decimalk, cca 1m natančnost               |
| `lon`                   | Geografska dolžina ambulante               | decimal | NULL     | GURS RPE  | 5 decimalk, cca 1m natančnost               |

Popravki preko ReportErr se uvozijo iz [overrides.csv](csv/overrides.csv).

 
### Šifranti

Struktura datoteke [dict-doctors.csv](csv/dict-doctors.csv):

| Stolpec          | Pomen                        | Tip    | NULL?    | Vir | Opomba |
|------------------|------------------------------|--------|----------|-----|--------|
| `id`             | ID vrste zdravnika, PK :key: | string | NOT NULL |     |        |
| `description`    | Opis vrste zdravnika (EN)    | string | NOT NULL |     |        |
| `description-sl` | Opis vrste zdravnika (SL)    | string | NOT NULL |     |        |
