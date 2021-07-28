import json
import os
import re
import sys
import time
from threading import Thread

import requests
from PyQt5 import QtWidgets, QtCore

import Config
import Log
from uic.UI_MainDownloader import Ui_MainWindow
import Icon

HOST = "http://www.imomoe.la"


class Animation:
    def __init__(self):
        self.title = ""
        self.videoList = []
        self.selection = 0
        self.checkBoxItems = []  # 集数下载复选框列表
        pass


class DownloaderFrame(QtWidgets.QMainWindow):
    """下载器窗体类"""

    showSelectionSignal = QtCore.pyqtSignal(int)
    lineEditRecordSignal = QtCore.pyqtSignal()
    showMsgBoxSignal = QtCore.pyqtSignal(int)
    proxies = {"http": Config.setting["PROXY"], "https": Config.setting["PROXY"]}

    def __init__(self):
        super(DownloaderFrame, self).__init__()

        self.ui = Ui_MainWindow()
        self.icon = Icon.getIcon()
        self.lineEdit = QtWidgets.QLineEdit()
        self.animation = Animation()
        self.recoding = {}

        self.ui.setupUi(self)
        self.setWindowIcon(self.icon)
        self.ui.downloadButton.setEnabled(False)
        self.setLineEdit()
        self.lineEdit.returnPressed.connect(self.on_queryButton_clicked)
        self.showSelectionSignal.connect(self.showSelection)
        self.lineEditRecordSignal.connect(self.lineEditRecord)
        self.showMsgBoxSignal.connect(self.showMsgBox)
        self.ui.treeWidget.header().setSectionsClickable(True)
        self.ui.treeWidget.header().sectionClicked.connect(self.on_treeWidget_header_clicked)
        pass

    @QtCore.pyqtSlot()
    def on_queryButton_clicked(self):
        inputUrl = self.lineEdit.text()  # http://www.imomoe.la/player/8006-0-0.html
        if len(inputUrl) != 0:
            self.ui.videoNameLabel.setText("正在查询中，请稍候...")
            if inputUrl.startswith("www"):
                inputUrl = "http://" + inputUrl
            queryThread = Thread(name='Query Thread', target=self.query, args=(inputUrl,), daemon=True)
            queryThread.start()
        pass

    def query(self, url):
        try:
            rps = requests.get(url, proxies=self.proxies)
            rps.encoding = "gb2312"
            html = rps.text

            self.animation.title = re.findall('var xTitle=\'.+\';</script>', html)[0].split('\'')[1]

            videoJsonUrl = HOST + re.findall('/playdata/\\d+/\\d+.js\\?\\d+.\\d+', html)[0]
            rps = requests.get(videoJsonUrl, proxies=self.proxies)
            rps.encoding = "gb2312"
            videoJsonHtml = rps.text
            videoJsonStr = re.split('Json=|,urlinfo', videoJsonHtml)[1]
            videoJsonStr = videoJsonStr.replace('\'', '\"')
            videoList = json.loads(videoJsonStr)
            for x in videoList:
                urls = {}
                for y in x[1]:
                    obj = y.split("$")
                    urls[obj[0]] = obj[1]
                self.animation.videoList.append(urls)
            self.lineEditRecordSignal.emit()
            self.showSelectionSignal.emit(-1)
        except requests.exceptions.RequestException as ex:
            msg = {
                "ErrorType": type(ex),
                "Title": "无",
                "Section": "无",
                "Event": "查询失败",
                "TextOfLineEdit": self.lineEdit.text(),
                "Reason": "输入了错误的网址"
            }
            Log.writeLog(time.strftime("%Y-%m-%d"), msg)
            self.showMsgBoxSignal.emit(0)
        except Exception as ex:
            msg = {
                "ErrorType": type(ex),
                "Title": "无",
                "Section": "无",
                "Event": "查询失败",
                "TextOfLineEdit": self.lineEdit.text()
            }
            Log.writeLog(time.strftime("%Y-%m-%d"), msg)
        pass

    @QtCore.pyqtSlot(int)
    def showSelection(self, index: int):
        """
        显示选项

        :param index: 类型为int。默认值为-1，根据其值来选择数据源。
        :return: 无
        """
        if index == -1:
            self.animation.selection = 0
            videoUrls = self.animation.videoList[0]

            self.ui.videoNameLabel.setText(self.animation.title)

            self.ui.videoSourceComboBox.clear()
            for i in range(0, len(self.animation.videoList)):
                self.ui.videoSourceComboBox.addItem(str(i + 1))
        else:
            self.animation.selection = index
            videoUrls = self.animation.videoList[index]

        self.animation.checkBoxItems.clear()
        self.ui.treeWidget.clear()
        for epi in videoUrls:
            treeItem = QtWidgets.QTreeWidgetItem()
            treeItem.setTextAlignment(3, QtCore.Qt.AlignCenter)
            treeItem.setTextAlignment(1, QtCore.Qt.AlignCenter)
            self.ui.treeWidget.addTopLevelItem(treeItem)

            checkBox = QtWidgets.QCheckBox()
            hLayout = QtWidgets.QHBoxLayout()
            hLayout.addWidget(checkBox, alignment=QtCore.Qt.AlignCenter)
            itemCheckBoxWidget = QtWidgets.QWidget()
            itemCheckBoxWidget.setLayout(hLayout)
            self.ui.treeWidget.setItemWidget(treeItem, 0, itemCheckBoxWidget)
            self.animation.checkBoxItems.append(checkBox)
            checkBox.stateChanged.connect(self.change_treeHeader_0_text)  #

            treeItem.setText(1, epi)

            progressBar = QtWidgets.QProgressBar()
            progressBar.setValue(0)
            self.ui.treeWidget.setItemWidget(treeItem, 2, progressBar)

        self.ui.downloadButton.setEnabled(True)
        pass

    @QtCore.pyqtSlot(int)
    def on_treeWidget_header_clicked(self, index):
        if index != 0:
            return
        header = self.ui.treeWidget.headerItem()
        if header.text(0) == "全选":
            for item in self.animation.checkBoxItems:
                item.setCheckState(QtCore.Qt.Checked)
            header.setText(0, "取消")
        elif header.text(0) == "取消":
            for item in self.animation.checkBoxItems:
                item.setCheckState(QtCore.Qt.Unchecked)
            header.setText(0, "全选")
        elif header.text(0) == "反选":
            for item in self.animation.checkBoxItems:
                if item.isChecked():
                    item.setChecked(False)
                else:
                    item.setChecked(True)
        pass

    @QtCore.pyqtSlot(str)
    def on_videoSourceComboBox_activated(self, text):
        self.showSelectionSignal.emit(int(text) - 1)
        self.ui.treeWidget.headerItem().setText(0, "全选")
        pass

    @QtCore.pyqtSlot()
    def on_downloadButton_clicked(self):

        for i in range(0, self.ui.treeWidget.topLevelItemCount()):
            if self.animation.checkBoxItems[i].isChecked():
                self.ui.treeWidget.topLevelItem(i).setText(3, "等待中")
        pass

    @QtCore.pyqtSlot(int, int)
    def on_treeWidget_progressBar_setValue(self, index, percentage):
        treeItem = self.ui.treeWidget.topLevelItem(index)
        self.ui.treeWidget.itemWidget(treeItem, 2).setValue(percentage)
        pass

    @QtCore.pyqtSlot(int, str)
    def on_treeWidget_itemStatus_change(self, index, status):
        self.ui.treeWidget.topLevelItem(index).setText(3, status)
        pass

    @QtCore.pyqtSlot()
    def change_treeHeader_0_text(self):
        statue = 0
        for item in self.animation.checkBoxItems:
            if item.isChecked():
                statue += 1
        if statue == 0:
            self.ui.treeWidget.headerItem().setText(0, "全选")
        elif statue == len(self.animation.checkBoxItems):
            self.ui.treeWidget.headerItem().setText(0, "取消")
        else:
            self.ui.treeWidget.headerItem().setText(0, "反选")
        pass

    @QtCore.pyqtSlot()
    def on_downloadPathAction_triggered(self):
        DOWNLOAD_DIR = QtWidgets.QFileDialog.getExistingDirectory(self, "选择保存路径", Config.setting['DOWNLOAD_DIR'])
        if DOWNLOAD_DIR != '':
            Config.setting['DOWNLOAD_DIR'] = DOWNLOAD_DIR
            Config.saveSetting()
        pass

    @QtCore.pyqtSlot()
    def on_exitAction_triggered(self):
        QtWidgets.QApplication.exit(0)
        pass

    @QtCore.pyqtSlot()
    def on_aboutAction_triggered(self):
        QtWidgets.QMessageBox.about(self, "关于 樱花动漫下载器", "\n作者：DevilSpider")
        pass

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def on_treeWidget_itemDoubleClicked(self, treeWidgetItem):
        index = self.ui.treeWidget.indexOfTopLevelItem(treeWidgetItem)
        if self.animation.checkBoxItems[index].isChecked():
            self.animation.checkBoxItems[index].setChecked(False)
        else:
            self.animation.checkBoxItems[index].setChecked(True)
        pass

    def setLineEdit(self):
        self.lineEdit.setClearButtonEnabled(True)
        self.ui.lineEditComboBox.setLineEdit(self.lineEdit)
        recordingPath = Config.setting["RECORDING_PATH"]
        if os.path.lexists(recordingPath):
            with open(recordingPath, "r", encoding="utf-8")as reader:
                self.recoding = json.load(reader)
            recordingList = [""]
            for key in self.recoding:
                recordingList.append(key)
            self.ui.lineEditComboBox.addItems(recordingList)
            pass

    @QtCore.pyqtSlot(str)
    def on_lineEditComboBox_activated(self, name):
        if name in self.recoding:
            self.lineEdit.setText(self.recoding[name])
        pass

    @QtCore.pyqtSlot()
    def lineEditRecord(self):
        isDifferent = False
        if self.animation.title not in self.recoding:
            self.recoding[self.animation.title] = self.lineEdit.text()
            isDifferent = True
        elif self.recoding[self.animation.title] != self.lineEdit.text():
            self.recoding[self.animation.title] = self.lineEdit.text()
            isDifferent = True
        if isDifferent:
            with open(Config.setting["RECORDING_PATH"], "w", encoding='utf8') as writer:
                json.dump(self.recoding, writer, indent="\t")
        pass

    @QtCore.pyqtSlot(int)
    def showMsgBox(self, index):
        if index == 0:
            msgBox = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, "错误", "请输入正确的网址")
            msgBox.setWindowIcon(self.icon)
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Ok)
            msgBox.exec_()
        pass

    pass


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    downloader = DownloaderFrame()
    downloader.show()
    sys.exit(app.exec_())
