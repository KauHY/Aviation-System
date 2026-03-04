// 统一导航栏功能
function initUnifiedHeader() {
    function ensureFavicon() {
        const faviconHref = '/static/logo.svg';
        let icon = document.querySelector('link[rel="icon"]');
        if (!icon) {
            icon = document.createElement('link');
            icon.setAttribute('rel', 'icon');
            icon.setAttribute('type', 'image/svg+xml');
            document.head.appendChild(icon);
        }
        icon.setAttribute('href', faviconHref);
    }

    ensureFavicon();

    // Force redirect to login when not authenticated.
    function enforceLogin() {
        const currentPath = window.location.pathname;
        const allowPaths = new Set(['/login']);
        const currentUser = localStorage.getItem('currentUser');
        const accessToken = localStorage.getItem('access_token');

        if (!allowPaths.has(currentPath) && !currentUser && !accessToken) {
            window.location.href = '/login';
            return false;
        }

        return true;
    }

    if (!enforceLogin()) {
        return;
    }

    // 更新用户信息
    function updateUserInfo() {
        const username = localStorage.getItem('currentUser');
        const role = localStorage.getItem('currentUserRole');
        
        if (username) {
            const userNameEl = document.getElementById('user-name');
            const userAvatarEl = document.getElementById('user-avatar');
            const userRoleEl = document.getElementById('user-role');
            
            if (userNameEl) userNameEl.textContent = username;
            if (userAvatarEl) userAvatarEl.textContent = username.charAt(0).toUpperCase();
            
            if (userRoleEl) {
                const roleMap = {
                    'admin': '总负责人',
                    'manager': '管理人员',
                    'technician': '技术人员',
                    'user': '用户'
                };
                userRoleEl.textContent = roleMap[role] || role;
            }
        }
    }
    
    // 设置当前页面激活状态
    function setActivePage() {
        const currentPath = window.location.pathname;
        const links = document.querySelectorAll('.unified-navbar-menu a');
        
        links.forEach(link => {
            link.classList.remove('active');
            const href = link.getAttribute('href');
            if (href === currentPath || 
                (currentPath.startsWith(href) && currentPath !== '/') ||
                (currentPath === '/blockchain-deposit/records' && href === '/blockchain-deposit') ||
                (currentPath === '/blockchain-deposit/audit' && href === '/blockchain-deposit')) {
                link.classList.add('active');
            }
        });
    }
    
    // 根据权限更新用户下拉菜单
    function updateDropdownByPermissions() {
        const role = localStorage.getItem('currentUserRole');
        
        // 系统设置 - 只有管理员可以访问
        const systemSettingsLink = document.querySelector('#userDropdown a[href="/system-settings"]');
        if (systemSettingsLink) {
            systemSettingsLink.style.display = (role === 'admin') ? 'flex' : 'none';
        }
        
        // 系统监控 - 管理员和管理人员可以访问
        const systemMonitorLink = document.querySelector('#userDropdown a[href="/system-monitor"]');
        if (systemMonitorLink) {
            systemMonitorLink.style.display = (role === 'admin' || role === 'manager') ? 'flex' : 'none';
        }
        
        // 报表生成 - 管理员和管理人员可以访问
        const reportGenerationLink = document.querySelector('#userDropdown a[href="/report-generation"]');
        if (reportGenerationLink) {
            reportGenerationLink.style.display = (role === 'admin' || role === 'manager') ? 'flex' : 'none';
        }
        
        // 权限管理 - 只有管理员可以访问
        const permissionManagementLink = document.querySelector('#userDropdown a[href="/permission-management"]');
        if (permissionManagementLink) {
            permissionManagementLink.style.display = (role === 'admin') ? 'flex' : 'none';
        }
    }
    
    // 检查页面访问权限
    function checkPageAccessPermission() {
        const role = localStorage.getItem('currentUserRole');
        const currentPath = window.location.pathname;
        
        const pagePermissions = {
            '/system-settings': 'admin',
            '/system-monitor': ['admin', 'manager'],
            '/report-generation': ['admin', 'manager'],
            '/permission-management': 'admin'
        };
        
        const requiredRole = pagePermissions[currentPath];
        if (requiredRole) {
            if (Array.isArray(requiredRole)) {
                if (!requiredRole.includes(role)) {
                    alert('您没有权限访问此页面');
                    window.location.href = '/profile';
                    return false;
                }
            } else {
                if (role !== requiredRole) {
                    alert('您没有权限访问此页面');
                    window.location.href = '/profile';
                    return false;
                }
            }
        }
        
        return true;
    }
    
    // 个人信息下拉菜单
    const userInfo = document.getElementById('userInfo');
    const userDropdown = document.getElementById('userDropdown');
    
    if (userInfo && userDropdown) {
        userInfo.addEventListener('click', (e) => {
            e.stopPropagation();
            userDropdown.classList.toggle('active');
        });
        
        // 点击页面其他地方关闭下拉菜单
        document.addEventListener('click', () => {
            userDropdown.classList.remove('active');
        });
        
        // 阻止下拉菜单内的点击事件冒泡
        userDropdown.addEventListener('click', (e) => {
            e.stopPropagation();
        });
        
        // 退出登录
        userDropdown.addEventListener('click', (e) => {
            if (e.target.classList.contains('logout')) {
                localStorage.removeItem('currentUser');
                localStorage.removeItem('currentUserRole');
                localStorage.removeItem('currentUserAddress');
                localStorage.removeItem('currentUserPublicKey');
                localStorage.removeItem('currentUserEmployeeId');
                localStorage.removeItem('private_key');
                window.location.href = '/login';
            }
        });
    }
    
    // 初始化
    updateUserInfo();
    setActivePage();
    updateDropdownByPermissions();
    checkPageAccessPermission();
}

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUnifiedHeader);
} else {
    initUnifiedHeader();
}