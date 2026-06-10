import os, json
from datetime import datetime

BASE = r'D:/WSR_History'


def current_week_folder():
    now = datetime.now()
    week = now.isocalendar().week
    path = os.path.join(BASE, str(now.year), f'Week_{week}')
    os.makedirs(path, exist_ok=True)
    return path


def save_history(report):
    path = current_week_folder()
    with open(os.path.join(path, 'summary.json'), 'w') as f:
        json.dump(report['summary'].to_dict(), f, default=str)
    with open(os.path.join(path, 'bullets.txt'), 'w', encoding='utf-8') as f:
        for b in report.get('bullets', []):
            f.write(b + '')
    return path