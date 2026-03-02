import os
import re

def remove_duplicate_scripts(file_path):
    """移除重复的 unified-header.js 脚本标签"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 查找连续重复的脚本标签
        pattern = r'(<script src="/static/unified-header\.js"></script>\s*){2,}'
        
        # 替换为单个脚本标签
        replacement = r'<script src="/static/unified-header.js"></script>\n'
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  成功移除重复脚本")
            return True
        else:
            print(f"  跳过（无重复脚本）")
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
    
    print("开始移除重复脚本标签...\n")
    
    success_count = 0
    for filename in files_to_update:
        file_path = os.path.join(frontend_dir, filename)
        if os.path.exists(file_path):
            print(f"处理文件: {filename}")
            if remove_duplicate_scripts(file_path):
                success_count += 1
            print()
        else:
            print(f"文件不存在: {filename}\n")
    
    print(f"\n完成！成功更新 {success_count}/{len(files_to_update)} 个文件")

if __name__ == '__main__':
    main()
