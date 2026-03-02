import os
import re

def remove_navbar_links(file_path):
    """从导航栏中移除系统设置、系统监控、报表生成链接"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 移除系统设置链接
        content = re.sub(r'\s*<a href="/system-settings"[^>]*>系统设置</a>\s*\n?', '', content)
        
        # 移除系统监控链接
        content = re.sub(r'\s*<a href="/system-monitor"[^>]*>系统监控</a>\s*\n?', '', content)
        
        # 移除报表生成链接
        content = re.sub(r'\s*<a href="/report-generation"[^>]*>报表生成</a>\s*\n?', '', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  成功移除导航栏链接")
            return True
        else:
            print(f"  跳过（无需修改）")
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
    
    print("开始从导航栏移除系统设置、系统监控、报表生成链接...\n")
    
    success_count = 0
    for filename in files_to_update:
        file_path = os.path.join(frontend_dir, filename)
        if os.path.exists(file_path):
            print(f"处理文件: {filename}")
            if remove_navbar_links(file_path):
                success_count += 1
            print()
        else:
            print(f"文件不存在: {filename}\n")
    
    print(f"\n完成！成功更新 {success_count}/{len(files_to_update)} 个文件")

if __name__ == '__main__':
    main()
