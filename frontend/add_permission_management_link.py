import os
import re

def add_permission_management_link(file_path):
    """在用户下拉菜单中添加权限管理链接"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经有权限管理链接
        if 'href="/permission-management"' in content:
            print(f"✓ {file_path} - 已有权限管理链接")
            return
        
        # 查找用户下拉菜单
        pattern = r'(<div class="user-dropdown"[^>]*>.*?<a href="/report-generation">.*?</a>\s*)(<a href="/login" class="logout">退出登录</a>)'
        
        replacement = r'\1<a href="/permission-management">权限管理</a>\n            \2'
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✓ {file_path} - 已添加权限管理链接")
        else:
            print(f"✗ {file_path} - 未找到用户下拉菜单")
            
    except Exception as e:
        print(f"✗ {file_path} - 错误: {e}")

def main():
    frontend_dir = r'd:\区块链\视频系统\frontend'
    
    html_files = [
        'video-system.html',
        'image-inspection.html',
        'flight-search.html',
        'inspection-management.html',
        'aircraft-info.html',
        'blockchain-deposit.html',
        'blockchain-deposit-records.html',
        'blockchain-deposit-records-create.html',
        'blockchain-deposit-records-view.html',
        'blockchain-deposit-records-approve.html',
        'blockchain-deposit-audit.html',
        'blockchain-visualization.html',
        'blockchain.html',
        'device-test.html',
        'inspector-assignment.html',
        'profile.html',
        'system-settings.html',
        'system-monitor.html',
        'report-generation.html',
        'permission-management.html'
    ]
    
    print("开始添加权限管理链接到所有HTML文件...\n")
    
    for html_file in html_files:
        file_path = os.path.join(frontend_dir, html_file)
        if os.path.exists(file_path):
            add_permission_management_link(file_path)
        else:
            print(f"✗ {file_path} - 文件不存在")
    
    print("\n完成！")

if __name__ == '__main__':
    main()
