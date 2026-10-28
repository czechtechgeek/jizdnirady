#!/usr/bin/env python3
"""Postaví SQLite databázi z GTFS pro Jablonec nad Nisou a okolí."""
import csv, io, os, sqlite3, sys, zipfile

ZIP = sys.argv[1] if len(sys.argv) > 1 else 'gtfs.zip'
DB = sys.argv[2] if len(sys.argv) > 2 else 'jizdnirady.db'

# Liberecký kraj + přesah (Jablonec, Liberec, Tanvald, Semily, Turnov, Harrachov)
LAT_MIN, LAT_MAX = 50.45, 51.10
LON_MIN, LON_MAX = 14.70, 15.60

def rows(z, name):
    with z.open(name) as f:
        data = io.TextIOWrapper(f, encoding='utf-8-sig', newline='')
        for r in csv.DictReader(data):
            yield r

def main():
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.executescript('''
        CREATE TABLE stops(stop_id TEXT PRIMARY KEY, name TEXT, lat REAL, lon REAL);
        CREATE TABLE routes(route_id TEXT PRIMARY KEY, short_name TEXT, long_name TEXT, type INT);
        CREATE TABLE trips(trip_id TEXT PRIMARY KEY, route_id TEXT, service_id TEXT, headsign TEXT);
        CREATE TABLE stop_times(trip_id TEXT, stop_id TEXT, seq INT, arr TEXT, dep TEXT);
        CREATE TABLE calendar(service_id TEXT, mon INT, tue INT, wed INT, thu INT, fri INT, sat INT, sun INT,
                              start TEXT, end TEXT);
        CREATE TABLE calendar_dates(service_id TEXT, date TEXT, exception INT);
    ''')
    z = zipfile.ZipFile(ZIP)

    allstops = {}
    keep = {}
    for r in rows(z, 'stops.txt'):
        try:
            lat, lon = float(r['stop_lat']), float(r['stop_lon'])
        except (ValueError, KeyError):
            lat = lon = 0.0
        allstops[r['stop_id']] = (r.get('stop_name', '').strip(), lat, lon)
        if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
            keep[r['stop_id']] = allstops[r['stop_id']]
    print('zastávek v oblasti:', len(keep), '| celkem:', len(allstops))

    c.executemany('INSERT INTO stops VALUES (?,?,?,?)',
                  [(k, v[0], v[1], v[2]) for k, v in allstops.items()])

    for r in rows(z, 'routes.txt'):
        c.execute('INSERT OR REPLACE INTO routes VALUES (?,?,?,?)',
                  (r['route_id'], r.get('route_short_name', ''), r.get('route_long_name', ''),
                   int(r.get('route_type') or 3)))

    trips = {}
    for r in rows(z, 'trips.txt'):
        trips[r['trip_id']] = (r['route_id'], r['service_id'], r.get('trip_headsign', ''))

    # stop_times – jen zastávky v oblasti, ale celé spoje
    tids = set()
    batch = []
    for r in rows(z, 'stop_times.txt'):
        sid = r['stop_id']
        if sid not in keep:
            continue
        batch.append((r['trip_id'], sid, int(r['stop_sequence']),
                      r.get('arrival_time', ''), r.get('departure_time', '')))
        tids.add(r['trip_id'])
        if len(batch) >= 200000:
            c.executemany('INSERT INTO stop_times VALUES (?,?,?,?,?)', batch)
            batch.clear()
    if batch:
        c.executemany('INSERT INTO stop_times VALUES (?,?,?,?,?)', batch)
    print('spojů v oblasti:', len(tids), '| záznamů stop_times:', c.execute('SELECT COUNT(*) FROM stop_times').fetchone()[0])

    # doplníme všechny zastávky spojů, které oblastí projíždějí (aby šlo jet dál)
    have = set(tids)
    for r in rows(z, 'stop_times.txt'):
        if r['trip_id'] in have and r['stop_id'] not in keep:
            batch.append((r['trip_id'], r['stop_id'], int(r['stop_sequence']),
                          r.get('arrival_time', ''), r.get('departure_time', '')))
            if len(batch) >= 200000:
                c.executemany('INSERT INTO stop_times VALUES (?,?,?,?,?)', batch); batch.clear()
    if batch:
        c.executemany('INSERT INTO stop_times VALUES (?,?,?,?,?)', batch)
    print('stop_times celkem:', c.execute('SELECT COUNT(*) FROM stop_times').fetchone()[0])

    # trips jen pro spoje, které máme
    c.executemany('INSERT OR REPLACE INTO trips VALUES (?,?,?,?)',
                  [(t, *trips[t]) for t in have if t in trips])

    for r in rows(z, 'calendar.txt'):
        c.execute('INSERT INTO calendar VALUES (?,?,?,?,?,?,?,?,?,?)',
                  (r['service_id'], *[int(r[d]) for d in
                   ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')],
                   r['start_date'], r['end_date']))
    if 'calendar_dates.txt' in z.namelist():
        c.executemany('INSERT INTO calendar_dates VALUES (?,?,?)',
                      [(r['service_id'], r['date'], int(r['exception_type'])) for r in rows(z, 'calendar_dates.txt')])

    c.executescript('''
        CREATE INDEX ix_st_stop ON stop_times(stop_id, dep);
        CREATE INDEX ix_st_trip ON stop_times(trip_id, seq);
        CREATE INDEX ix_trips ON trips(service_id);
        CREATE INDEX ix_trips_route ON trips(route_id);
        CREATE INDEX ix_stops_name ON stops(name);
    ''')
    con.commit(); con.close()
    print('hotovo:', DB, round(os.path.getsize(DB)/1e6, 1), 'MB')

if __name__ == '__main__':
    main()
