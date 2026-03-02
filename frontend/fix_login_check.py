import os
import re

def fix_login_check(file_path):
    """修复登录检查函数，避免与unified-header.js冲突"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 查找并移除checkLogin函数中的DOM操作部分
        # 只保留未登录重定向逻辑
        pattern = r'(function checkLogin\(\) \{[^}]*if \(!currentUser\) \{[^}]*window\.location\.href = \'/login\';[^}]*\}[^}]*\})'
        
        def replace_checkLogin(match):
            # 保留未登录检查，移除DOM操作
            return '''function checkLogin() {
            const currentUser = localStorage.getItem('currentUser');
            
            if (!currentUser) {
                // 未登录，重定向到登录页面
                window.location.href = '/login';
            }
        }'''
        
        new_content = re.sub(pattern, replace_checkLogin, content, flags=re.DOTALL)
        
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  成功修复登录检查函数")
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
    
    # 需要修复的HTML文件列表
    files_to_update = [
        'video-system.html',
        'inspection-management.html'
    ]
    
    print("开始修复登录检查函数...\n")
    
    success_count = 0
    for filename in files_to_update:
        file_path = os.path.join(frontend_dir, filename)
        if os.path.exists(file_path):
            print(f"处理文件: {filename}")
            if fix_login_check(file_path):
                success_count += 1
            print()
        else:
            print(f"文件不存在: {filename}\n")
    
    print(f"\n完成！成功修复 {success_count}/{len(files_to_update)} 个文件")

if __name__ == '__main__':
    main()
