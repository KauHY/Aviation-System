import os
import re

def update_user_dropdown(file_path):
    """更新用户下拉菜单，添加系统设置、系统监控、报表生成"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 查找用户下拉菜单部分
        pattern = r'(<div class="user-dropdown" id="userDropdown">\s*<a href="/profile">查看个人信息</a>)'
        
        # 检查是否已经包含系统设置等链接
        if '系统设置' in content and 'userDropdown' in content:
            # 检查是否在下拉菜单中
            dropdown_pattern = r'<div class="user-dropdown" id="userDropdown">.*?</div>'
            dropdown_match = re.search(dropdown_pattern, content, re.DOTALL)
            if dropdown_match and '系统设置' in dropdown_match.group(0):
                print(f"  跳过（已包含系统设置等链接）")
                return False
        
        # 在"查看个人信息"后添加系统设置、系统监控、报表生成
        replacement = r'\1\n                    <a href="/system-settings">系统设置</a>\n                    <a href="/system-monitor">系统监控</a>\n                    <a href="/report-generation">报表生成</a>'
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  成功更新用户下拉菜单")
            return True
        else:
            print(f"  未找到匹配的下拉菜单结构")
            return False
            
    except Exception as e:
        print(f"  错误: {e}")
        return False

def main():
    """主函数"""
    frontend_dir = r'd:\区块链\视频系统\frontend'
    
    # 需要更新的HTML文件列表
    files_to_update = [
        'video-system.html',
        'image-inspection.html',
        'flight-search.html',
        'inspection-management.html',
        'blockchain-deposit.html',
        'blockchain-deposit-records-approve.html',
        'blockchain-deposit-records-create.html',
        'blockchain-deposit-records-view.html',
        'blockchain-visualization.html',
        'aircraft-info.html',
        'profile.html',
        'inspector-assignment.html'
    ]
    
    print("开始更新用户下拉菜单...\n")
    
    success_count = 0
    for filename in files_to_update:
        file_path = os.path.join(frontend_dir, filename)
        if os.path.exists(file_path):
            print(f"处理文件: {filename}")
            if update_user_dropdown(file_path):
                success_count += 1
            print()
        else:
            print(f"文件不存在: {filename}\n")
    
    print(f"\n完成！成功更新 {success_count}/{len(files_to_update)} 个文件")

if __name__ == '__main__':
    main()
