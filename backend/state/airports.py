import csv
import os

IATA_FIELD = "\u4e09\u5b57\u7801 (IATA)"
NAME_FIELD = "\u673a\u573a\u540d\u79f0"
CITY_FIELD = "\u57ce\u5e02"
PROVINCE_FIELD = "\u7701\u4efd/\u5730\u533a"


def load_airport_data():
    try:
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(backend_dir)), "\u673a\u573a\u4fe1\u606f.csv"),
            os.path.join("D:\\BlockChain", "\u673a\u573a\u4fe1\u606f.csv"),
            "\u673a\u573a\u4fe1\u606f.csv"
        ]

        csv_path = None
        for path in possible_paths:
            if os.path.exists(path):
                csv_path = path
                break

        if not csv_path:
            print("Warning: airport info CSV not found")
            return []

        airports_list = []
        with open(csv_path, "r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                code = row.get(IATA_FIELD, "").strip()
                if code and len(code) == 3 and code.isalpha():
                    airports_list.append({
                        "name": row.get(NAME_FIELD, "").strip(),
                        "city": row.get(CITY_FIELD, "").strip(),
                        "province": row.get(PROVINCE_FIELD, "").strip(),
                        "code": code
                    })
        return airports_list
    except Exception as exc:
        print("Failed to read airport info: " + str(exc))
        return []
