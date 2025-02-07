import asyncio
import websockets
import uuid
import socket
import threading

# 储存已连接的用户及其标识
clients = {}
# 存储消息关系
relations = {}
# 默认发送时间（秒）
punishment_duration = 5
# 默认一秒发送次数
punishment_time = 1
# 存储客户端和发送计时器关系
client_timers = {}

# 定义心跳消息
heartbeat_msg = {
    "type": "heartbeat",
    "clientId": "",
    "targetId": "",
    "message": "200"
}


async def delay_send_msg(client_id, client, target, send_data, total_sends, time_space, channel):
    await target.send(send_data)
    total_sends -= 1
    if total_sends > 0:
        async def send_loop():
            nonlocal total_sends
            while total_sends > 0:
                await asyncio.sleep(time_space)
                await target.send(send_data)
                total_sends -= 1
            await client.send('发送完毕')
            client_timers.pop(f'{client_id}-{channel}', None)

        task = asyncio.create_task(send_loop())
        client_timers[f'{client_id}-{channel}'] = task


async def handle_connection(ws, path):
    # 生成唯一的标识符
    client_id = str(uuid.uuid4())
    print(f'新的 WebSocket 连接已建立，标识符为: {client_id}')
    clients[client_id] = ws
    # 发送标识符给客户端
    await ws.send(f'{{"type": "bind", "clientId": "{client_id}", "message": "targetId", "targetId": ""}}')

    async for message in ws:
        try:
            import json
            data = json.loads(message)
        except json.JSONDecodeError:
            await ws.send(f'{{"type": "msg", "clientId": "", "targetId": "", "message": "403"}}')
            continue

        if data.get('clientId') not in clients or data.get('targetId') not in clients:
            await ws.send(f'{{"type": "msg", "clientId": "", "targetId": "", "message": "404"}}')
            continue

        if all(key in data for key in ['type', 'clientId', 'message', 'targetId']):
            client_id = data['clientId']
            target_id = data['targetId']
            msg = data['message']
            msg_type = data['type']

            if msg_type == "bind":
                if client_id in clients and target_id in clients:
                    if client_id not in relations and target_id not in relations and target_id not in relations.values():
                        relations[client_id] = target_id
                        send_data = f'{{"type": "bind", "clientId": "{client_id}", "targetId": "{target_id}", "message": "200"}}'
                        await ws.send(send_data)
                        await clients[client_id].send(send_data)
                    else:
                        await ws.send(f'{{"type": "bind", "clientId": "{client_id}", "targetId": "{target_id}", "message": "400"}}')
                else:
                    await ws.send(f'{{"type": "bind", "clientId": "{client_id}", "targetId": "{target_id}", "message": "401"}}')
            elif msg_type in [1, 2, 3]:
                if relations.get(client_id) != target_id:
                    await ws.send(f'{{"type": "bind", "clientId": "{client_id}", "targetId": "{target_id}", "message": "402"}}')
                    continue
                if target_id in clients:
                    send_type = msg_type - 1
                    send_channel = data.get('channel', 1)
                    send_strength = data.get('strength', 1) if msg_type >= 3 else 1
                    msg = f"strength-{send_channel}+{send_type}+{send_strength}"
                    send_data = f'{{"type": "msg", "clientId": "{client_id}", "targetId": "{target_id}", "message": "{msg}"}}'
                    await clients[target_id].send(send_data)
            elif msg_type == 4:
                if relations.get(client_id) != target_id:
                    await ws.send(f'{{"type": "bind", "clientId": "{client_id}", "targetId": "{target_id}", "message": "402"}}')
                    continue
                if target_id in clients:
                    send_data = f'{{"type": "msg", "clientId": "{client_id}", "targetId": "{target_id}", "message": "{msg}"}}'
                    await clients[target_id].send(send_data)
            elif msg_type == "clientMsg":
                if relations.get(client_id) != target_id:
                    await ws.send(f'{{"type": "bind", "clientId": "{client_id}", "targetId": "{target_id}", "message": "402"}}')
                    continue
                if 'channel' not in data:
                    await ws.send(f'{{"type": "error", "clientId": "{client_id}", "targetId": "{target_id}", "message": "406-channel is empty"}}')
                    continue
                if target_id in clients:
                    send_time = data.get('time', punishment_duration)
                    target = clients[target_id]
                    send_data = f'{{"type": "msg", "clientId": "{client_id}", "targetId": "{target_id}", "message": "pulse-{msg}"}}'
                    total_sends = punishment_time * send_time
                    time_space = 1 / punishment_time

                    channel = data['channel']
                    if f'{client_id}-{channel}' in client_timers:
                        print(f"通道{channel}覆盖消息发送中，总消息数：{total_sends}持续时间A：{send_time}")
                        await ws.send(f"当前通道{channel}有正在发送的消息，覆盖之前的消息")
                        task = client_timers[f'{client_id}-{channel}']
                        task.cancel()
                        client_timers.pop(f'{client_id}-{channel}')

                        if channel == "A":
                            clear_data = f'{{"clientId": "{client_id}", "targetId": "{target_id}", "message": "clear-1", "type": "msg"}}'
                            await target.send(clear_data)
                        elif channel == "B":
                            clear_data = f'{{"clientId": "{client_id}", "targetId": "{target_id}", "message": "clear-2", "type": "msg"}}'
                            await target.send(clear_data)

                        await asyncio.sleep(0.15)
                        await delay_send_msg(client_id, ws, target, send_data, total_sends, time_space, channel)
                    else:
                        print(f"通道{channel}消息发送中，总消息数：{total_sends}持续时间：{send_time}")
                        await delay_send_msg(client_id, ws, target, send_data, total_sends, time_space, channel)
                else:
                    print(f"未找到匹配的客户端，clientId: {client_id}")
                    await ws.send(f'{{"type": "msg", "clientId": "{client_id}", "targetId": "{target_id}", "message": "404"}}')
            else:
                if relations.get(client_id) != target_id:
                    await ws.send(f'{{"type": "bind", "clientId": "{client_id}", "targetId": "{target_id}", "message": "402"}}')
                    continue
                if client_id in clients:
                    send_data = f'{{"type": "{msg_type}", "clientId": "{client_id}", "targetId": "{target_id}", "message": "{msg}"}}'
                    await clients[client_id].send(send_data)
                else:
                    await ws.send(f'{{"type": "msg", "clientId": "{client_id}", "targetId": "{target_id}", "message": "404"}}')


async def heartbeat():
    while True:
        if clients:
            print(len(relations), len(clients), f'发送心跳消息：{asyncio.get_running_loop().time()}')
            for client_id, client in clients.items():
                heartbeat_msg["clientId"] = client_id
                heartbeat_msg["targetId"] = relations.get(client_id, "")
                await client.send(str(heartbeat_msg).replace("'", '"'))
        await asyncio.sleep(60)


async def start_websocket_server():
    # 获取当前机器的 IP 地址
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()

    server = await websockets.serve(handle_connection, local_ip, 8888)
    asyncio.create_task(heartbeat())
    print(f"WebSocket 服务器已启动，监听地址: {local_ip}:8888")
    await server.wait_closed()


def run_server():
    asyncio.run(start_websocket_server())


if __name__ == "__main__":
    # 启动服务器线程
    server_thread = threading.Thread(target=run_server)
    server_thread.start()

    # 这里可以添加其他逻辑
    # 如果你想让主线程等待服务器线程结束，可以使用 server_thread.join()
    server_thread.join()