import asyncio
import socket
import websockets
import uuid
import json
import log
import argparse
# 配置日志
log = log.HandleLog()

#解析启动函数
parser = argparse.ArgumentParser
parser.add_argument('-i', '--ip', type=str, default=None)
parser.add_argument('-p', '--port', type=int, default=1145)
args = parser.parse_args()
# 获取 IP 地址，如果未指定则获取本地 IP
if args.ip is None:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = '127.0.0.1'
else:
    ip = args.ip
port = args.port

# 模式列表
mode_r = ['n-n', 'n-1', '1-n']
mode = mode_r[0]
server_client_id = str(uuid.uuid4())

# 储存已连接的用户及其WebSocket连接对象
clients = dict()
stop = False

# 存储消息关系（n-n模式使用）
relations = dict()

# n-1模式存储
target_n_1 = {
    'id': '',
    'client': None
}

# 1-n模式存储
client_1_n = {
    'id': '',
    'client': None
}

# 默认惩罚时长（单位：秒）
punishmentDuration = 5

# 默认发送心跳的时间间隔（单位：秒）
punishmentTime = 1

# 存储客户端和发送计时器的关系（如果需要的话）
client_timers = dict()

# 定义心跳消息模板
heartbeat_msg = {
    "type": "heartbeat",
    "clientId": "",
    "targetId": "",
    "message": "200"
}

# 获取本地IP
def get_local_ip():
    try:
        # 创建一个UDP套接字
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到一个不存在的地址，这样不会真正发送数据
        s.connect(('8.8.8.8', 80))
        # 获取本地IP地址
        local_ip = s.getsockname()
        # 关闭套接字
        s.close()
    except Exception as e:
        log.error(f"Error occurred while getting local IP: {e}")
        local_ip = None
    return local_ip[0] if local_ip else None

# 检查绑定关系和客户端存在性
def check_bind_and_client(data):
    client_Id = data.get('clientId')
    target_Id = data.get('targetId')
    send_data = data.copy()
    if mode == mode_r[0] and relations.get(client_Id) != target_Id:
        send_data['type'] = "bind"
        send_data['message'] = "402"
        log.info(f'client_Id:{client_Id} 错误：未绑定APP！')
        return send_data
    elif mode == mode_r[2] and client_1_n['id'] == "":
        send_data['type'] = "bind"
        send_data['message'] = "402"
        log.info(f'client_Id:{client_Id} 错误：客户端不存在！')
        return send_data
    elif mode == mode_r[1] and target_n_1['id'] == "":
        send_data['type'] = "error"
        send_data['message'] = "403 - no app client"
        log.info('无APP连接！')
        return send_data
    if target_Id not in clients:
        send_data['message'] = "404"
        log.info(f'未找到匹配的客户端，clientId:{client_Id}')
        return send_data
    return None

# 处理绑定消息
async def handler_type_bind(websocket, data):
    client_Id = data.get('clientId')
    target_Id = data.get('targetId')
    send_data = data.copy()
    if mode == mode_r[0]:
        if client_Id in clients and target_Id in clients:
            if client_Id not in relations or target_Id not in relations.values():
                relations[client_Id] = target_Id
                client = clients[client_Id]
                send_data['message'] = "200"
                await websocket.send(json.dumps(send_data))
                await client.send(json.dumps(send_data))
                log.info(f'clientId:{client_Id},targetId:{target_Id} 绑定成功')
            else:
                send_data['message'] = "400"
                await websocket.send(json.dumps(send_data))
                log.info(f'clientId:{client_Id},targetId:{target_Id} 绑定失败 原因：其中一方已被绑定过')
                return
        else:
            send_data['message'] = "401"
            await websocket.send(json.dumps(send_data))
            log.info('客户端或APP连接不存在！')
            return
    elif mode == mode_r[1]:
        if target_Id in clients and target_n_1['id'] == "":
            send_data['message'] = "200"
            await websocket.send(json.dumps(send_data))
            target_n_1['id'] = target_Id
            target_n_1['client'] = websocket
            for client in clients.values():
                await client.send(json.dumps(send_data))
            log.info(f'targetId:{target_Id} 主机连接成功')
        elif target_n_1['id'] != "":
            send_data['message'] = "401"
            await websocket.send(json.dumps(send_data))
            log.info('APP已达连接上限！')
            return
        else:
            send_data['message'] = "401"
            await websocket.send(json.dumps(send_data))
            log.info('客户端或APP连接不存在！')
            return
    elif mode == mode_r[2]:
        if client_Id in clients and target_Id in clients and client_1_n['id'] != "":
            client = clients[client_Id]
            send_data['message'] = "200"
            await websocket.send(json.dumps(send_data))
            send_data_a = {
                'type': 'msgClient',
                'targetId': target_Id
            }
            await client.send(json.dumps(send_data_a))
            log.info(f'targetId:{target_Id} 主机连接成功')
        else:
            send_data['message'] = "401"
            await websocket.send(json.dumps(send_data))
            log.info('客户端或APP连接不存在！')
            return
    else:
        log.info("模式错误，即将断开连接")
        await on_connection_closed(websocket)

# 处理类型1、2、3的消息
async def handler_type_123(websocket, data):
    error_data = check_bind_and_client(data)
    if error_data:
        await websocket.send(json.dumps(error_data))
        return
    client_Id = data.get('clientId')
    target_Id = data.get('targetId')
    message = data.get('message')
    send_data = data.copy()
    send_type = data.get('type') - 1
    send_channel = data.get('channel') if 'channel' in data else 1
    send_strength = data.get('strength') if 'strength' in data else 1
    msg = f"strength-{send_channel}+{send_type}+{send_strength}"
    send_data['type'] = "msg"
    send_data['message'] = msg
    if mode != mode_r[2]:
        client = clients.get(target_Id)
        await client.send(json.dumps(send_data))
    else:
        for clientId, client in clients.items():
            if client_Id == clientId:
                continue
            await client.send(json.dumps(send_data))

# 处理类型4的消息
async def handler_type_4(websocket, data):
    error_data = check_bind_and_client(data)
    if error_data:
        await websocket.send(json.dumps(error_data))
        return
    client_Id = data.get('clientId')
    target_Id = data.get('targetId')
    message = data.get('message')
    client = clients.get(target_Id)
    send_data = {
        'type': 'bind',
        'clientId': client_Id,
        'targetId': target_Id,
        'message': message
    }
    await client.send(json.dumps(send_data))

# 处理客户端消息
async def handler_type_client_msg(websocket, data):
    error_data = check_bind_and_client(data)
    if error_data:
        await websocket.send(json.dumps(error_data))
        return
    if data.get('channel') is None:
        send_data = data.copy()
        send_data['type'] = "error"
        send_data['message'] = "406 - channel is empty"
        await websocket.send(json.dumps(send_data))
        log.info("客户端消息缺少channel字段")
        return
    client_Id = data.get('clientId')
    target_Id = data.get('targetId')
    message = data.get('message')
    send_time = data.get('time', punishmentDuration)
    send_data = data.copy()
    send_data['type'] = "msg"
    send_data['message'] = f'pulse-{message}'
    total_Sends = punishmentTime * send_time
    time_Space = 1 / punishmentTime
    channel = data['channel']
    if mode == mode_r[0] or mode == mode_r[1]:
        timer_Id_a = f'{target_Id}-{channel}'
        task_name = f'{target_Id}-{channel}'
    else:
        timer_Id_a = f'{client_Id}-{channel}'
        task_name = f'{client_Id}-{channel}'
    task_channel = {
        'A': '',
        'B': ''
    }
    if timer_Id_a in client_timers:
        log.info(f'通道{channel}覆盖消息发送中，总消息数：{total_Sends}持续时间：{send_time}')
        await websocket.send(f'当前通道{channel}有正在发送的消息，覆盖之前的消息')
        timer_Id = client_timers[timer_Id_a]
        # 清除计时器
        timer_Id.cancel()
        try:
            await timer_Id
        except asyncio.CancelledError:
            log.info(f'通道{timer_Id_a}任务关闭，消息重新覆盖')
        client_timers.pop(timer_Id_a)
        clear_Data = {
            'type': 'msg',
            'clientId': client_Id,
            'targetId': target_Id,
            'message': 'clear-1' if channel == "A" else 'clear-2'
        }
        # 延迟发送信息
        await asyncio.sleep(0.150)
        if mode == mode_r[2]:
            for target__id, target in clients.items():
                if target__id == client_Id:
                    continue
                await target.send(json.dumps(clear_Data))
                task_channel[task_name] = asyncio.create_task(
                    delay_send_msg(client_Id, websocket, target, send_data, total_Sends, time_Space, channel, timer_Id_a))
        else:
            target = clients.get(target_Id)
            task_channel[task_name] = asyncio.create_task(
                delay_send_msg(client_Id, websocket, target, send_data, total_Sends, time_Space, channel, timer_Id_a))
        log.info(f'通道{channel}消息发送中，总消息数：{total_Sends}持续时间：{send_time}')
    else:
        # 直接发送信息
        if mode == mode_r[2]:
            for target__id, target in clients.items():
                if target__id == client_Id:
                    continue
                task_channel[task_name] = asyncio.create_task(
                    delay_send_msg(client_Id, websocket, target, send_data, total_Sends, time_Space, channel, timer_Id_a))
        else:
            target = clients.get(target_Id)
            task_channel[task_name] = asyncio.create_task(
                delay_send_msg(client_Id, websocket, target, send_data, total_Sends, time_Space, channel, timer_Id_a))
        log.info(f'通道{channel}消息发送中，总消息数：{total_Sends}持续时间：{send_time}')

# 传入类型
type_handlers = {
    'bind': handler_type_bind,
    1: handler_type_123,
    2: handler_type_123,
    3: handler_type_123,
    4: handler_type_4,
    'clientMsg': handler_type_client_msg
}

# 主程序
async def server_main(websocket):
    global heartbeat_Interval
    # 生成标识符
    client_id = str(uuid.uuid4())
    log.info(f'新的 WebSocket 连接已建立，标识符为:{client_id}')
    # 将客户端标识符和WebSocket连接对象存入字典
    clients[client_id] = websocket
    if mode == mode_r[2] and client_1_n['id'] == "":
        client_1_n['id'] = client_id
        client_1_n['client'] = websocket
    # 构造绑定消息
    msg = {
        "type": "bind",
        "clientId": client_id,
        "message": "targetId",
        "targetId": ""
    }
    if mode == mode_r[1]:
        msg['targetId'] = target_n_1['id']
        msg["message"] = "OK"
    # 将字典转换成JSON字符串并发送
    await websocket.send(json.dumps(msg))
    try:
        if not heartbeat_Interval:
            asyncio.create_task(send_heartbeat())
            heartbeat_Interval = True
        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                # 如果消息不是有效的JSON，则发送错误响应
                response = {
                    'type': 'msg',
                    'clientId': '',
                    'targetId': '',
                    'message': '403'
                }
                await websocket.send(json.dumps(response))
                log.info('发现数据非json格式')
                continue
            if data['clientId'] not in clients and clients.get(data['targetId']) != websocket:
                response = {
                    'type': 'msg',
                    'clientId': '',
                    'targetId': '',
                    'message': '404'
                }
                await websocket.send(json.dumps(response))
                log.info("非法提交")
                return
            if 'type' in data and 'clientId' in data and 'message' in data and 'targetId' in data:
                a_type = data['type']
                if a_type in type_handlers:
                    await type_handlers[a_type](websocket, data)
                else:
                    client_Id = data.get('clientId')
                    target_Id = data.get('targetId')
                    if relations.get(client_Id) != target_Id:
                        send_data = {
                            'type': 'bind',
                            'clientId': client_Id,
                            'targetId': target_Id,
                            'message': '402'
                        }
                        await websocket.send(json.dumps(send_data))
                        return
                    if client_Id in clients:
                        client = clients.get(client_Id)
                        send_data = {
                            'type': a_type,
                            'clientId': client_Id,
                            'targetId': target_Id,
                            'message': data['message']
                        }
                        await client.send(json.dumps(send_data))
                    else:
                        send_data = {
                            'type': 'msg',
                            'clientId': client_Id,
                            'targetId': target_Id,
                            'message': '404'
                        }
                        await websocket.send(json.dumps(send_data))
    except websockets.exceptions.ConnectionClosedOK:
        pass
    except websockets.exceptions.ConnectionClosedError:
        await on_connection_closed(websocket)
    except websockets.exceptions.InvalidStatusCode:
        log.error("Received an invalid status code from the server.")
    except websockets.exceptions.InvalidURI:
        log.error("The provided URI is invalid.")
# 连接关闭操作
async def on_connection_closed(websocket):
    client_Id = ''
    for key, value in clients.items():
        if value == websocket:
            # 拿到断开的客户端id
            client_Id = key
            break  # 找到后退出循环
    if client_Id.strip() == '':
        return
    log.info(f'WebSocket 连接已关闭 断开的client id:{client_Id}')
    if client_Id in relations.keys() or client_Id in relations.values():
        keys_to_remove = []
        for key, value in relations.copy().items():
            if key == client_Id:
                appid = relations.get(key)
                appClient = clients.get(appid)
                send_data = {
                    'type': 'break',
                    'clientId': client_Id,
                    'targetId': appid,
                    'message': '209'
                }
                try:
                    await appClient.send(json.dumps(send_data))
                    await appClient.close(code=1000, reason='Close Connencent')
                except Exception as e:
                    log.error(f"关闭{appid}连接时出错: {e}")
                keys_to_remove.append(key)
                log.info(f'对方掉线，关闭{appid}')
            elif value == client_Id:
                webClient = clients.get(key)
                send_data = {
                    'type': 'break',
                    'clientId': key,
                    'targetId': client_Id,
                    'message': '209'
                }
                try:
                    # 补充完整字符串
                    await webClient.send(json.dumps(send_data))
                    await webClient.close(code=1000, reason='Close Connencent')
                except Exception as e:
                    log.error(f"关闭{key}连接时出错: {e}")
                keys_to_remove.append(key)
                log.info(f'对方掉线，关闭{client_Id}')
        for key in keys_to_remove:
            del relations[key]
            clients.pop(key)
    else:
        clients.pop(client_Id)
    log.info(f"已清除{client_Id},当前len：{len(clients)}")

if __name__ == "__main__":
