import csv
import json
import os

def generate_airlines_js():
    # 路径配置
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 视频系统
    csv_path = os.path.join(os.path.dirname(base_dir), '航司信息.csv')
    # 输出到 frontend/static/airlines.js
    output_path = os.path.join(base_dir, 'frontend', 'static', 'airlines.js')
    
    # 确保static目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Reading from: {csv_path}")
    
    airlines = []
    
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name_cn = row.get('公司中文全称', '').strip()
                    name_en = row.get('公司英文简称', '').strip()
                    iata = row.get('IATA代码', '').strip()
                    icao = row.get('ICAO代码', '').strip()
                    
                    # 过滤逻辑：只要有IATA代码和中文名
                    if name_cn and iata:
                        airlines.append({
                            "name_cn": name_cn,
                            "name_en": name_en,
                            "iata": iata,
                            "icao": icao
                        })
            
            # 生成 JS 文件内容
            # 将数据赋值给 window 对象的一个属性，方便全局访问
            js_content = f"window.AIRLINE_DATA = {json.dumps(airlines, ensure_ascii=False, indent=2)};"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(js_content)
                
            print(f"Successfully generated {output_path}")
            print(f"Total airlines: {len(airlines)}")
            
        except Exception as e:
            print(f"Error processing CSV: {e}")
    else:
        print(f"CSV file not found at {csv_path}")

if __name__ == "__main__":
    generate_airlines_js()
