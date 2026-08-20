import sys
import os

# 修复 Qt 在中文路径下找不到 platform plugin 的问题
qt_plugin_path = os.path.join(os.path.dirname(__file__), "venv", "Lib", "site-packages", "PyQt5", "Qt5", "plugins")
if os.path.exists(qt_plugin_path):
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(qt_plugin_path, "platforms")

from PyQt5 import QtWidgets
from UI.MainWindow import MainWindow_Ui

if __name__ == "__main__":
    # 初始化
    app = QtWidgets.QApplication(sys.argv)
    main = QtWidgets.QMainWindow()
    ui = MainWindow_Ui()
    ui.setupUi(main)
    main.show()
    # 启动监听
    ui.active()
    # 主窗体循环
    app.exec_()

