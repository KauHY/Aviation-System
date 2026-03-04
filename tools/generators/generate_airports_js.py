import csv
import json
import os

def generate_static_js():
    # 路径配置
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    csv_path = os.path.join(os.path.dirname(base_dir), '机场信息.csv')
    json_path = os.path.join(base_dir, 'backend', 'airports.json')
    # 输出到 frontend/static/airports.js
    output_path = os.path.join(base_dir, 'frontend', 'static', 'airports.js')
    
    # 确保static目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    airports = []
    
    if os.path.exists(csv_path):
        print(f"Reading from CSV: {csv_path}")
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('机场名称', '').strip()
                    city = row.get('城市', '').strip()
                    province = row.get('省份/地区', '').strip()
                    code = row.get('三字码 (IATA)', '').strip()
                    
                    if name:
                        entry = {
                            "name": name,
                            "city": city,
                            "province": province,
                            "code": code
                        }
                        lat = row.get('纬度') or row.get('lat') or row.get('latitude')
                        lon = row.get('经度') or row.get('lon') or row.get('longitude')
                        if lat and lon:
                            try:
                                entry['lat'] = float(lat)
                                entry['lon'] = float(lon)
                            except ValueError:
                                pass
                        airports.append(entry)
        except Exception as e:
            print(f"Error processing CSV: {e}")
    elif os.path.exists(json_path):
        print(f"CSV not found, loading from JSON: {json_path}")
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                airports = json.load(f)
        except Exception as e:
            print(f"Error loading JSON: {e}")
    else:
        print(f"Neither CSV nor JSON airport data available.")

    # 生成 JS 文件内容，如果有数据
    if airports:
        js_content = f"window.AIRPORT_DATA = {json.dumps(airports, ensure_ascii=False, indent=2)};"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(js_content)
        print(f"Successfully generated {output_path}")
        print(f"Total airports: {len(airports)}")
    else:
        print("No airport entries generated; empty list.")

if __name__ == "__main__":
    generate_static_js()
