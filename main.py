# -*- coding: utf-8 -*-
import sys
import warnings
# 忽略 DeprecationWarning 警告
warnings.filterwarnings("ignore", category=DeprecationWarning)
# PyQt5 中使用的基本控件都在 PyQt5.QtWidgets 模块中
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import Qt
# 导入 designer 工具生成的 login 模块
from gui import Ui_Dialog
from datetime import datetime
import log
import ws_client
import ws_server
import socket

log = log.HandleLog()
openserver = None
# 获取当前机器的 IP 地址
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(('8.8.8.8', 80))
    local_ip = s.getsockname()[0]
except Exception:
    local_ip = '127.0.0.1'
finally:
    s.close()

class MyMainForm(QDialog, Ui_Dialog):
    def __init__(self, parent=None):
        super(MyMainForm, self).__init__(parent)
        self.setupUi(self)
        self.textBrowser.setText("郊狼惩罚器启动成功,版本 V0.1")
        self.setWindowTitle("郊狼惩罚器")
        # 禁用最大化功能
        flags = self.windowFlags()
        flags = flags & ~Qt.WindowMaximizeButtonHint
        self.setWindowFlags(flags)

        # 为按钮绑定事件处理函数，并添加调试信息
        self._connect_button(self.openserver, self.on_openserver_clicked, "openserver")
        self._connect_button(self.displayQR, self.on_displayQR_clicked, "displayQR")
        self._connect_button(self.plugin_config, self.on_plugin_config_clicked, "plugin_config")
        self._connect_button(self.pushButton, self.on_pushButton_clicked, "pushButton")
        self._connect_button(self.run_plugin, self.on_run_plugin_clicked, "run_plugin")
        self._connect_button(self.waveform_generator, self.on_waveform_generator_clicked, "waveform_generator")
        self._connect_button(self.clos, self.on_clos_clicked, "clos")

    def _connect_button(self, button, slot, button_name):
        try:
            button.clicked.disconnect()
        except TypeError:
            pass  # 如果没有连接，会抛出 TypeError 异常，忽略即可
        print(f"正在连接 {button_name} 按钮的 clicked 信号到相应槽函数...")
        button.clicked.connect(slot)
        print(f"{button_name} 按钮的 clicked 信号连接完成")

    def log_text(self, text):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output = f"[{current_time}] {text}"
        self.textBrowser.append(output)

    def on_openserver_clicked(self):
        log.info("开启服务端按钮被点击")

        ws_server.run_server()
        self.log_text(f"WebSocket 服务器已启动，监听地址: {local_ip}:8888")



    def on_displayQR_clicked(self):
        log.info("显示二维码按钮被点击")
        # 在这里添加显示二维码的具体逻辑

    def on_plugin_config_clicked(self):
        log.info("插件配置按钮被点击")
        # 在这里添加插件配置的具体逻辑

    def on_pushButton_clicked(self):
        log.info("插件市场按钮被点击")
        # 在这里添加插件市场的具体逻辑

    def on_run_plugin_clicked(self):
        log.info("启动插件按钮被点击")
        # 在这里添加启动插件的具体逻辑

    def on_waveform_generator_clicked(self):
        log.info("波形生成器按钮被点击")
        # 在这里添加波形生成器的具体逻辑

    def on_clos_clicked(self):
        # 禁用关闭按钮，防止重复点击
        self.clos.setEnabled(False)
        # 弹出确认对话框，询问用户是否真的要关闭程序
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, '确认关闭', '你确定要关闭程序吗？',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            log.info("用户确认关闭程序")
            self.log_text("用户确认关闭程序")
            # 这里可以添加更多在关闭窗口前需要执行的操作，比如释放资源、保存数据等
            self.close()
        else:
            log.info("用户取消关闭程序")
            self.log_text("用户取消关闭程序")
            # 如果用户取消关闭，恢复按钮可用状态
            self.clos.setEnabled(True)


if __name__ == "__main__":
    # 固定的，PyQt5 程序都需要 QApplication 对象。sys.argv 是命令行参数列表，确保程序可以双击运行
    app = QApplication(sys.argv)
    # 初始化
    myWin = MyMainForm()
    # 将窗口控件显示在屏幕上
    myWin.show()
    # 程序运行，sys.exit 方法确保程序完整退出。
    sys.exit(app.exec_())

if __name__ == "__main__":
    # 固定的，PyQt5 程序都需要 QApplication 对象。sys.argv 是命令行参数列表，确保程序可以双击运行
    app = QApplication(sys.argv)
    # 初始化
    myWin = MyMainForm()
    # 将窗口控件显示在屏幕上
    myWin.show()
    # 程序运行，sys.exit 方法确保程序完整退出。
    sys.exit(app.exec_())