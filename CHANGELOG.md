# Changelog

## 1.0.1 — 2026-10-28

### Opraveno
- Navigace mezi hledáním a displejem: v aplikaci je odkaz **„Displej odjezdů →“**, na displeji **„hledat“** (v HA ingressu se cesty přepisují správně).

## 1.0.0 — 2026-10-28

První veřejné vydání.

### Přidáno
- Hledání spojení mezi dvěma zastávkami (GTFS IDOL), našeptávač, oblíbené trasy a historie hledání.
- Spojení s jedním přestupem (min. 3 minuty, max. 45 minut čekání) s cache na 5 minut.
- Displej `/display` pro tablet: režimy **TEĎ** a **PLÁN**, velké časy, detail zastávek po kliknutí, ranní nabídka „na 6“ s maximálně jedním spojem před cílem.
- Alternativní zastávka (`alt_home`) pro cestu přes autobusové nádraží.
- PWA: manifest, service worker, ikony, wake lock a celoobrazovkový režim.
- Home Assistant add-on (`addon/`, `repository.yaml`) s ingress a přímým portem 8099.
- Home Assistant balíček se senzory a automatizací (`homeassistant/`).
- Instalační skripty a systemd unit (`packaging/`).
- HTTP API `/api/stops`, `/api/next`, `/api/trip`, `/api/display`, `/api/favorites`, `/api/insights`, `/healthz`.
