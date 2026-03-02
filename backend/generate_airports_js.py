import csv
import json
import os

def generate_static_js():
    # 路径配置
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 视频系统
    csv_path = os.path.join(os.path.dirname(base_dir), '机场信息.csv')
    # 输出到 frontend/static/airports.js
    output_path = os.path.join(base_dir, 'frontend', 'static', 'airports.js')
    
    # 确保static目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Reading from: {csv_path}")
    
    airports = []
    
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('机场名称', '').strip()
                    city = row.get('城市', '').strip()
                    province = row.get('省份/地区', '').strip()
                    code = row.get('三字码 (IATA)', '').strip()
                    
                    # 过滤逻辑：只要有代码或者是规划中但有名字的，都通过搜索
                    # 为了用户体验，过滤掉完全没有参考价值的数据
                    if name:
                        airports.append({
                            "name": name,
                            "city": city,
                            "province": province,
                            "code": code
                        })
            
            # 生成 JS 文件内容
            # 将数据赋值给 window 对象的一个属性，方便全局访问
            js_content = f"window.AIRPORT_DATA = {json.dumps(airports, ensure_ascii=False, indent=2)};"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(js_content)
                
            print(f"Successfully generated {output_path}")
            print(f"Total airports: {len(airports)}")
            
        except Exception as e:
            print(f"Error processing CSV: {e}")
    else:
        print(f"CSV file not found at {csv_path}")

if __name__ == "__main__":
    generate_static_js()
