#!/usr/bin/env python3
"""Jablonecké spojení — nejbližší odjezdy mezi dvěma zastávkami (GTFS) + oblíbené."""
import datetime, json, os, sqlite3
from zoneinfo import ZoneInfo
from flask import Flask, jsonify, make_response, render_template, request, send_from_directory

import transfers as tr_mod

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, 'jizdnirady.db')
USER = os.path.join(BASE, 'user.db')
TZ = ZoneInfo('Europe/Prague')

app = Flask(__name__)

_ALT_CACHE = {}

TYPE = {0: 'tram', 1: 'metro', 2: 'vlak', 3: 'bus', 4: 'loď', 5: 'lanovka', 6: 'lanovka',
        7: 'funicular', 11: 'bus', 12: 'vlak'}


@app.route('/sw.js')
def service_worker():
    """Service worker musí být na kořeni, aby měl scope '/'."""
    resp = make_response(send_from_directory(os.path.join(BASE, 'static'), 'sw.js'))
    resp.headers['Content-Type'] = 'application/javascript; charset=utf-8'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@app.route('/manifest.webmanifest')
def manifest():
    return send_from_directory(os.path.join(BASE, 'static'), 'manifest.webmanifest',
                               mimetype='application/manifest+json')


@app.route('/healthz')
def healthz():
    return jsonify({'ok': True})


def db():
    con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    return con


def udb():
    con = sqlite3.connect(USER)
    con.row_factory = sqlite3.Row
    return con


def init_user():
    con = udb()
    con.executescript('''
        CREATE TABLE IF NOT EXISTS favorites(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, stop_from TEXT NOT NULL, stop_to TEXT NOT NULL,
            created TEXT NOT NULL, last_used TEXT, use_count INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS searches(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stop_from TEXT, stop_to TEXT, ts TEXT, weekday INT, hour INT, minute INT,
            fav_id INTEGER, results INT);
        CREATE INDEX IF NOT EXISTS ix_searches_ts ON searches(ts);
    ''')
    con.commit(); con.close()


init_user()


def now():
    return datetime.datetime.now(TZ)


def active_services(con, d=None):
    d = d or now().date()
    wd = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'][d.weekday()]
    ymd = d.strftime('%Y%m%d')
    ids = {r['service_id'] for r in con.execute(
        f'SELECT service_id FROM calendar WHERE {wd}=1 AND start<=? AND end>=?', (ymd, ymd))}
    for r in con.execute('SELECT service_id, exception FROM calendar_dates WHERE date=?', (ymd,)):
        if r['exception'] == 1:
            ids.add(r['service_id'])
        elif r['exception'] == 2:
            ids.discard(r['service_id'])
    return ids


def hm(t):
    h, m, _ = t.split(':')
    return int(h) * 60 + int(m)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/stops')
def api_stops():
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify([])
    con = db()
    rows = con.execute(
        "SELECT name, MIN(lat) lat, MIN(lon) lon, COUNT(*) n FROM stops WHERE name LIKE ? "
        "GROUP BY name ORDER BY CASE WHEN name LIKE 'Jablonec nad Nisou%' THEN 0 ELSE 1 END, name LIMIT 20",
        (f'%{q}%',)).fetchall()
    return jsonify([{'name': r['name'], 'lat': r['lat'], 'lon': r['lon'], 'n': r['n']} for r in rows])


@app.route('/api/next')
def api_next():
    a = (request.args.get('from') or '').strip()
    b = (request.args.get('to') or '').strip()
    if not a or not b:
        return jsonify({'error': 'Zadej obě zastávky'}), 400
    con = db()
    ids_a = [r['stop_id'] for r in con.execute('SELECT stop_id FROM stops WHERE name=?', (a,))]
    ids_b = [r['stop_id'] for r in con.execute('SELECT stop_id FROM stops WHERE name=?', (b,))]
    if not ids_a or not ids_b:
        return jsonify({'error': 'Zastávka nenalezena'}), 404

    t = now()
    cur = t.hour * 60 + t.minute
    at = (request.args.get('at') or '').strip()
    if at:
        try:
            hh, mm = at.split(':')[:2]
            cur = int(hh) * 60 + int(mm)
        except ValueError:
            pass
    svc = active_services(con, t.date())
    if not svc:
        return jsonify({'connections': [], 'note': 'Dnes neplatí žádný jízdní řád.'})
    ph_a = ','.join('?' * len(ids_a)); ph_b = ','.join('?' * len(ids_b)); ph_s = ','.join('?' * len(svc))

    sql = f'''
        SELECT st1.dep, st2.arr, r.short_name line, r.type, tr.headsign, s.name name2
        FROM stop_times st1
        JOIN stop_times st2 ON st2.trip_id = st1.trip_id AND st2.seq > st1.seq
        JOIN trips tr ON tr.trip_id = st1.trip_id
        JOIN routes r ON r.route_id = tr.route_id
        JOIN stops s ON s.stop_id = st2.stop_id
        WHERE st1.stop_id IN ({ph_a}) AND st2.stop_id IN ({ph_b})
          AND tr.service_id IN ({ph_s}) AND st1.dep >= ?
        ORDER BY st1.dep LIMIT 60
    '''
    start = f'{cur // 60:02d}:{cur % 60:02d}:00'
    rows = con.execute(sql, (*ids_a, *ids_b, *svc, start)).fetchall()

    out, seen = [], set()
    for r in rows:
        dep, arr = hm(r['dep']), hm(r['arr'])
        if dep < cur:
            continue
        key = (r['line'], r['dep'], r['arr'], r['headsign'])
        if key in seen:
            continue
        seen.add(key)
        out.append({'line': r['line'], 'type': TYPE.get(r['type'], 'bus'),
                    'dep': r['dep'][:5], 'arr': r['arr'][:5], 'in_min': dep - cur,
                    'duration': (arr - dep) if arr >= dep else (arr + 1440 - dep),
                    'headsign': r['headsign'] or '', 'to_name': r['name2']})
        if len(out) >= 12:
            break

    # když přímých spojů není dost, zkusíme jeden přestup (s cache na 5 minut)
    alt = []
    ckey = (a, b, t.strftime('%Y%m%d'), cur // 5)
    if len(out) < 3 and ckey in _ALT_CACHE:
        alt = _ALT_CACHE[ckey]
    elif len(out) < 3:
        for x in tr_mod.find_transfers(con, ids_a, ids_b, list(svc), cur, limit=4, dest_name=b):
            alt.append({
                'dep': f"{x['dep_min'] // 60:02d}:{x['dep_min'] % 60:02d}",
                'arr': f"{x['arr_min'] // 60:02d}:{x['arr_min'] % 60:02d}",
                'in_min': x['dep_min'] - cur,
                'duration': x['duration'],
                'wait': x['wait'],
                'legs': [{
                    'line': l['line'], 'type': TYPE.get(l['type'], 'bus'),
                    'dep': l['dep'], 'arr': l['arr'], 'headsign': l['headsign'],
                    'from': a if i == 0 else l['from'], 'to': l['to'],
                } for i, l in enumerate(x['legs'])],
            })
        _ALT_CACHE[ckey] = alt

    # uložíme jen skutečné hledání (ne automatickou obnovu)
    if request.args.get('log') == '1':
        u = udb()
        u.execute('INSERT INTO searches(stop_from,stop_to,ts,weekday,hour,minute,fav_id,results) '
                  'VALUES (?,?,?,?,?,?,?,?)',
                  (a, b, t.isoformat(timespec='seconds'), t.weekday(), t.hour, t.minute,
                   request.args.get('fav') or None, len(out)))
        if request.args.get('fav'):
            u.execute('UPDATE favorites SET last_used=?, use_count=use_count+1 WHERE id=?',
                      (t.isoformat(timespec='seconds'), request.args.get('fav')))
        u.commit(); u.close()

    return jsonify({'from': a, 'to': b, 'now': f'{cur // 60:02d}:{cur % 60:02d}',
                    'connections': out, 'transfers': alt,
                    'note': '' if (out or alt) else 'V nejbližších hodinách nic nejede.'})


@app.route('/api/favorites', methods=['GET', 'POST'])
def favorites():
    u = udb()
    if request.method == 'GET':
        rows = u.execute('SELECT * FROM favorites ORDER BY use_count DESC, id').fetchall()
        return jsonify([dict(r) for r in rows])
    d = request.get_json(force=True)
    name = (d.get('name') or '').strip() or f"{d.get('from', '')} → {d.get('to', '')}"
    cur = u.execute('INSERT INTO favorites(name,stop_from,stop_to,created) VALUES (?,?,?,?)',
                    (name, d['from'], d['to'], now().isoformat(timespec='seconds')))
    u.commit()
    return jsonify({'id': cur.lastrowid, 'name': name})


@app.route('/api/favorites/<int:fid>', methods=['DELETE'])
def favorite_delete(fid):
    u = udb(); u.execute('DELETE FROM favorites WHERE id=?', (fid,)); u.commit()
    return jsonify({'ok': True})


@app.route('/api/insights')
def insights():
    """Kolikrát a v kolik se z oblíbených tras jezdí — podklad pro týdenní souhrn."""
    u = udb()
    favs = [dict(r) for r in u.execute('SELECT * FROM favorites')]
    out = []
    for f in favs:
        rows = u.execute('''SELECT weekday, hour, minute FROM searches
                            WHERE fav_id=? OR (stop_from=? AND stop_to=?) ORDER BY ts''',
                         (f['id'], f['stop_from'], f['stop_to'])).fetchall()
        if not rows:
            out.append({**f, 'searches': 0}); continue
        mins = sorted(r['hour'] * 60 + r['minute'] for r in rows if r['weekday'] < 5) or \
               sorted(r['hour'] * 60 + r['minute'] for r in rows)
        med = mins[len(mins) // 2]
        by_day = {}
        for r in rows:
            by_day[r['weekday']] = by_day.get(r['weekday'], 0) + 1
        out.append({**f, 'searches': len(rows), 'median_time': f'{med // 60:02d}:{med % 60:02d}',
                    'by_weekday': by_day})
    return jsonify(out)


COMMUTE = os.path.join(BASE, 'commute.json')


def load_commute():
    try:
        with open(COMMUTE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'home': '', 'work': ''}


def _direct(a, b, cur, limit=3, day=None, max_dep=None, min_dep=None):
    """Nejbližší přímé spoje mezi dvěma zastávkami (pro display)."""
    con = db()
    ids_a = [r['stop_id'] for r in con.execute('SELECT stop_id FROM stops WHERE name=?', (a,))]
    ids_b = [r['stop_id'] for r in con.execute('SELECT stop_id FROM stops WHERE name=?', (b,))]
    if not ids_a or not ids_b:
        return []
    svc = active_services(con, day)
    if not svc:
        return []
    ph_a = ','.join('?' * len(ids_a))
    ph_b = ','.join('?' * len(ids_b))
    ph_s = ','.join('?' * len(svc))
    sql = f'''
        SELECT st1.dep, st2.arr, r.short_name line, r.type,
               st1.trip_id trip, st1.seq s1, st2.seq s2, tr.headsign
        FROM stop_times st1
        JOIN stop_times st2 ON st2.trip_id = st1.trip_id AND st2.seq > st1.seq
        JOIN trips tr ON tr.trip_id = st1.trip_id
        JOIN routes r ON r.route_id = tr.route_id
        WHERE st1.stop_id IN ({ph_a}) AND st2.stop_id IN ({ph_b})
          AND tr.service_id IN ({ph_s}) AND st1.dep >= ?
          {('AND st1.dep < ?' if max_dep else '')}
        ORDER BY st1.dep LIMIT 60
    '''
    lo = f'{cur // 60:02d}:{cur % 60:02d}:00'
    lo_full = min_dep + ':00' if (min_dep and len(min_dep) == 5) else (min_dep or '')
    if lo_full and lo_full > lo:
        lo = lo_full
    params = [*ids_a, *ids_b, *svc, lo]
    if max_dep:
        params.append(max_dep if len(max_dep) == 8 else max_dep + ':00')
    rows = con.execute(sql, params).fetchall()
    out, seen = [], set()
    for r in rows:
        dep = hm(r['dep'])
        if dep < cur:
            continue
        k = (r['line'], r['dep'], r['arr'])
        if k in seen:
            continue
        seen.add(k)
        out.append({'line': r['line'], 'type': TYPE.get(r['type'], 'bus'),
                    'dep': r['dep'][:5], 'arr': r['arr'][:5], 'in_min': dep - cur,
                    'trip': r['trip'], 's1': r['s1'], 's2': r['s2'],
                    'headsign': r['headsign'] or ''})
        if len(out) >= limit:
            break
    con.close()
    return out


@app.route('/display')
def display():
    return render_template('display.html')


def _direction(a, b, cur, tomorrow, limit=6, max_dep=None, min_dep=None, force_tomorrow=False):
    if not force_tomorrow:
        items = _direct(a, b, cur, limit=limit, max_dep=max_dep, min_dep=min_dep)
        if items:
            return {'from': a, 'to': b, 'items': items, 'tomorrow': False}
    # dnes už nic — ukaž první spoje zítra
    items = _direct(a, b, 0, limit=limit, day=tomorrow, max_dep=max_dep, min_dep=min_dep)
    for i in items:
        i['in_min'] = None
    return {'from': a, 'to': b, 'items': items, 'tomorrow': True}


@app.route('/api/trip')
def api_trip():
    """Zastávky jednoho spoje mezi nástupní a výstupní zastávkou."""
    trip = request.args.get('trip', '')
    try:
        s1 = int(request.args.get('s1', '0'))
        s2 = int(request.args.get('s2', '999999'))
    except ValueError:
        return jsonify([])
    con = db()
    rows = con.execute('''SELECT s.name, st.arr, st.dep, st.seq
                          FROM stop_times st JOIN stops s ON s.stop_id = st.stop_id
                          WHERE st.trip_id = ? AND st.seq BETWEEN ? AND ?
                          ORDER BY st.seq''', (trip, s1, s2)).fetchall()
    return jsonify([{'name': r['name'],
                     'arr': (r['arr'] or r['dep'] or '')[:5],
                     'dep': (r['dep'] or r['arr'] or '')[:5]} for r in rows])


def _morning_pick(items, arrive_by, n=6):
    """Ranní nabídka: max 1 spoj před cílovým příjezdem, cíl a pak spoje po něm."""
    if not items:
        return []
    fits = [i for i in items if i['arr'] <= arrive_by]
    if not fits:
        return items[:n]
    target = fits[-1]                      # poslední, kterým to ještě stíhá
    idx = items.index(target)
    start = max(0, idx - 1)                # jeden spoj dřív jako záloha
    return items[start:start + n]


def _typical_workday(start):
    """Nejbližší pracovní den s plným provozem (o prázdninách jezdí méně spojů)."""
    con = db()
    best, best_n = start, -1
    for k in range(15):
        d = start + datetime.timedelta(days=k)
        if d.weekday() >= 5:
            continue
        n = len(active_services(con, d))
        if n > best_n:
            best, best_n = d, n
    con.close()
    return best


def _plan(day, home, work, arrive_by, leave_before, leave_after=None):
    """Teoretický plán na pracovní den: ranní spoje s příjezdem do arrive_by,
    odpolední spoje z práce odjíždějící před leave_before."""
    con = db()
    ids_a = [r['stop_id'] for r in con.execute('SELECT stop_id FROM stops WHERE name=?', (home,))]
    ids_b = [r['stop_id'] for r in con.execute('SELECT stop_id FROM stops WHERE name=?', (work,))]
    if not ids_a or not ids_b:
        return {'morning': [], 'afternoon': [], 'date': day.isoformat()}
    svc = active_services(con, day)
    if not svc:
        return {'morning': [], 'afternoon': [], 'date': day.isoformat()}

    def q(a_ids, b_ids, lo, hi, field, reverse):
        ph_a = ','.join('?' * len(a_ids)); ph_b = ','.join('?' * len(b_ids)); ph_s = ','.join('?' * len(svc))
        cond = 'st2.arr' if field == 'arr' else 'st1.dep'
        sql = f'''
            SELECT st1.dep, st2.arr, r.short_name line, r.type, st1.trip_id trip,
                   st1.seq s1, st2.seq s2, tr.headsign
            FROM stop_times st1
            JOIN stop_times st2 ON st2.trip_id = st1.trip_id AND st2.seq > st1.seq
            JOIN trips tr ON tr.trip_id = st1.trip_id
            JOIN routes r ON r.route_id = tr.route_id
            WHERE st1.stop_id IN ({ph_a}) AND st2.stop_id IN ({ph_b})
              AND tr.service_id IN ({ph_s}) AND st1.dep >= ? AND {cond} <= ?
            ORDER BY st1.dep {'DESC' if reverse else 'ASC'} LIMIT 40
        '''
        rows = con.execute(sql, (*a_ids, *b_ids, *svc, lo, hi)).fetchall()
        out, seen = [], set()
        for r in rows:
            k = (r['line'], r['dep'], r['arr'])
            if k in seen:
                continue
            seen.add(k)
            out.append({'line': r['line'], 'type': TYPE.get(r['type'], 'bus'), 'dep': r['dep'][:5],
                        'arr': r['arr'][:5], 'trip': r['trip'], 's1': r['s1'], 's2': r['s2'],
                        'headsign': r['headsign'] or ''})
        return out

    morning = q(ids_a, ids_b, '04:30:00', '08:30:00', 'dep', False)
    if arrive_by:
        morning = _morning_pick(morning, arrive_by, 6)
        fits = [i for i in morning if i['arr'] <= arrive_by]
        best = max(fits, key=lambda i: i['dep']) if fits else None
        for i in morning:
            i['target'] = (i is best)
    else:
        morning = morning[:6]
    afternoon = q(ids_b, ids_a, f'{leave_after}:00' if leave_after else '03:30:00',
                  f'{leave_before}:00' if leave_before else '23:59:59', 'dep', True)[:4]
    afternoon.reverse()
    con.close()
    return {'morning': morning, 'afternoon': afternoon, 'date': day.isoformat()}


@app.route('/api/display')
def api_display():
    cfg = load_commute()
    t = now()
    cur = t.hour * 60 + t.minute
    tomorrow = (t + datetime.timedelta(days=1)).date()
    home, work = cfg.get('home', ''), cfg.get('work', '')
    alt = cfg.get('alt_home') or ''
    leave_before = cfg.get('leave_before') or None
    leave_after = cfg.get('leave_after') or None

    evening = cur >= 19 * 60          # po 19:00 už má smysl ukazovat zítřejší ráno
    arrive_by = cfg.get('arrive_by')
    to_work = _direction(home, work, cur, tomorrow, limit=15, force_tomorrow=evening)
    # ráno: max 1 spoj před cílem, cíl ("na 6") a pak nabídka po šesté
    if arrive_by:
        to_work['items'] = _morning_pick(to_work['items'], arrive_by, 6)
        fits = [i for i in to_work['items'] if i['arr'] <= arrive_by]
        best = max(fits, key=lambda i: i['dep']) if fits else None
        for i in to_work['items']:
            i['target'] = (i is best)

    workday = _typical_workday(t.date())

    return jsonify({
        'now': t.strftime('%H:%M'),
        'home': cfg.get('home_label', 'Doma'),
        'work': cfg.get('work_label', 'Práce'),
        'arrive_by': arrive_by,
        'leave_before': leave_before,
        'plan': _plan(workday, home, work, arrive_by, leave_before, leave_after),
        'to_work': to_work,
        'to_work_alt': _direction(alt, work, cur, tomorrow, limit=4, force_tomorrow=evening) if alt else None,
        'from_work': _direction(work, home, cur, tomorrow, limit=6, max_dep=leave_before, min_dep=leave_after),
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8099)), debug=False)
