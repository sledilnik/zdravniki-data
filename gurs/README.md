# GURS - extract of Register of Spatial Units (Registeer Prostorskih Enot)

[Register Prostorskih Enot (RPE)](https://podatki.gov.si/dataset/register-prostorskih-enot)

Struktura datoteke [addresses.csv](addresses.csv):

| Stolpec               | Pomen                              | Tip     | NULL?    | Vir       | Opomba                                       |
|-----------------------|------------------------------------|---------|----------|-----------|----------------------------------------------|
| `cityZZZS`            | Poštna številka in naziv, PK :key: | string  | NOT NULL | NIJZ xlsx |                                              |
| `addressZZZS`         | Ulica in hišna številka PK :key:   | string  | NOT NULL | NIJZ xlsx |                                              |
| `lat`                 | Geografska širina naslova          | decimal | NOT NULL | GURS RPE  | 5 decimalk, cca 1m natančnost                |
| `lon`                 | Geografska dolžina naslova         | decimal | NOT NULL | GURS RPE  | 5 decimalk, cca 1m natančnost                |
| `street`              | Ime ulice                          | string  | NOT NULL | GURS RPE  | Vsebuje ime naselja kjer ni uličnega sistema |
| `streetAlt`           | Ime ulice dvojezično (IT/HU)       | string  | NULL     | GURS RPE  | Se (še?) ne uporablja                        |
| `housenumber`         | Hišna številka                     | int     | NOT NULL | GURS RPE  |                                              |
| `housenumberAppendix` | Dodatek k hišni številki           | string  | NOT NULL | GURS RPE  |                                              |
| `city`                | Ime naselja                        | string  | NOT NULL | GURS RPE  |                                              |
| `cityAlt`             | Ime naselja dvojezično (IT/HU)     | string  | NULL     | GURS RPE  | Se (še?) ne uporablja                        |
| `municipalityPart`    | Del občine sedeža inštitucije      | string  | NOT NULL | GURS RPE  | Ožji del občine                              |
| `municipality`        | Ime občine                         | string  | NOT NULL | GURS RPE  |                                              |
| `zipCode`             | Poštna številka                    | int     | NOT NULL | GURS RPE  |                                              |
| `zipName`             | Naziv pošte                        | string  | NOT NULL | GURS RPE  |                                              |
| `statisticalRegion`   | Ime statistične regije             | string  | NOT NULL | GURS RPE  |                                              |

It is generated from the list of ZZZS addresses in [addresses-zzzs.csv](addresses-zzzs.csv) using:

```bash
$ geocodecsv -in addresses-zzzs.csv -out addresses.csv -zipCol 1 -addressCol 2 -appendAll
Loading RPE data by GURS, dated 2021-11-26 (4 days old)...done in 925ms
Preparing data for forward geocoding...done in 211ms
2021/11/29 20:25:01 Geocoding error: no street or city "NOVI TRG" with number 999 in postal area 8000
2021/11/29 20:25:01 Geocoded 99.91% (1154/1155) addresses in 6.81717ms. 1 errors.
```
