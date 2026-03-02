/**
 * 前端权限管理模块
 */

const Permission = {
    // 维修记录权限
    MAINTENANCE_VIEW: 'maintenance:view',
    MAINTENANCE_CREATE: 'maintenance:create',
    MAINTENANCE_EDIT: 'maintenance:edit',
    MAINTENANCE_DELETE: 'maintenance:delete',
    MAINTENANCE_APPROVE: 'maintenance:approve',
    MAINTENANCE_UPLOAD: 'maintenance:upload',
    
    // 任务管理权限
    TASK_VIEW: 'task:view',
    TASK_CREATE: 'task:create',
    TASK_EDIT: 'task:edit',
    TASK_DELETE: 'task:delete',
    TASK_ASSIGN: 'task:assign',
    
    // 航班信息权限
    FLIGHT_VIEW: 'flight:view',
    
    // 航空器信息权限
    AIRCRAFT_VIEW: 'aircraft:view',
    
    // 用户管理权限
    USER_VIEW: 'user:view',
    USER_CREATE: 'user:create',
    USER_EDIT: 'user:edit',
    USER_DELETE: 'user:delete',
    
    // 角色管理权限
    ROLE_VIEW: 'role:view',
    ROLE_CREATE: 'role:create',
    ROLE_EDIT: 'role:edit',
    ROLE_DELETE: 'role:delete',
    
    // 权限分配权限
    PERMISSION_ASSIGN: 'permission:assign',
    
    // 系统设置权限
    SYSTEM_SETTINGS: 'system:settings',
    
    // 系统监控权限
    SYSTEM_MONITOR: 'system:monitor',
    
    // 数据备份权限
    DATA_BACKUP: 'data:backup',
    DATA_RESTORE: 'data:restore',
    
    // 日志查看权限
    LOG_VIEW: 'log:view',
    
    // 区块链管理权限
    BLOCKCHAIN_VIEW: 'blockchain:view',
    BLOCKCHAIN_MANAGE: 'blockchain:manage',
    
    // 报表生成权限
    REPORT_GENERATE: 'report:generate',
    REPORT_EXPORT: 'report:export'
};

const Role = {
    ADMIN: 'admin',
    MANAGER: 'manager',
    TECHNICIAN: 'technician',
    USER: 'user'
};

// 角色权限映射
const ROLE_PERMISSIONS = {
    [Role.TECHNICIAN]: [
        Permission.MAINTENANCE_VIEW,
        Permission.MAINTENANCE_CREATE,
        Permission.MAINTENANCE_EDIT,
        Permission.MAINTENANCE_UPLOAD,
        Permission.TASK_VIEW,
        Permission.FLIGHT_VIEW,
        Permission.AIRCRAFT_VIEW
    ],
    [Role.MANAGER]: [
        Permission.MAINTENANCE_VIEW,
        Permission.MAINTENANCE_CREATE,
        Permission.MAINTENANCE_EDIT,
        Permission.MAINTENANCE_DELETE,
        Permission.MAINTENANCE_APPROVE,
        Permission.TASK_VIEW,
        Permission.TASK_CREATE,
        Permission.TASK_EDIT,
        Permission.TASK_DELETE,
        Permission.TASK_ASSIGN,
        Permission.FLIGHT_VIEW,
        Permission.AIRCRAFT_VIEW,
        Permission.SYSTEM_MONITOR,
        Permission.REPORT_GENERATE,
        Permission.REPORT_EXPORT
    ],
    [Role.ADMIN]: [
        Permission.MAINTENANCE_VIEW,
        Permission.MAINTENANCE_CREATE,
        Permission.MAINTENANCE_EDIT,
        Permission.MAINTENANCE_DELETE,
        Permission.MAINTENANCE_APPROVE,
        Permission.TASK_VIEW,
        Permission.TASK_CREATE,
        Permission.TASK_EDIT,
        Permission.TASK_DELETE,
        Permission.TASK_ASSIGN,
        Permission.FLIGHT_VIEW,
        Permission.AIRCRAFT_VIEW,
        Permission.USER_VIEW,
        Permission.USER_CREATE,
        Permission.USER_EDIT,
        Permission.USER_DELETE,
        Permission.ROLE_VIEW,
        Permission.ROLE_CREATE,
        Permission.ROLE_EDIT,
        Permission.ROLE_DELETE,
        Permission.PERMISSION_ASSIGN,
        Permission.SYSTEM_SETTINGS,
        Permission.SYSTEM_MONITOR,
        Permission.DATA_BACKUP,
        Permission.DATA_RESTORE,
        Permission.LOG_VIEW,
        Permission.BLOCKCHAIN_VIEW,
        Permission.BLOCKCHAIN_MANAGE,
        Permission.REPORT_GENERATE,
        Permission.REPORT_EXPORT
    ],
    [Role.USER]: [
        Permission.MAINTENANCE_VIEW,
        Permission.FLIGHT_VIEW,
        Permission.AIRCRAFT_VIEW
    ]
};

// 获取当前用户角色
function getCurrentUserRole() {
    return localStorage.getItem('currentUserRole') || Role.USER;
}

// 获取当前用户ID
function getCurrentUserId() {
    return localStorage.getItem('currentUser') || 'unknown';
}

// 检查是否有指定权限
function hasPermission(permission) {
    const userRole = getCurrentUserRole();
    const permissions = ROLE_PERMISSIONS[userRole] || [];
    return permissions.includes(permission);
}

// 检查数据访问权限（数据隔离）
function hasDataAccess(resource, dataOwner) {
    const userRole = getCurrentUserRole();
    const currentUserId = getCurrentUserId();
    
    // 技术人员只能访问自己创建的数据
    if (userRole === Role.TECHNICIAN) {
        if (resource === 'maintenance_record' || resource === 'task') {
            return dataOwner === currentUserId;
        }
        return true;
    }
    
    // 管理人员可以访问所有数据
    if (userRole === Role.MANAGER) {
        return true;
    }
    
    // 总负责人可以访问所有数据
    if (userRole === Role.ADMIN) {
        return true;
    }
    
    // 普通用户只能查看数据
    if (userRole === Role.USER) {
        return ['maintenance_record', 'task', 'flight', 'aircraft'].includes(resource);
    }
    
    return false;
}

// 根据权限显示/隐藏元素
function toggleElementByPermission(elementId, permission, showIfHasPermission = true) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const hasPerm = hasPermission(permission);
    element.style.display = (hasPerm === showIfHasPermission) ? '' : 'none';
}

// 根据权限显示/隐藏按钮
function toggleButtonByPermission(buttonId, permission, showIfHasPermission = true) {
    const button = document.getElementById(buttonId);
    if (!button) return;
    
    const hasPerm = hasPermission(permission);
    button.style.display = (hasPerm === showIfHasPermission) ? 'inline-block' : 'none';
}

// 根据权限显示/隐藏链接
function toggleLinkByPermission(linkSelector, permission, showIfHasPermission = true) {
    const links = document.querySelectorAll(linkSelector);
    links.forEach(link => {
        const hasPerm = hasPermission(permission);
        link.style.display = (hasPerm === showIfHasPermission) ? 'flex' : 'none';
    });
}

// 根据权限显示/隐藏菜单项
function toggleMenuItemByPermission(menuItemSelector, permission, showIfHasPermission = true) {
    const menuItems = document.querySelectorAll(menuItemSelector);
    menuItems.forEach(item => {
        const hasPerm = hasPermission(permission);
        item.style.display = (hasPerm === showIfHasPermission) ? 'block' : 'none';
    });
}

// 更新用户下拉菜单（根据权限）
function updateUserDropdownMenu() {
    const userRole = getCurrentUserRole();
    
    // 系统设置 - 只有管理员可以访问
    toggleLinkByPermission('a[href="/system-settings"]', Permission.SYSTEM_SETTINGS);
    
    // 系统监控 - 管理员和管理人员可以访问
    if (userRole === Role.ADMIN || userRole === Role.MANAGER) {
        toggleLinkByPermission('a[href="/system-monitor"]', Permission.SYSTEM_MONITOR, true);
    } else {
        toggleLinkByPermission('a[href="/system-monitor"]', Permission.SYSTEM_MONITOR, false);
    }
    
    // 报表生成 - 管理员和管理人员可以访问
    if (userRole === Role.ADMIN || userRole === Role.MANAGER) {
        toggleLinkByPermission('a[href="/report-generation"]', Permission.REPORT_GENERATE, true);
    } else {
        toggleLinkByPermission('a[href="/report-generation"]', Permission.REPORT_GENERATE, false);
    }
}

// 更新主导航栏（根据权限）
function updateMainNavbar() {
    const userRole = getCurrentUserRole();
    
    // 隐藏系统设置、系统监控、报表生成（已移到用户下拉菜单）
    // 这些功能现在通过用户下拉菜单访问
}

// 页面加载时检查权限
function checkPagePermission() {
    const userRole = getCurrentUserRole();
    const currentPath = window.location.pathname;
    
    // 检查页面访问权限
    const pagePermissions = {
        '/system-settings': Permission.SYSTEM_SETTINGS,
        '/system-monitor': Permission.SYSTEM_MONITOR,
        '/report-generation': Permission.REPORT_GENERATE,
        '/user-management': Permission.USER_VIEW,
        '/role-management': Permission.ROLE_VIEW,
        '/permission-management': Permission.PERMISSION_ASSIGN,
        '/data-backup': Permission.DATA_BACKUP,
        '/log-view': Permission.LOG_VIEW,
        '/blockchain-manage': Permission.BLOCKCHAIN_MANAGE
    };
    
    const requiredPermission = pagePermissions[currentPath];
    if (requiredPermission && !hasPermission(requiredPermission)) {
        alert('您没有权限访问此页面');
        window.location.href = '/profile';
        return false;
    }
    
    return true;
}

// 显示权限不足提示
function showPermissionDenied(message = '您没有权限执行此操作') {
    alert(message);
}

// 记录权限检查（前端审计）
function logPermissionCheck(resource, action, allowed, reason = '') {
    const log = {
        timestamp: new Date().toISOString(),
        user_id: getCurrentUserId(),
        user_role: getCurrentUserRole(),
        resource: resource,
        action: action,
        allowed: allowed,
        reason: reason
    };
    
    // 可以将日志发送到后端保存
    console.log('Permission Check:', log);
}

// 获取用户权限列表
function getUserPermissions() {
    const userRole = getCurrentUserRole();
    return ROLE_PERMISSIONS[userRole] || [];
}

// 检查是否有任意一个权限
function hasAnyPermission(permissions) {
    return permissions.some(perm => hasPermission(perm));
}

// 检查是否有所有权限
function hasAllPermissions(permissions) {
    return permissions.every(perm => hasPermission(perm));
}

// 页面加载完成后初始化权限控制
document.addEventListener('DOMContentLoaded', function() {
    // 检查页面访问权限
    checkPagePermission();
    
    // 更新用户下拉菜单
    updateUserDropdownMenu();
    
    // 更新主导航栏
    updateMainNavbar();
});

// 导出权限管理对象
window.PermissionManager = {
    Permission,
    Role,
    hasPermission,
    hasDataAccess,
    toggleElementByPermission,
    toggleButtonByPermission,
    toggleLinkByPermission,
    toggleMenuItemByPermission,
    updateUserDropdownMenu,
    updateMainNavbar,
    checkPagePermission,
    showPermissionDenied,
    logPermissionCheck,
    getUserPermissions,
    hasAnyPermission,
    hasAllPermissions,
    getCurrentUserRole,
    getCurrentUserId
};
