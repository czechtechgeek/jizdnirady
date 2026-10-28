# Home Assistant add-on

Tenhle adresář dělá z repozitáře **add-on repository** pro Home Assistant — aplikaci jde nainstalovat přímo z UI HA, bez Dockeru a bez ručního spouštění.

## Instalace

1. HA → **Nastavení → Doplňky → Obchod s doplňky**
2. Vpravo nahoře **⋮ → Repozitáře**
3. Přidat `https://github.com/czechtechgeek/jizdnirady`
4. Obchod obnovit (ikona reload) → objeví se **Jablonecké spojení**
5. **Nainstalovat** → **Spustit**

Po instalaci:

- **Postranní panel „Odjezdy“** (ingress) — aplikace i displej.
- **Přímý port 8099** — `http://homeassistant.local:8099` (pro PWA, tablet na stole, HA senzory).

## První start

Add-on při prvním spuštění stáhne GTFS z IDOLu (~84 MB) a postaví databázi — trvá to řádově minuty. Průběh je v logu add-onu. Databáze se ukládá do `/data`, takže přežije restart i aktualizaci add-onu.

## Konfigurace

`/data/commute.json` (domov, práce, alternativa, časy) — uprav přes **Terminal & SSH** add-on nebo **File editor**:

```bash
cat /addon_configs/*/commute.json   # nebo /data/commute.json v kontejneru
```

Po změně restartuj add-on.

## Aktualizace jízdních řádů

Smaž `/data/jizdnirady.db` a restartuj add-on — databáze se postaví znovu z aktuálního GTFS. `user.db` (oblíbené) zůstává.

## Poznámky

- Architektury: `aarch64`, `amd64`, `armv7`.
- Ingress cesta: aplikace si sama přepisuje absolutní cesty podle `X-Ingress-Path`.
- `addon/src/` je generované z kořene repa (`packaging/sync_addon.sh`) — needituj přímo.
