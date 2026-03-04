import urllib.request
import os

# 创建 js 目录
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
js_dir = os.path.join(repo_root, 'frontend', 'static', 'js')
os.makedirs(js_dir, exist_ok=True)

# 下载 Chart.js
chart_js_url = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'
chart_js_path = os.path.join(js_dir, 'chart.umd.min.js')

print(f"正在下载 Chart.js...")
try:
    urllib.request.urlretrieve(chart_js_url, chart_js_path)
    print(f"Chart.js 下载成功: {chart_js_path}")
except Exception as e:
    print(f"Chart.js 下载失败: {e}")

# 下载 D3.js
d3_js_url = 'https://d3js.org/d3.v7.min.js'
d3_js_path = os.path.join(js_dir, 'd3.v7.min.js')

print(f"正在下载 D3.js...")
try:
    urllib.request.urlretrieve(d3_js_url, d3_js_path)
    print(f"D3.js 下载成功: {d3_js_path}")
except Exception as e:
    print(f"D3.js 下载失败: {e}")

print("\n所有库下载完成！")
