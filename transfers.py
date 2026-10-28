"""Hledání spojení s jedním přestupem (pro Jablonecké spojení)."""

MIN_TRANSFER = 3      # minuty na přestup
MAX_WAIT = 45         # max čekání na přestup
HORIZON1 = 120        # jak daleko hledat první úsek
HORIZON2 = 60         # druhý úsek může jet až 60 min po prvním


def _m(expr):
    """SQL výraz: 'HH:MM:SS' → minuty od půlnoci."""
    return (f"(CAST(substr({expr},1,2) AS INTEGER)*60 + CAST(substr({expr},4,2) AS INTEGER))")


def find_transfers(con, ids_a, ids_b, services, now_min, limit=6, dest_name=''):
    ph_a = ','.join('?' * len(ids_a))
    ph_b = ','.join('?' * len(ids_b))
    ph_s = ','.join('?' * len(services))
    a1 = "COALESCE(NULLIF(st2.arr,''), st2.dep)"
    a2 = "COALESCE(NULLIF(st1.arr,''), st1.dep)"

    sql = f'''
    WITH l1 AS (
        SELECT st1.trip_id t1, st1.stop_id x1, s.name nx, st1.dep d1, {a1} a1,
               {_m('st1.dep')} m1, {_m(a1)} am1
        FROM stop_times st1
        JOIN stop_times st2 ON st2.trip_id = st1.trip_id AND st2.seq > st1.seq
        JOIN trips tr ON tr.trip_id = st1.trip_id
        JOIN stops s ON s.stop_id = st2.stop_id
        WHERE st1.stop_id IN ({ph_a}) AND tr.service_id IN ({ph_s})
          AND {_m('st1.dep')} >= ? AND {_m('st1.dep')} <= ?
          AND st2.arr <> '' AND st2.dep <> ''
    ),
    l2 AS (
        SELECT st2.trip_id t2, st2.stop_id x2, s.name nx2, st2.dep d2, {a2} a2,
               {_m('st2.dep')} m2, {_m(a2)} am2
        FROM stop_times st2
        JOIN stop_times st1 ON st1.trip_id = st2.trip_id AND st1.seq > st2.seq
        JOIN trips tr ON tr.trip_id = st2.trip_id
        JOIN stops s ON s.stop_id = st2.stop_id
        WHERE st1.stop_id IN ({ph_b}) AND tr.service_id IN ({ph_s})
          AND {_m('st2.dep')} <= ?
          AND st1.arr <> '' AND st2.dep <> ''
    )
    SELECT l1.t1, l1.d1, l1.nx, l1.a1, l1.m1, l1.am1,
           l2.t2, l2.d2, l2.a2, l2.m2, l2.am2,
           r1.short_name line1, r1.type type1, r1.route_id rid1, tr1.headsign head1,
           r2.short_name line2, r2.type type2, r2.route_id rid2, tr2.headsign head2
    FROM l1
    JOIN l2 ON l2.nx2 = l1.nx
            AND l2.m2 >= l1.am1 + {MIN_TRANSFER}
            AND l2.m2 <= l1.am1 + {MAX_WAIT}
    JOIN trips tr1 ON tr1.trip_id = l1.t1
    JOIN routes r1 ON r1.route_id = tr1.route_id
    JOIN trips tr2 ON tr2.trip_id = l2.t2
    JOIN routes r2 ON r2.route_id = tr2.route_id
    WHERE l1.t1 <> l2.t2
      AND l1.am1 >= ?
    ORDER BY l1.m1
    LIMIT 6000
    '''
    params = (*ids_a, *services, now_min, now_min + HORIZON1,
              *ids_b, *services, now_min + HORIZON1 + HORIZON2,
              now_min)
    rows = con.execute(sql, params).fetchall()

    best = {}
    for r in rows:
        if not r['d1'] or not r['d2'] or not r['a1'] or not r['a2']:
            continue
        if r['rid1'] == r['rid2']:          # přestup na stejnou linku nemá smysl
            continue
        key = (r['t1'], r['t2'])
        if key not in best or r['m1'] < best[key]['m1']:
            best[key] = r

    out = []
    for r in best.values():
        dep, arr = r['m1'], r['am2']
        if arr < dep:            # přes půlnoc
            arr += 1440
        out.append({
            'dep_min': dep, 'arr_min': arr, 'duration': arr - dep,
            'wait': r['m2'] - r['am1'],
            'legs': [
                {'line': r['line1'], 'type': r['type1'], 'from': None, 'dep': r['d1'][:5],
                 'to': r['nx'], 'arr': r['a1'][:5], 'headsign': r['head1'] or ''},
                {'line': r['line2'], 'type': r['type2'], 'from': r['nx'], 'dep': r['d2'][:5],
                 'to': dest_name, 'arr': r['a2'][:5], 'headsign': r['head2'] or ''},
            ],
        })
    out.sort(key=lambda x: (x['arr_min'], x['dep_min']))

    seen, uniq = set(), []
    for o in out:
        k = (o['legs'][0]['line'], o['legs'][0]['dep'], o['legs'][1]['line'], o['legs'][1]['dep'])
        if k in seen:
            continue
        seen.add(k); uniq.append(o)
        if len(uniq) >= limit:
            break
    return uniq
