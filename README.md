# Podatki o razpoložljivosti zdravnikov

[![Doctors update](https://github.com/sledilnik/zdravniki-data/actions/workflows/update.yaml/badge.svg)](https://github.com/sledilnik/zdravniki-data/actions/workflows/update.yaml)

## How to run scripts
___
In this folder run:
1. `python3 -m venv venv` or `virtualenv -p python3 venv`
1. `source venv/bin/activate`
1. `pip install -r requirements.txt`
1. `python update.py`

## Viri

### ZZZS

* https://zavarovanec.zzzs.si/wps/portal/portali/azos/ioz/ioz_izvajalci
* https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/
  * `gp` General Practitioner,Zdravnik: Splošna ambulanta [API](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Splo%C5%A1na%20ambulanta)
  * `gp-y` General Practitioner (youth), Zdravnik (mladina): Otroški in šolski dispanzer [API](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Otro%C5%A1ki%20in%20%C5%A1olski%20dispanzer)
  * `den` Dentist,Zobozdravnik: [zob](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Zobozdravstvo%20za%20odrasle)
  * `den-y` Dentist (youth),Zobozdravnik (mladina): Zobozdravstvo za mladino: [API](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Zobozdravstvo%20za%20mladino)
  * `den-s` Dentist (students),Zobozdravnik (študenti): Zobozdravstvo za študente [API](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Zobozdravstvo%20za%20%C5%A1tudente)
  * `gyn` Gynecologist,Ginekolog: Dispanzer za ženske [API](https://www.zzzs.si/zzzs-api/izvajalci-zdravstvenih-storitev/po-dejavnosti/?ajax=1&act=get-izvajalci&type=dejavnosti&key=Dispanzer%20za%20%C5%BEenske)
* http://api.zzzs.si/ZZZS/pao/bpi.nsf/index

### NIJZ

* https://www.nijz.si/podatki/izvajalci-zdravstvene-dejavnosti

### GURS

* Register Prostorskih Enot
