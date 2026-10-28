#!/usr/bin/env python3
"""Souhrn dojíždění z user.db — co, kdy a jak často se hledá."""
import datetime, os, sqlite3, statistics, sys

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user.db')
DAYS = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne']


def fmt(m):
    return f'{m // 60:02d}:{m % 60:02d}'


def main():
    con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    favs = con.execute('SELECT * FROM favorites ORDER BY use_count DESC').fetchall()
    print('# Profil dojíždění\n')
    if not favs:
        print('Zatím žádné oblíbené trasy.')
        return
    for f in favs:
        rows = con.execute('''SELECT ts, weekday, hour, minute FROM searches
                              WHERE fav_id=? OR (stop_from=? AND stop_to=?)
                              ORDER BY ts''', (f['id'], f['stop_from'], f['stop_to'])).fetchall()
        print(f"## ★ {f['name']}")
        print(f"{f['stop_from']} → {f['stop_to']}")
        if not rows:
            print('Zatím žádné hledání.\n')
            continue
        work = [r for r in rows if r['weekday'] < 5] or rows
        mins = [r['hour'] * 60 + r['minute'] for r in work]
        days = {}
        for r in rows:
            days[r['weekday']] = days.get(r['weekday'], 0) + 1
        print(f"- hledání: **{len(rows)}** (poslední {rows[-1]['ts'][:16].replace('T', ' ')})")
        print(f"- typický čas hledání v pracovní dny: **{fmt(int(statistics.median(mins)))}** "
              f"(rozsah {fmt(min(mins))}–{fmt(max(mins))})")
        print('- dny: ' + ', '.join(f'{DAYS[d]} {c}×' for d, c in sorted(days.items())))
        # posledních 14 dní
        cut = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
        recent = [r for r in rows if r['ts'][:10] >= cut]
        print(f"- za 14 dní: {len(recent)}×")
        print()


if __name__ == '__main__':
    main()
