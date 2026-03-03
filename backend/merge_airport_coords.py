import csv
import json
import os


def load_csv_coords(csv_path):
    coords = {}
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get('三字码 (IATA)') or row.get('IATA') or row.get('code')
            if not code:
                continue
            code = code.strip().upper()
            lat = row.get('纬度') or row.get('lat') or row.get('latitude')
            lon = row.get('经度') or row.get('lon') or row.get('longitude')
            try:
                latv = float(lat) if lat not in (None, '') else None
                lonv = float(lon) if lon not in (None, '') else None
            except ValueError:
                latv = None
                lonv = None
            if latv is not None and lonv is not None:
                coords[code] = (latv, lonv)
    return coords


def merge_coords(json_path, csv_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    coords = load_csv_coords(csv_path)

    updated = 0
    for item in data:
        code = (item.get('code') or '').strip().upper()
        if not code:
            continue
        if code in coords:
            lat, lon = coords[code]
            # Only update if missing or different
            if item.get('lat') != lat or item.get('lon') != lon:
                item['lat'] = lat
                item['lon'] = lon
                updated += 1

    # write back
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Merged coords for {updated} airports into {json_path}")


if __name__ == '__main__':
    base = os.path.abspath(os.path.dirname(__file__) + os.sep + '..')
    csv_path = os.path.join(base, '297个机场经纬度汇总.csv')
    json_path = os.path.join(base, 'backend', 'airports.json')

    if not os.path.exists(csv_path):
        csv_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '297个机场经纬度汇总.csv'))

    if not os.path.exists(csv_path):
        print('CSV file not found:', csv_path)
    else:
        merge_coords(json_path, csv_path)
