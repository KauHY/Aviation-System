import csv
import json
import os

def convert_csv_to_json():
    csv_path = r'd:\BlockChain\机场信息.csv'
    json_path = r'd:\BlockChain\视频系统\backend\airports.json'
    
    airports = []
    
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 去除可能的空白字符
            name = row.get('机场名称', '').strip()
            city = row.get('城市', '').strip()
            province = row.get('省份/地区', '').strip()
            code = row.get('三字码 (IATA)', '').strip()
            
            # 过滤掉没有代码的或者规划中的机场，除非用户需要，但通常航班系统只需要运营中的
            # 这里先全部保留，但重点是代码存在的情况
            if code and '待定' not in code and '规划' not in code:
               airports.append({
                   "name": name,
                   "city": city,
                   "province": province,
                   "code": code
               })
            
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(airports, f, ensure_ascii=False, indent=4)
        print(f"Successfully converted {len(airports)} airports to {json_path}")

if __name__ == "__main__":
    convert_csv_to_json()
