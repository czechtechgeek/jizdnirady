# Home Assistant

Dvě cesty, jak spojení dostat do HA — můžeš použít obě.

## 1. Senzory (REST)

Soubor [`packages/odjezdy.yaml`](packages/odjezdy.yaml) vytvoří:

| Entita | Význam |
|---|---|
| `sensor.spojeni_do_prace` | nejbližší spoj domov → práce (`05:37 → 05:55`), atributy `items` (celý seznam), `tomorrow` |
| `sensor.spojeni_z_prace` | nejbližší spoj práce → domov |
| `sensor.spojeni_rano_plan` | plán ranních spojů na typický pracovní den |
| `sensor.spojeni_odpoledne_plan` | plán odpoledních spojů před 15:00 |
| `sensor.spojeni_dalsi_odjezd` | minuty do odjezdu |
| `sensor.spojeni_stav` | hotový text pro notifikaci/dashboard |

Instalace:

1. Zkopíruj `packages/odjezdy.yaml` do `/config/packages/`.
2. V `configuration.yaml`:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

3. V `secrets.yaml`:

   ```yaml
   jizdnirady_url: "http://192.168.88.37:8099"
   ```

4. Restart HA.

Automatizace „připomenutí odjezdu“ je součástí balíčku — pošle notifikaci, když je do odjezdu 15 minut a méně (mezi 4:00 a 9:00).

## 2. Panel s displejem

Displej jde vložit jako iframe do postranního panelu:

```yaml
panel_iframe:
  odjezdy:
    title: Odjezdy
    url: http://192.168.88.37:8099/display
    icon: mdi:bus-clock
```

Nebo na dashboard jako kartu:

```yaml
type: iframe
url: http://192.168.88.37:8099/display
aspect_ratio: 16:9
```

## 3. Karta na dashboard

Soubor [`lovelace-card.yaml`](lovelace-card.yaml) obsahuje Markdown kartu, která vypisuje nejbližší spoje z atributů senzorů — hodí se na mobil i na nástěnný tablet.

## Poznámky

- `scan_interval: 60` — data se obnovují každou minutu, stejně jako displej.
- Senzory jsou read-only; oblíbené trasy se spravují v aplikaci, ne v HA.
- Pokud HA běží na jiném stroji než aplikace, nahraď IP adresu v `secrets.yaml`.
