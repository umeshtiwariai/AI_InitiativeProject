import os, json
from datetime import datetime

BASE = r'D:/WSR_History'


def compare_last_week(current_summary):
    now = datetime.now()
    prev_week = now.isocalendar().week - 1
    prev = os.path.join(BASE, str(now.year), f'Week_{prev_week}', 'summary.json')
    if not os.path.exists(prev):
        return ['No previous week data found.']
    with open(prev, 'r') as f:
        old = json.load(f)
    old_row = old[list(old.keys())[0]] if isinstance(old, dict) else old[0]
    cur = current_summary.to_dict(orient='records')[0]
    out = []
    for k,v in cur.items():
        try:
            delta = int(v) - int(old_row.get(k,0))
            sign = '+' if delta >= 0 else ''
            out.append(f'{k}: {sign}{delta}')
        except:
            pass
    return out or ['No comparable metrics.']