import os
import re

def add_report_generation_link(file_path):
    """在导航栏中添加报表生成链接"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经有报表生成链接
        if '报表生成' in content and 'report-generation' in content:
            print(f"  跳过（已包含报表生成链接）")
            return False
        
        # 在系统监控之后添加报表生成链接
        pattern = r'(<a href="/system-monitor"[^>]*>系统监控</a>)'
        replacement = r'\1\n                    <a href="/report-generation" class="unified-navbar-menu">报表生成</a>'
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  成功添加报表生成链接")
            return True
        else:
            print(f"  未找到匹配的导航栏结构")
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
    
    print("开始添加报表生成链接到导航栏...\n")
    
    success_count = 0
    for filename in files_to_update:
        file_path = os.path.join(frontend_dir, filename)
        if os.path.exists(file_path):
            print(f"处理文件: {filename}")
            if add_report_generation_link(file_path):
                success_count += 1
            print()
        else:
            print(f"文件不存在: {filename}\n")
    
    print(f"\n完成！成功更新 {success_count}/{len(files_to_update)} 个文件")

if __name__ == '__main__':
    main()
