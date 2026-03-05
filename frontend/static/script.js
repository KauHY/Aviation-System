let socket;
let localStream;
let peerConnections = {};
let roomId;
let userId;
let isMicOn = true;
let isVideoOn = true;
let currentCamera = 'user'; // 'user' = 前置摄像头, 'environment' = 后置摄像头

// WebRTC配置
const pcConfig = {
    iceServers: [
        {
            urls: ['stun:stun.l.google.com:19302', 'stun:stun1.l.google.com:19302']
        }
    ]
};

// DOM元素
const joinRoomSection = document.getElementById('join-room');
const callSection = document.getElementById('call-section');
const roomIdInput = document.getElementById('room-id');
const joinBtn = document.getElementById('join-btn');
const createRoomBtn = document.getElementById('create-room-btn');
const leaveBtn = document.getElementById('leave-btn');
const localVideo = document.getElementById('local-video');
const remoteVideos = document.getElementById('remote-videos');
const micBtn = document.getElementById('mic-btn');
const videoBtn = document.getElementById('video-btn');
const flipCameraBtn = document.getElementById('flip-camera-btn');
const screenBtn = document.getElementById('screen-btn');
const currentRoom = document.getElementById('current-room');
const participantList = document.getElementById('participant-list');

// 聊天相关DOM元素
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendMessageBtn = document.getElementById('send-message-btn');

// 初始化
function init() {
    // 检查元素是否存在，避免在index.html页面加载时出错
    if (joinBtn) {
        joinBtn.addEventListener('click', joinRoom);
    }
    if (createRoomBtn) {
        createRoomBtn.addEventListener('click', createRoom);
    }
    if (leaveBtn) {
        leaveBtn.addEventListener('click', leaveRoom);
    }
    if (micBtn) {
        micBtn.addEventListener('click', toggleMic);
    }
    if (videoBtn) {
        videoBtn.addEventListener('click', toggleVideo);
    }
    if (screenBtn) {
        screenBtn.addEventListener('click', toggleScreen);
    }
    if (flipCameraBtn) {
        flipCameraBtn.addEventListener('click', flipCamera);
    }
    if (sendMessageBtn) {
        sendMessageBtn.addEventListener('click', sendChatMessage);
    }
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendChatMessage();
            }
        });
    }
}

// 全局变量存储选中的用户
let selectedUsers = [];
let allUsers = [];

// 创建房间
async function createRoom() {
    // 检查用户权限
    const currentUserRole = localStorage.getItem('currentUserRole');
    if (!currentUserRole || (currentUserRole !== 'admin' && currentUserRole !== 'manager')) {
        alert('只有总负责人和管理人员可以创建房间');
        return;
    }
    
    // 加载用户列表
    await loadAllUsers();
    
    // 显示模态框
    const modal = document.getElementById('create-room-modal');
    modal.classList.add('show');
    
    // 重置选择
    selectedUsers = [];
    updateSelectedCount();
}

// 加载所有用户
async function loadAllUsers() {
    try {
        const response = await fetch('/api/system/users');
        if (response.ok) {
            const data = await response.json();
            allUsers = data.users || [];
            renderUserList(allUsers);
        }
    } catch (error) {
        console.error('加载用户列表失败:', error);
        // 如果 API 失败，使用 localStorage 作为后备
        const users = JSON.parse(localStorage.getItem('users')) || {};
        allUsers = Object.keys(users).map(username => ({
            username: username,
            role: users[username].role || 'technician',
            employee_id: users[username].employee_id || username
        }));
        renderUserList(allUsers);
    }
}

// 渲染用户列表
function renderUserList(users) {
    const userList = document.getElementById('user-list');
    if (!userList) return;
    
    if (users.length === 0) {
        userList.innerHTML = '<div style="padding: 20px; text-align: center; color: #718096;">暂无用户</div>';
        return;
    }
    
    userList.innerHTML = users.map(user => {
        const roleText = getRoleText(user.role);
        const isSelected = selectedUsers.includes(user.username);
        return `
            <div class="user-item ${isSelected ? 'selected' : ''}" onclick="toggleUser('${user.username}')">
                <input type="checkbox" ${isSelected ? 'checked' : ''} onclick="event.stopPropagation(); toggleUser('${user.username}')">
                <div class="user-info">
                    <div class="name">${user.username}</div>
                    <div class="details">${roleText} | 工号: ${user.employee_id || user.username}</div>
                </div>
            </div>
        `;
    }).join('');
}

// 获取角色文本
function getRoleText(role) {
    const roleMap = {
        'admin': '总负责人',
        'manager': '管理人员',
        'technician': '技术人员'
    };
    return roleMap[role] || '技术人员';
}

// 切换用户选择
function toggleUser(username) {
    const index = selectedUsers.indexOf(username);
    if (index > -1) {
        selectedUsers.splice(index, 1);
    } else {
        if (selectedUsers.length >= 10) {
            alert('最多只能选择 10 人');
            return;
        }
        selectedUsers.push(username);
    }
    
    updateSelectedCount();
    renderUserList(allUsers);
}

// 更新选中计数
function updateSelectedCount() {
    const countElement = document.getElementById('selected-count');
    if (countElement) {
        countElement.textContent = selectedUsers.length;
    }
    
    const createBtn = document.getElementById('confirm-create-btn');
    if (createBtn) {
        createBtn.disabled = selectedUsers.length === 0;
    }
}

// 过滤用户
function filterUsers() {
    const searchInput = document.getElementById('user-search');
    if (!searchInput) return;
    
    const searchTerm = searchInput.value.toLowerCase().trim();
    
    if (!searchTerm) {
        renderUserList(allUsers);
        return;
    }
    
    const filtered = allUsers.filter(user => {
        return user.username.toLowerCase().includes(searchTerm) ||
               (user.employee_id && user.employee_id.toLowerCase().includes(searchTerm));
    });
    
    renderUserList(filtered);
}

// 关闭模态框
function closeCreateRoomModal() {
    const modal = document.getElementById('create-room-modal');
    modal.classList.remove('show');
    selectedUsers = [];
    const searchInput = document.getElementById('user-search');
    if (searchInput) searchInput.value = '';
}

// 确认创建房间
async function confirmCreateRoom() {
    if (selectedUsers.length === 0) {
        alert('请至少选择一个与会人员');
        return;
    }
    
    try {
        const response = await fetch('/create-room', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                invited_users: selectedUsers,
                max_participants: 10
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            roomIdInput.value = data.room_id;
            closeCreateRoomModal();
            alert(`房间创建成功！\n房间ID: ${data.room_id}\n邀请人员: ${selectedUsers.join(', ')}`);
        } else {
            throw new Error('创建房间失败');
        }
    } catch (error) {
        console.error('创建房间失败:', error);
        alert('创建房间失败，请重试');
    }
}

// 加入房间
async function joinRoom() {
    roomId = roomIdInput.value.trim();
    
    // 自动获取当前用户
    userId = localStorage.getItem('currentUser');
    
    if (!roomId) {
        alert('请输入房间ID');
        return;
    }
    
    if (!userId) {
        alert('未检测到登录信息，请重新登录');
        window.location.href = '/login';
        return;
    }
    
    try {
        // 验证房间访问权限
        const verifyResponse = await fetch('/verify-room-access', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                room_id: roomId,
                username: userId
            })
        });
        
        if (!verifyResponse.ok) {
            throw new Error('验证请求失败');
        }
        
        const verifyData = await verifyResponse.json();
        
        if (!verifyData.allowed) {
            alert(verifyData.reason || '您没有权限加入此房间');
            return;
        }
        
        // 权限验证通过，继续加入房间
        alert('🔍 正在请求摄像头和麦克风权限，请在浏览器提示中允许使用这些设备。');
        
        // 尝试获取视频和音频
        try {
            localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            localVideo.srcObject = localStream;
        } catch (videoError) {
            console.warn('无法获取视频设备，尝试只获取音频:', videoError);
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ video: false, audio: true });
                localVideo.srcObject = localStream;
                alert('无法访问摄像头，将仅使用音频通话');
            } catch (audioError) {
                console.warn('无法获取音频设备:', audioError);
                try {
                    localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
                    localVideo.srcObject = localStream;
                    alert('无法访问麦克风，将仅使用视频通话');
                } catch (bothError) {
                    console.error('无法获取任何媒体设备:', bothError);
                    throw new Error('无法访问摄像头和麦克风，请检查设备连接和权限设置');
                }
            }
        }
        
        // 显示连接中提示
        alert('🔗 正在连接到视频系统，请稍候...');
        
        // 连接WebSocket
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        socket = new WebSocket(`${protocol}//${window.location.host}/ws/${roomId}/${userId}`);
        
        // WebSocket连接成功处理
        socket.onopen = function() {
            console.log('WebSocket连接已打开');
            // 显示通话界面
            joinRoomSection.classList.add('hidden');
            callSection.classList.remove('hidden');
            currentRoom.textContent = roomId;
            
            // 添加本地用户到参会者列表
            addParticipant(userId);
            
            // 为本地视频添加双击事件
            setTimeout(() => {
                setupLocalVideoDoubleClick();
                // 初始化布局
                updateVideoLayout();
            }, 1000);
            
            // 通知用户连接成功
            alert('✅ 连接成功！已加入任务房间。');
        };
        
        socket.onmessage = handleSocketMessage;
        
        socket.onclose = function(event) {
            console.log('WebSocket连接已关闭:', event);
            // 如果连接关闭且不是用户主动离开，显示错误提示
            if (!event.wasClean) {
                alert('⚠️ 连接已断开，请检查网络连接后重试。');
                // 重置界面
                resetJoinRoom();
            }
        };
        
        socket.onerror = function(error) {
            console.error('WebSocket错误:', error);
            // 显示错误提示
            alert('❌ 连接失败，请检查网络连接和服务器状态后重试。');
            // 重置界面
            resetJoinRoom();
        };
        
    } catch (error) {
        console.error('加入房间失败:', error);
        let errorMessage = '无法加入房间: ' + error.message;
        if (error.name === 'NotAllowedError') {
            errorMessage += '\n请在浏览器地址栏左侧的锁图标中检查权限设置，确保允许使用摄像头和麦克风。';
        }
        alert(errorMessage);
    }
}

// 重置加入房间界面
function resetJoinRoom() {
    // 停止本地流
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localVideo.srcObject = null;
    }
    
    // 关闭WebSocket连接
    if (socket) {
        socket.close();
    }
    
    // 显示加入房间界面
    callSection.classList.add('hidden');
    joinRoomSection.classList.remove('hidden');
    
    // 清空参会者列表
    if (participantList) {
        participantList.innerHTML = '';
    }
    
    // 清空远程视频
    if (remoteVideos) {
        remoteVideos.innerHTML = '';
    }
}

// 离开房间
function leaveRoom() {
    // 关闭所有对等连接
    Object.values(peerConnections).forEach(pc => {
        pc.close();
    });
    peerConnections = {};
    
    // 停止本地流
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localVideo.srcObject = null;
    }
    
    // 关闭WebSocket连接
    if (socket) {
        socket.close();
    }
    
    // 清空远程视频和参会者列表
    remoteVideos.innerHTML = '';
    participantList.innerHTML = '';
    
    // 显示加入房间界面
    callSection.classList.add('hidden');
    joinRoomSection.classList.remove('hidden');
}

// WebSocket事件处理
function handleSocketOpen() {
    console.log('WebSocket连接已打开');
}

function handleSocketMessage(event) {
    try {
        const message = JSON.parse(event.data);
        console.log('收到消息:', message);
        
        switch (message.type) {
            case 'user_joined':
                console.log('用户加入:', message.user_id);
                handleUserJoined(message.user_id);
                break;
            case 'user_left':
                console.log('用户离开:', message.user_id);
                handleUserLeft(message.user_id);
                break;
            case 'offer':
                console.log('收到offer来自:', message.user_id);
                handleOffer(message);
                break;
            case 'answer':
                console.log('收到answer来自:', message.user_id);
                handleAnswer(message);
                break;
            case 'ice_candidate':
                console.log('收到ICE候选来自:', message.user_id);
                handleIceCandidate(message);
                break;
            case 'chat_message':
                console.log('收到聊天消息来自:', message.user_id);
                displayChatMessage(message);
                break;
            default:
                console.log('未知消息类型:', message.type);
        }
    } catch (error) {
        console.error('处理WebSocket消息失败:', error);
    }
}

function handleSocketClose() {
    console.log('WebSocket连接已关闭');
}

function handleSocketError(error) {
    console.error('WebSocket错误:', error);
}

// 处理用户加入
async function handleUserJoined(user_id) {
    // 不为自己创建远程视图
    if (user_id === userId) {
        console.log('跳过为自己创建远程视图');
        return;
    }
    
    addParticipant(user_id);
    
    // 创建对等连接
    const pc = createPeerConnection(user_id);
    
    // 添加本地流到对等连接
    localStream.getTracks().forEach(track => {
        pc.addTrack(track, localStream);
    });
    
    // 创建并发送offer
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    
    socket.send(JSON.stringify({
        type: 'offer',
        target_id: user_id,
        user_id: userId,
        sdp: offer
    }));
}

// 处理用户离开
function handleUserLeft(user_id) {
    removeParticipant(user_id);
    removeRemoteVideo(user_id);
    
    // 关闭对等连接
    if (peerConnections[user_id]) {
        peerConnections[user_id].close();
        delete peerConnections[user_id];
    }
}

// 处理offer
async function handleOffer(message) {
    const { target_id, sdp, user_id } = message;
    
    if (target_id !== userId) return;
    
    // 创建对等连接
    const pc = createPeerConnection(user_id);
    
    // 添加本地流到对等连接
    localStream.getTracks().forEach(track => {
        pc.addTrack(track, localStream);
    });
    
    // 设置远程描述
    await pc.setRemoteDescription(new RTCSessionDescription(sdp));
    
    // 创建并发送answer
    const answer = await pc.createAnswer();
    await pc.setLocalDescription(answer);
    
    socket.send(JSON.stringify({
        type: 'answer',
        target_id: user_id,
        user_id: userId,
        sdp: answer
    }));
}

// 处理answer
async function handleAnswer(message) {
    const { target_id, sdp, user_id } = message;
    
    if (target_id !== userId) return;
    
    // 设置远程描述
    const pc = peerConnections[user_id];
    if (pc) {
        await pc.setRemoteDescription(new RTCSessionDescription(sdp));
    }
}

// 处理ICE候选
async function handleIceCandidate(message) {
    const { target_id, candidate, user_id } = message;
    
    if (target_id !== userId) return;
    
    // 添加ICE候选
    const pc = peerConnections[user_id];
    if (pc) {
        await pc.addIceCandidate(new RTCIceCandidate(candidate));
    }
}

// 创建对等连接
function createPeerConnection(user_id) {
    const pc = new RTCPeerConnection(pcConfig);
    
    pc.onicecandidate = (event) => {
        if (event.candidate) {
            console.log('发送ICE候选到', user_id, event.candidate);
            socket.send(JSON.stringify({
                type: 'ice_candidate',
                target_id: user_id,
                user_id: userId,
                candidate: event.candidate
            }));
        } else {
            console.log('ICE候选收集完成');
        }
    };
    
    pc.ontrack = (event) => {
        console.log('收到远程流', user_id, event.streams[0]);
        addRemoteVideo(user_id, event.streams[0]);
    };
    
    pc.onconnectionstatechange = (event) => {
        console.log('连接状态变化:', pc.connectionState);
        if (pc.connectionState === 'connected') {
            console.log('WebRTC连接已成功建立');
        } else if (pc.connectionState === 'failed') {
            console.error('WebRTC连接失败');
        } else if (pc.connectionState === 'disconnected') {
            console.log('WebRTC连接已断开');
        }
    };
    
    pc.oniceconnectionstatechange = (event) => {
        console.log('ICE连接状态变化:', pc.iceConnectionState);
    };
    
    pc.onsignalingstatechange = (event) => {
        console.log('信令状态变化:', pc.signalingState);
    };
    
    peerConnections[user_id] = pc;
    return pc;
}

// 添加远程视频
function addRemoteVideo(user_id, stream) {
    console.log('添加远程视频:', user_id, stream);
    
    // 不为自己创建远程视图
    if (user_id === userId) {
        console.log('跳过为自己创建远程视图');
        return;
    }
    
    if (!remoteVideos) {
        console.error('remoteVideos元素不存在');
        return;
    }
    
    let videoElement = document.getElementById(`remote-${user_id}`);
    if (!videoElement) {
        console.log('创建新的远程视频元素:', user_id);
        const videoWrapper = document.createElement('div');
        videoWrapper.className = 'video-wrapper';
        videoWrapper.dataset.userId = user_id;
        videoWrapper.innerHTML = `
            <h3>远程视图 - ${user_id}</h3>
            <div class="video-status online">在线</div>
            <video id="remote-${user_id}" autoplay></video>
        `;
        
        videoWrapper.addEventListener('click', () => {
            openFullscreen(user_id, `远程视图 - ${user_id}`);
        });
        
        remoteVideos.appendChild(videoWrapper);
        videoElement = document.getElementById(`remote-${user_id}`);
        
        if (!videoElement) {
            console.error('无法创建视频元素:', user_id);
            return;
        }
    }
    
    console.log('设置视频流:', user_id, stream);
    videoElement.srcObject = stream;
    
    videoElement.onerror = (error) => {
        console.error('视频元素错误:', error);
    };
    
    videoElement.onplaying = () => {
        console.log('远程视频开始播放:', user_id);
    };
}

// 打开全屏放大
function openFullscreen(videoId, title) {
    const modal = document.getElementById('fullscreen-modal');
    const fullscreenVideo = document.getElementById('fullscreen-video');
    const fullscreenTitle = document.getElementById('fullscreen-title');
    
    // 获取原始视频流
    let sourceVideo;
    if (videoId === 'local') {
        sourceVideo = document.getElementById('local-video');
    } else {
        sourceVideo = document.getElementById(`remote-${videoId}`);
    }
    
    if (sourceVideo && sourceVideo.srcObject) {
        fullscreenVideo.srcObject = sourceVideo.srcObject;
        fullscreenTitle.textContent = title;
        modal.classList.add('show');
    }
}

// 关闭全屏
function closeFullscreen() {
    const modal = document.getElementById('fullscreen-modal');
    const fullscreenVideo = document.getElementById('fullscreen-video');
    
    modal.classList.remove('show');
    fullscreenVideo.srcObject = null;
}

// 为本地视频添加点击事件
function setupLocalVideoDoubleClick() {
    const localVideoWrapper = document.querySelector('.video-wrapper:not(.remote-video)');
    if (localVideoWrapper) {
        localVideoWrapper.addEventListener('click', () => {
            openFullscreen('local', '本地视图');
        });
    }
}

// 移除远程视频
function removeRemoteVideo(user_id) {
    const videoWrapper = document.querySelector(`#remote-${user_id}`)?.parentElement;
    if (videoWrapper) {
        videoWrapper.remove();
    }
}

// 添加参会者
function addParticipant(user_id) {
    // 检查是否已存在
    if (!document.querySelector(`#participant-${user_id}`)) {
        const li = document.createElement('li');
        li.id = `participant-${user_id}`;
        li.textContent = user_id;
        participantList.appendChild(li);
    }
}

// 移除参会者
function removeParticipant(user_id) {
    const li = document.getElementById(`participant-${user_id}`);
    if (li) {
        li.remove();
    }
}

// 切换麦克风
function toggleMic() {
    isMicOn = !isMicOn;
    localStream.getAudioTracks().forEach(track => {
        track.enabled = isMicOn;
    });
    micBtn.textContent = isMicOn ? '关闭麦克风' : '开启麦克风';
}

// 切换摄像头
function toggleVideo() {
    isVideoOn = !isVideoOn;
    localStream.getVideoTracks().forEach(track => {
        track.enabled = isVideoOn;
    });
    videoBtn.textContent = isVideoOn ? '关闭摄像头' : '开启摄像头';
}

// 切换屏幕共享
async function toggleScreen() {
    try {
        const displayStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        
        // 获取屏幕共享轨道
        const screenTrack = displayStream.getVideoTracks()[0];
        
        // 替换本地流中的视频轨道
        const videoTrack = localStream.getVideoTracks()[0];
        localStream.removeTrack(videoTrack);
        localStream.addTrack(screenTrack);
        
        // 更新所有对等连接
        Object.values(peerConnections).forEach(pc => {
            const sender = pc.getSenders().find(s => s.track.kind === 'video');
            if (sender) {
                sender.replaceTrack(screenTrack);
            }
        });
        
        // 监听屏幕共享结束
        screenTrack.onended = async () => {
            // 恢复摄像头
            const cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
            const cameraTrack = cameraStream.getVideoTracks()[0];
            
            localStream.removeTrack(screenTrack);
            localStream.addTrack(cameraTrack);
            localVideo.srcObject = localStream;
            
            // 更新所有对等连接
            Object.values(peerConnections).forEach(pc => {
                const sender = pc.getSenders().find(s => s.track.kind === 'video');
                if (sender) {
                    sender.replaceTrack(cameraTrack);
                }
            });
        };
        
        localVideo.srcObject = localStream;
    } catch (error) {
        console.error('屏幕共享失败:', error);
        alert('无法共享屏幕，请检查权限');
    }
}

// 翻转摄像头
async function flipCamera() {
    try {
        // 切换摄像头
        currentCamera = currentCamera === 'user' ? 'environment' : 'user';
        
        // 获取新的摄像头流
        const newStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: currentCamera },
            audio: true
        });
        
        // 获取新的视频轨道
        const newVideoTrack = newStream.getVideoTracks()[0];
        
        // 替换本地流中的视频轨道
        const oldVideoTrack = localStream.getVideoTracks()[0];
        localStream.removeTrack(oldVideoTrack);
        localStream.addTrack(newVideoTrack);
        
        // 更新本地视频
        localVideo.srcObject = localStream;
        
        // 更新所有对等连接
        Object.values(peerConnections).forEach(pc => {
            const sender = pc.getSenders().find(s => s.track.kind === 'video');
            if (sender) {
                sender.replaceTrack(newVideoTrack);
            }
        });
        
        // 停止旧的视频轨道
        oldVideoTrack.stop();
        
        // 更新按钮文本
        flipCameraBtn.textContent = currentCamera === 'user' ? '翻转摄像头（前置）' : '翻转摄像头（后置）';
        
        console.log('摄像头已切换到:', currentCamera === 'user' ? '前置' : '后置');
    } catch (error) {
        console.error('翻转摄像头失败:', error);
        alert('无法切换摄像头，请检查设备支持');
    }
}

// 初始化应用
window.onload = function() {
    init();
    setupFlightSearch();
};

// 航班查询功能
function setupFlightSearch() {
    const searchBtn = document.getElementById('search-flight-btn');
    const resultsContainer = document.getElementById('results-container');
    const formElements = [
        document.getElementById('flight-number'),
        document.getElementById('departure-airport'),
        document.getElementById('arrival-airport'),
        document.getElementById('flight-date')
    ];
    
    if (searchBtn) {
        // 添加表单输入事件，实时验证
        formElements.forEach(element => {
            if (element) {
                element.addEventListener('input', function() {
                    // 移除错误样式
                    this.style.borderColor = '';
                    this.style.boxShadow = '';
                });
            }
        });
        
        searchBtn.addEventListener('click', async function() {
            // 获取表单数据
            const flightNumber = document.getElementById('flight-number').value;
            const departureAirport = document.getElementById('departure-airport').value;
            const arrivalAirport = document.getElementById('arrival-airport').value;
            const flightDate = document.getElementById('flight-date').value;
            
            // 验证表单
            if (!flightNumber && !departureAirport && !arrivalAirport) {
                // 显示错误提示
                const errorMessage = document.createElement('div');
                errorMessage.style.cssText = 'color: #ef4444; margin-bottom: 15px; font-size: 14px;';
                errorMessage.textContent = '请至少输入一个查询条件';
                
                const form = document.querySelector('.flight-search-form');
                const existingError = form.querySelector('.error-message');
                if (existingError) {
                    existingError.remove();
                }
                form.insertBefore(errorMessage, form.firstChild);
                
                // 添加错误样式到表单元素
                formElements.forEach(element => {
                    if (element) {
                        element.style.borderColor = '#ef4444';
                        element.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.1)';
                    }
                });
                
                return;
            }
            
            // 显示加载状态
            resultsContainer.innerHTML = '<div style="text-align: center; padding: 40px 0;"><div class="loading"></div><p style="margin-top: 15px;">查询中...</p></div>';
            
            // 禁用查询按钮，防止重复点击
            searchBtn.disabled = true;
            searchBtn.style.opacity = '0.7';
            searchBtn.textContent = '查询中...';
            
            try {
                // 发送请求到后端API
                const response = await fetch('/api/flight/search', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        flight_number: flightNumber,
                        departure_airport: departureAirport,
                        arrival_airport: arrivalAirport,
                        flight_date: flightDate
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    displayFlightResults(data.flights);
                } else {
                    resultsContainer.innerHTML = `<p class="no-results">${data.message || '未找到航班信息'}</p>`;
                }
            } catch (error) {
                console.error('查询航班失败:', error);
                resultsContainer.innerHTML = '<p class="no-results">查询失败，请稍后重试</p>';
            } finally {
                // 恢复查询按钮状态
                searchBtn.disabled = false;
                searchBtn.style.opacity = '1';
                searchBtn.textContent = '查询航班';
            }
        });
    }
}

// 显示航班查询结果
function displayFlightResults(flights) {
    const resultsContainer = document.getElementById('results-container');
    
    if (!flights || flights.length === 0) {
        resultsContainer.innerHTML = '<p class="no-results">未找到匹配的航班信息</p>';
        return;
    }
    
    let html = '';
    
    flights.forEach(flight => {
        html += `
            <div class="flight-card">
                <h4>${flight.flight_number} - ${flight.airline || '未知航空公司'}</h4>
                <div class="flight-info">
                    <div class="info-item">
                        <div class="info-label">出发机场</div>
                        <div class="info-value">${flight.departure_airport} (${flight.departure_city || ''})</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">到达机场</div>
                        <div class="info-value">${flight.arrival_airport} (${flight.arrival_city || ''})</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">出发时间</div>
                        <div class="info-value">${flight.departure_time || '未知'}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">到达时间</div>
                        <div class="info-value">${flight.arrival_time || '未知'}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">日期</div>
                        <div class="info-value">${flight.flight_date || '未知'}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">飞机型号</div>
                        <div class="info-value">${flight.aircraft_type || '未知'}</div>
                    </div>
                </div>
                <div class="flight-status ${getStatusClass(flight.status)}">
                    ${getStatusText(flight.status)}
                </div>
            </div>
        `;
    });
    
    resultsContainer.innerHTML = html;
}

// 获取状态样式类
function getStatusClass(status) {
    switch (status) {
        case 'on-time':
        case '正常':
            return 'on-time';
        case 'delayed':
        case '延误':
            return 'delayed';
        case 'cancelled':
        case '取消':
            return 'cancelled';
        default:
            return 'on-time';
    }
}

// 获取状态文本
function getStatusText(status) {
    switch (status) {
        case 'on-time':
            return '准点';
        case 'delayed':
            return '延误';
        case 'cancelled':
            return '取消';
        default:
            return status || '未知';
    }
}

// 发送聊天消息
function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message) return;
    
    const timestamp = new Date().toLocaleTimeString();
    
    // 发送消息到服务器
    socket.send(JSON.stringify({
        type: 'chat_message',
        message: message,
        timestamp: timestamp
    }));
    
    // 显示自己发送的消息
    const messageElement = createChatMessageElement('sent', userId, message, timestamp);
    chatMessages.appendChild(messageElement);
    
    // 清空输入框
    chatInput.value = '';
    
    // 滚动到底部
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 显示聊天消息
function displayChatMessage(message) {
    const { user_id, message: content, timestamp } = message;
    
    // 如果消息是自己发送的，不显示（避免重复）
    if (user_id === userId) return;
    
    // 显示收到的消息
    const messageElement = createChatMessageElement('received', user_id, content, timestamp);
    chatMessages.appendChild(messageElement);
    
    // 滚动到底部
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 创建聊天消息元素
function createChatMessageElement(type, sender, content, timestamp) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;
    
    const senderDiv = document.createElement('div');
    senderDiv.className = 'message-sender';
    senderDiv.textContent = sender;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;
    
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = timestamp;
    
    messageDiv.appendChild(senderDiv);
    messageDiv.appendChild(contentDiv);
    messageDiv.appendChild(timeDiv);
    
    return messageDiv;
}

// 检测人员分配管理功能
function initInspectorAssignment() {
    // 检查元素是否存在，避免在其他页面加载时出错
    const inspectorList = document.getElementById('inspector-list');
    const taskList = document.getElementById('task-list');
    
    if (inspectorList && taskList) {
        // 加载检测人员列表
        loadInspectors();
        // 加载检测任务列表
        loadTasks();
    }
}

// 加载检测人员列表
async function loadInspectors() {
    try {
        const response = await fetch('/api/inspectors');
        if (!response.ok) {
            throw new Error('获取检测人员列表失败');
        }
        const data = await response.json();
        if (data.success) {
            displayInspectors(data.inspectors);
        }
    } catch (error) {
        console.error('加载检测人员失败:', error);
    }
}

// 加载检测任务列表
async function loadTasks() {
    try {
        const response = await fetch('/api/tasks');
        if (!response.ok) {
            throw new Error('获取检测任务列表失败');
        }
        const data = await response.json();
        if (data.success) {
            displayTasks(data.tasks);
        }
    } catch (error) {
        console.error('加载检测任务失败:', error);
    }
}

// 显示检测人员列表
function displayInspectors(inspectors) {
    const inspectorList = document.getElementById('inspector-list');
    if (!inspectorList) return;
    
    if (!inspectors || inspectors.length === 0) {
        inspectorList.innerHTML = '<p class="no-results">暂无检测人员</p>';
        return;
    }
    
    let html = '';
    inspectors.forEach(inspector => {
        html += `
            <div class="inspector-item">
                <div class="inspector-info">
                    <h4>${inspector.name}</h4>
                    <p>${inspector.position} | ${inspector.specialty}</p>
                    ${inspector.current_task ? `<p>当前任务: ${inspector.current_task}</p>` : ''}
                </div>
                <div class="inspector-status ${inspector.status}">${inspector.status === 'available' ? '可用' : '忙碌'}</div>
            </div>
        `;
    });
    
    inspectorList.innerHTML = html;
}

// 显示检测任务列表
function displayTasks(tasks) {
    const taskList = document.getElementById('task-list');
    if (!taskList) return;
    
    if (!tasks || tasks.length === 0) {
        taskList.innerHTML = '<p class="no-results">暂无检测任务</p>';
        return;
    }
    
    let html = '';
    tasks.forEach(task => {
        html += `
            <div class="assignment-task-item">
                <div class="assignment-task-info">
                    <h4>${task.flight_number} - ${task.task_type}</h4>
                    <p>优先级: ${task.priority === 'high' ? '高' : task.priority === 'medium' ? '中' : '低'}</p>
                    <p>截止时间: ${task.deadline}</p>
                    ${task.assignee_id ? `<p>已分配给: ${task.assignee_id}</p>` : ''}
                </div>
                <div class="assignment-task-actions">
                    ${task.status === 'pending' ? '<button class="btn assign" onclick="assignTaskToInspector(this, \'' + task.id + '\')">分配</button>' : ''}
                    ${task.status === 'assigned' ? '<button class="btn complete" onclick="completeTask(\'' + task.id + '\')">完成</button>' : ''}
                </div>
            </div>
        `;
    });
    
    taskList.innerHTML = html;
}

// 分配任务给检测人员
function assignTaskToInspector(button, taskId) {
    // 弹出选择检测人员的对话框
    const inspectorSelect = prompt('请输入检测人员ID: 1. 张三 2. 李四 3. 王五 4. 赵六');
    if (!inspectorSelect) return;
    
    const inspectorId = inspectorSelect.trim();
    if (!inspectorId) return;
    
    // 发送分配请求
    assignTask(taskId, inspectorId);
}

// 分配任务
async function assignTask(taskId, inspectorId) {
    try {
        const response = await fetch('/api/tasks/assign', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ task_id: taskId, inspector_id: inspectorId })
        });
        
        if (!response.ok) {
            throw new Error('分配任务失败');
        }
        
        const data = await response.json();
        if (data.success) {
            alert('任务分配成功');
            // 重新加载任务和检测人员列表
            loadTasks();
            loadInspectors();
        } else {
            alert('分配失败: ' + data.message);
        }
    } catch (error) {
        console.error('分配任务失败:', error);
        alert('分配任务失败，请重试');
    }
}

// 完成任务
async function completeTask(taskId) {
    try {
        const response = await fetch('/api/tasks/complete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ task_id: taskId })
        });
        
        if (!response.ok) {
            throw new Error('完成任务失败');
        }
        
        const data = await response.json();
        if (data.success) {
            alert('任务完成成功');
            // 重新加载任务和检测人员列表
            loadTasks();
            loadInspectors();
        } else {
            alert('完成失败: ' + data.message);
        }
    } catch (error) {
        console.error('完成任务失败:', error);
        alert('完成任务失败，请重试');
    }
}

// 初始化检测人员分配管理
initInspectorAssignment();

// 初始化
init();