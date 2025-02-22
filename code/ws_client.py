# -*- coding: utf-8 -*-
import asyncio
import websockets
import json
import socket
import qrcode
import log

log = log.HandleLog()

# 全局变量
connection_id = ""
target_ws_id = ""
fangdou = 0.5  # 500 毫秒防抖
fangdou_set_timeout = None
follow_a_strength = False
follow_b_strength = False
ws_conn = None
# 获取当前机器的 IP 地址
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(('8.8.8.8', 80))
    local_ip = s.getsockname()[0]
except Exception:
    local_ip = '127.0.0.1'
finally:
    s.close()

feed_back_msg = {
    "feedback-0": "A通道：○",
    "feedback-1": "A通道：△",
    "feedback-2": "A通道：□",
    "feedback-3": "A通道：☆",
    "feedback-4": "A通道：⬡",
    "feedback-5": "B通道：○",
    "feedback-6": "B通道：△",
    "feedback-7": "B通道：□",
    "feedback-8": "B通道：☆",
    "feedback-9": "B通道：⬡"
}

wave_data = {
    "1": '["0A0A0A0A00000000","0A0A0A0A0A0A0A0A","0A0A0A0A14141414","0A0A0A0A1E1E1E1E","0A0A0A0A28282828","0A0A0A0A32323232","0A0A0A0A3C3C3C3C","0A0A0A0A46464646","0A0A0A0A50505050","0A0A0A0A5A5A5A5A","0A0A0A0A64646464"]',
    "2": '["0A0A0A0A00000000","0D0D0D0D0F0F0F0F","101010101E1E1E1E","1313131332323232","1616161641414141","1A1A1A1A50505050","1D1D1D1D64646464","202020205A5A5A5A","2323232350505050","262626264B4B4B4B","2A2A2A2A41414141"]',
    "3": '["4A4A4A4A64646464","4545454564646464","4040404064646464","3B3B3B3B64646464","3636363664646464","3232323264646464","2D2D2D2D64646464","2828282864646464","2323232364646464","1E1E1E1E64646464","1A1A1A1A64646464"]'
}


async def connect_ws():
    """
    建立 WebSocket 连接并处理消息
    """
    global ws_conn, connection_id
    log.info(f"ws:// {local_ip}:8888")
    try:
        ws_conn = await websockets.connect(f"ws://{local_ip}:8888")

        log.info("WebSocket连接已建立")
        async for message in ws_conn:
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                log.info(message)
                continue

            # 根据 message.type 进行不同的处理
            if message["type"] == 'bind':
                if not message["targetId"]:
                    # 初次连接获取网页wsid
                    connection_id = message["clientId"]
                    log.info(f"收到clientId：{connection_id}")
                else:
                    if message["clientId"] != connection_id:
                        log.info(f'收到不正确的target消息{message["message"]}')
                        return
                    global target_ws_id
                    target_ws_id = message["targetId"]
                    log.info(f"收到targetId: {target_ws_id} msg: {message['message']}")
            elif message["type"] == 'break':
                # 对方断开
                if message["targetId"] != target_ws_id:
                    return
                log.info(f"对方已断开，code:{message['message']}")
                break
            elif message["type"] == 'error':
                if message["targetId"] != target_ws_id:
                    return
                log.info(message)
            elif message["type"] == 'msg':
                if "strength" in message["message"]:
                    import re
                    numbers = [int(i) for i in re.findall(r'\d+', message["message"])]
                    log.info(f"通道A强度: {numbers[0]}, 通道B强度: {numbers[1]}, 软上限A: {numbers[2]}, 软上限B: {numbers[3]}")

                    global follow_a_strength, follow_b_strength
                    if follow_a_strength and numbers[2] != numbers[0]:
                        data1 = {"type": 4, "message": f"strength-1+2+{numbers[2]}"}
                        send_ws_msg(data1)
                    if follow_b_strength and numbers[3] != numbers[1]:
                        data2 = {"type": 4, "message": f"strength-2+2+{numbers[3]}"}
                        send_ws_msg(data2)
                elif "feedback" in message["message"]:
                    log.info(feed_back_msg[message["message"]])
            elif message["type"] == 'heartbeat':
                # 心跳包
                log.info("收到心跳")
            else:
                log.info(f"收到其他消息：{message}")
    except Exception as e:
        log.info(f"WebSocket连接发生错误: {e}")


def create_QR():
    """
    生成clientID的二维码并显示
    """
    QR_test =f"https://www.dungeon-lab.com/app-download.php#DGLAB-SOCKET##{local_ip}:8888/{connection_id}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    qr.add_data(QR_test)
    qr.make(fit=True)

    # 创建二维码图像
    img = qr.make_image(fill_color="black", back_color="white")
    img.show()
def send_ws_msg(message_obj):
    """
    发送 WebSocket 消息
    """
    global ws_conn, connection_id, target_ws_id
    message_obj["clientId"] = connection_id
    message_obj["targetId"] = target_ws_id
    if "type" not in message_obj:
        message_obj["type"] = "msg"
    asyncio.ensure_future(ws_conn.send(json.dumps(message_obj)))


def toggle_switch(id):
    """
    切换开关状态
    """
    global follow_a_strength, follow_b_strength
    if id == 'toggle1':
        follow_a_strength = not follow_a_strength
    else:
        follow_b_strength = not follow_b_strength


def add_or_increase(type, channel_index, strength):
    """
    增加或减少通道强度
    """
    data = {"type": type, "strength": strength, "message": "set channel", "channel": channel_index}
    send_ws_msg(data)


def clear_ab(channel_index):
    """
    清除指定通道
    """
    data = {"type": 4, "message": f"clear-{channel_index}"}
    send_ws_msg(data)


def auto_add_strength(channel_id, add_strength, current_strength, follow):
    """
    自动增加通道强度
    """
    if not follow:
        set_to = add_strength + current_strength
        if add_strength > 0:
            data = {"type": 4, "message": f"strength-{channel_id}+2+{set_to}"}
            send_ws_msg(data)


def send_custom_msg(select_a, select_b, time_a, time_b, failed_a, failed_b):
    """
    发送自定义消息
    """
    global fangdou_set_timeout
    if fangdou_set_timeout:
        return

    auto_add_strength(1, failed_a, 0, follow_a_strength)
    auto_add_strength(2, failed_b, 0, follow_b_strength)

    msg1 = f"A:{wave_data[select_a]}"
    msg2 = f"B:{wave_data[select_b]}"

    data_a = {"type": "clientMsg", "message": msg1, "time": time_a, "channel": "A"}
    data_b = {"type": "clientMsg", "message": msg2, "time": time_b, "channel": "B"}
    send_ws_msg(data_a)
    send_ws_msg(data_b)

    fangdou_set_timeout = asyncio.get_event_loop().call_later(fangdou, lambda: setattr(globals(), 'fangdou_set_timeout', None))


def connect_or_disconn():
    """
    连接或断开 WebSocket 连接
    """
    global ws_conn, target_ws_id
    if ws_conn and not target_ws_id:
        return
    else:
        if ws_conn:
            asyncio.ensure_future(ws_conn.close())
        log.info("已断开连接")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.create_task(connect_ws())
        loop.run_forever()
    except KeyboardInterrupt:
        connect_or_disconn()
        loop.close()