# Jablonecké spojení

Odjezdy z jabloneckých zastávek nad daty GTFS — hledání spojení, oblíbené trasy, přestupy, plán dojíždění a displej na stůl.

![Displej](docs/display.png)

## Co to umí

- **Hledání spojení** mezi dvěma zastávkami s našeptávačem (všechny zastávky IDOL, Liberecký kraj a navazující linky).
- **Přestupy** — pokud nejede přímý spoj, zkusí jedno přestupové spojení (min. 3 minuty na přestup, max. 45 minut čekání). Výsledky se cachují na 5 minut.
- **Oblíbené trasy** a **historie hledání** v samostatné `user.db` — přežije přestavbu jízdních řádů.
- **Displej** (`/display`) pro tablet nebo malý monitor: dva režimy, velké časy, klik na spoj rozbalí všechny zastávky.
  - **TEĎ** — co jede právě teď (včetně alternativy z jiné zastávky).
  - **PLÁN** — typický pracovní den: ráno „na 6“ a odpoledne „před 15:00“.
- **PWA** — jde nainstalovat na plochu PC, tabletu i telefonu, funguje offline (shell se cachuje, data vždy ze sítě).
- **Home Assistant** — hotový balíček s REST senzory a automatizací, viz [`homeassistant/`](homeassistant/).

## Rychlý start

```bash
git clone https://github.com/czechtechgeek/jizdnirady.git
cd jizdnirady

python3 -m pip install --user -r requirements.txt

# stáhne GTFS (~84 MB) a postaví jizdnirady.db (~60 MB)
./packaging/fetch_gtfs.sh

python3 app.py          # http://localhost:8099
```

Jako službu (systemd --user):

```bash
./packaging/install.sh 8099
```

## Konfigurace dojíždění

`commute.json` řídí displej:

```json
{
  "home": "Jablonec nad Nisou, Podhorská Vikýř",
  "work": "Jablonec nad Nisou, Lukášov, Cihelná",
  "alt_home": "Jablonec nad Nisou, autobusové nádraží",
  "arrive_by": "06:05",
  "leave_before": "15:00",
  "leave_after": "12:00",
  "home_label": "Doma",
  "work_label": "Práce"
}
```

- `arrive_by` — nejpozdější přijatelný příjezd do práce; spoj, který ho splní, dostane na displeji štítek **„na 6“**.
- `leave_before` / `leave_after` — okno, ve kterém se zobrazují spoje z práce.
- `alt_home` — záložní zastávka (např. když dojdete pěšky na autobusové nádraží).
- Ranní nabídka ukazuje **maximálně jeden spoj před cílovým příjezdem** a zbytek po něm.

## HTTP API

| Endpoint | Popis |
|---|---|
| `GET /api/stops?q=` | našeptávač zastávek |
| `GET /api/next?from=&to=&at=HH:MM` | nejbližší spoje (přímé i s jedním přestupem) |
| `GET /api/trip?trip=&s1=&s2=` | zastávky jednoho spoje mezi nástupem a výstupem |
| `GET /api/display` | data pro displej (oba směry, plán, minuty do odjezdu) |
| `GET /api/favorites` · `POST` · `DELETE` | oblíbené trasy |
| `GET /api/insights` | souhrn dojíždění z historie |
| `GET /healthz` | healthcheck |

Příklad:

```bash
curl 'http://localhost:8099/api/next?from=Jablonec%20nad%20Nisou,%20Brandl&to=Liberec,%20F%C3%BCgnerova'
```

## Home Assistant

Viz [`homeassistant/README.md`](homeassistant/README.md) — balíček vytvoří senzory `sensor.spojeni_do_prace`, `sensor.spojeni_z_prace`, `sensor.spojeni_dalsi_odjezd` a automatizaci na připomenutí odjezdu. Displej lze vložit i jako `panel_iframe`.

## Struktura

```
app.py                 Flask aplikace a API
transfers.py           hledání spojení s jedním přestupem
build_db.py            stavba SQLite databáze z GTFS
report.py              souhrn dojíždění (pro cron)
commute.json           konfigurace displeje
templates/index.html   hledání spojení
templates/display.html displej na stůl
static/sw.js, manifest PWA
homeassistant/         balíček a karta pro HA
packaging/             systemd unit, instalace, stažení GTFS
```

## Data

- GTFS: [IDOL / SPOJENKA](https://www.spojenka.cz/jrdata/jizdnirady-gtfs.zip) — jízdní řády Libereckého kraje.
- `jizdnirady.db` se generuje lokálně, v repu není.
- `user.db` (oblíbené a historie) zůstává mimo git.

## Omezení

- Jen přímé spoje a maximálně jeden přestup.
- Jízdní řády jsou plánované, ne real-time — zpoždění se nezobrazují.
- Data se aktualizují ručně (`packaging/fetch_gtfs.sh`); jízdní řády se mění několikrát ročně.

## Licence

MIT — viz [LICENSE](LICENSE).
