import requests
import websocket
import json
import time

# 测试配置
BASE_URL = "http://localhost:8000"

class TestVideoCallSystem:
    def test_health_check(self):
        """测试服务是否正常运行"""
        print("\n=== 测试服务健康状态 ===")
        try:
            response = requests.get(BASE_URL)
            if response.status_code == 200:
                print("✅ 服务运行正常")
                return True
            else:
                print(f"❌ 服务状态异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 服务未运行: {e}")
            return False
    
    def test_create_room(self):
        """测试创建房间功能"""
        print("\n=== 测试创建房间 ===")
        try:
            response = requests.post(f"{BASE_URL}/create-room")
            if response.status_code == 200:
                room_id = response.json().get("room_id")
                print(f"✅ 房间创建成功: {room_id}")
                return room_id
            else:
                print(f"❌ 房间创建失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 房间创建异常: {e}")
            return None
    
    def test_room_info(self, room_id):
        """测试获取房间信息"""
        print("\n=== 测试获取房间信息 ===")
        try:
            response = requests.get(f"{BASE_URL}/room-info/{room_id}")
            if response.status_code == 200:
                room_info = response.json()
                print(f"✅ 房间信息获取成功: {room_info}")
                return True
            else:
                print(f"❌ 房间信息获取失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 房间信息获取异常: {e}")
            return False
    
    def test_websocket_connection(self, room_id, user_id):
        """测试WebSocket连接"""
        print("\n=== 测试WebSocket连接 ===")
        try:
            ws_url = f"ws://localhost:8000/ws/{room_id}/{user_id}"
            ws = websocket.WebSocket()
            ws.connect(ws_url)
            print("✅ WebSocket连接成功")
            
            # 发送测试消息
            test_message = {
                "type": "test",
                "message": "Hello from test"
            }
            ws.send(json.dumps(test_message))
            print("✅ 测试消息发送成功")
            
            # 等待并接收消息
            time.sleep(1)
            try:
                response = ws.recv()
                print(f"✅ 接收到消息: {response}")
            except websocket.WebSocketTimeoutException:
                print("⚠️  未收到消息 (正常，因为没有其他用户)")
            
            ws.close()
            print("✅ WebSocket连接关闭成功")
            return True
        except Exception as e:
            print(f"❌ WebSocket连接失败: {e}")
            return False

if __name__ == "__main__":
    print("开始测试视频通话系统...")
    
    test_system = TestVideoCallSystem()
    
    # 运行所有测试
    tests_passed = 0
    total_tests = 4
    
    # 1. 测试服务健康状态
    if test_system.test_health_check():
        tests_passed += 1
    
    # 2. 测试创建房间
    room_id = test_system.test_create_room()
    if room_id:
        tests_passed += 1
    
    # 3. 测试获取房间信息
    if room_id and test_system.test_room_info(room_id):
        tests_passed += 1
    
    # 4. 测试WebSocket连接
    if room_id and test_system.test_websocket_connection(room_id, "test_user"):
        tests_passed += 1
    
    # 输出测试结果
    print(f"\n=== 测试结果 ===")
    print(f"通过测试: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 所有测试通过！系统运行正常")
    else:
        print("⚠️  部分测试失败，需要检查系统配置")
