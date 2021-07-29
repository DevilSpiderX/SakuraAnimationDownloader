import json
import os
import re
import shutil
import sys
import time
from threading import Thread

import requests
from PyQt5 import QtWidgets, QtCore

import Config
import Log
from uic.UI_MainDownloader import Ui_MainWindow
import Icon
from Executor import ThreadPoolExecutor

HOST = "http://www.imomoe.la"


class Animation:
    def __init__(self):
        self.title = ""
        self.videoList = []
        self.checkBoxItems = []  # 集数下载复选框列表
        self.selection = 0
        self.selectedUrls = {}
        self.status = []  # -1：未选中，0：等待中，1：下载中，2：下载完成，3：下载失败
        pass

    def select(self, index: int):
        self.selection = index
        self.selectedUrls = self.videoList[index]
        pass

    def isDone(self, index: int) -> bool:
        if self.status[index] == 2 or self.status[index] == 3:
            return True
        else:
            return False


class DownloaderFrame(QtWidgets.QMainWindow):
    """下载器窗体类"""

    showSelectionSignal = QtCore.pyqtSignal(int)
    inputLineEditRecordSignal = QtCore.pyqtSignal()
    showMsgBoxSignal = QtCore.pyqtSignal(int)
    treeItemPercentageSignal = QtCore.pyqtSignal(int, int)
    treeItemStatusSignal = QtCore.pyqtSignal(int, str)
    proxies = {"http": Config.setting["PROXY"], "https": Config.setting["PROXY"]}

    def __init__(self):
        super(DownloaderFrame, self).__init__()

        self.ui = Ui_MainWindow()
        self.icon = Icon.getIcon()
        self.inputLineEdit = QtWidgets.QLineEdit()
        self.animation = Animation()
        self.recoding = {}
        self.executor = ThreadPoolExecutor(Config.setting["MAX_NUM_PARALLEL_DOWNLOAD"])

        self.ui.setupUi(self)
        self.setWindowIcon(self.icon)
        self.ui.downloadButton.setEnabled(False)
        self.initInputLineEdit()
        self.inputLineEdit.returnPressed.connect(self.on_queryButton_clicked)
        self.showSelectionSignal.connect(self.showSelection)
        self.inputLineEditRecordSignal.connect(self.inputLineEditRecord)
        self.showMsgBoxSignal.connect(self.showMsgBox)
        self.ui.treeWidget.header().setSectionsClickable(True)
        self.ui.treeWidget.header().sectionClicked.connect(self.on_treeWidget_header_clicked)
        self.treeItemPercentageSignal.connect(self.on_treeWidget_progressBar_setValue)
        self.treeItemStatusSignal.connect(self.on_treeWidget_itemStatus_change)
        self.executor.start()
        pass

    def query(self, url):
        try:
            rps = requests.get(url, proxies=self.proxies)
            rps.encoding = "gb2312"
            html = rps.text

            self.animation.title = re.findall('var xTitle=\'.+\';</script>', html)[0].split('\'')[1]
            self.animation.videoList.clear()

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
            self.inputLineEditRecordSignal.emit()
            self.showSelectionSignal.emit(-1)
        except requests.exceptions.RequestException as ex:
            msg = {
                "ErrorType": type(ex),
                "Title": "无",
                "Section": "无",
                "Event": "查询失败",
                "TextOfLineEdit": self.inputLineEdit.text(),
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
                "TextOfLineEdit": self.inputLineEdit.text()
            }
            Log.writeLog(time.strftime("%Y-%m-%d"), msg)
        pass

    def initInputLineEdit(self):
        self.inputLineEdit.setClearButtonEnabled(True)
        self.ui.lineEditComboBox.setLineEdit(self.inputLineEdit)
        recordingPath = Config.setting["RECORDING_PATH"]
        if os.path.lexists(recordingPath):
            with open(recordingPath, "r", encoding="utf-8") as reader:
                self.recoding = json.load(reader)
            recordingList = [""]
            for key in self.recoding:
                recordingList.append(key)
            self.ui.lineEditComboBox.addItems(recordingList)
            pass

    def download(self, index: int):
        title = self.animation.title
        episode = list(self.animation.selectedUrls.keys())[index]
        url = self.animation.selectedUrls[episode]
        print(title + "：" + episode + "开始下载")
        self.animation.status[index] = 1
        DOWNLOAD_DIR = os.path.join(Config.setting["DOWNLOAD_DIR"], title)
        DOWNLOAD_PATH = os.path.join(DOWNLOAD_DIR, episode + ".mp4")
        TEMP_DIR = os.path.join(Config.setting["TEMP_DIR"], title)
        TEMP_PATH = os.path.join(TEMP_DIR, episode + ".temp")
        try:
            if not os.path.lexists(Config.setting["DOWNLOAD_DIR"]):
                os.mkdir(Config.setting["DOWNLOAD_DIR"])
            if not os.path.lexists(DOWNLOAD_DIR):
                os.mkdir(DOWNLOAD_DIR)
            if not os.path.lexists(Config.setting["TEMP_DIR"]):
                os.mkdir(Config.setting["TEMP_DIR"])
            if not os.path.lexists(TEMP_DIR):
                os.mkdir(TEMP_DIR)

            r = requests.get(url, stream=True, headers=Config.REQUEST_HEADERS, proxies=self.proxies)

            allSize = int(r.headers.get('Content-Length'))

            showSizeThread = Thread(name=title + "-" + episode + "-Size", target=self.showPercentage,
                                    args=(index, allSize))

            with open(TEMP_PATH, "wb") as f:
                showSizeThread.start()
                for chunk in r.iter_content(chunk_size=1024):  # 这样就可以下载一定大小就写入文件
                    if chunk:
                        f.write(chunk)
            shutil.copyfile(TEMP_PATH, DOWNLOAD_PATH)
            os.remove(TEMP_PATH)
            print(title + "：" + episode + " 下载完成")
            self.animation.status[index] = 2
        except BaseException as ex:
            print(title + "：" + episode + " 下载失败")
            self.animation.status[index] = 3
            msg = {
                "ErrorType": type(ex),
                "Title": title,
                "Section": episode,
                "Event": "下载失败",
                "TextOfLineEdit": self.inputLineEdit.text(),
                "VideoURL": url
            }
            Log.writeLog(time.strftime("%Y-%m-%d"), msg)
        finally:
            self.executor.lock.reduce()
        pass

    def m3u8Download(self, index: int):
        title = self.animation.title
        episode = list(self.animation.selectedUrls.keys())[index]
        url = self.animation.selectedUrls[episode]
        print(episode + ":" + url)
        self.treeItemStatusSignal.emit(index, "m3u8功能未完成")
        self.executor.lock.reduce()
        pass

    def showPercentage(self, index: int, allSize: int):
        self.treeItemStatusSignal.emit(index, "下载中")
        title = self.animation.title
        episode = list(self.animation.selectedUrls.keys())[index]
        path = os.path.join(Config.setting["TEMP_DIR"], title, episode + '.temp')
        while not self.animation.isDone(index):
            if os.path.lexists(path):
                now = os.path.getsize(path)
                self.treeItemPercentageSignal.emit(index, int(now / allSize * 100))
            time.sleep(0.07)
        if self.animation.status[index] == 2:
            self.treeItemPercentageSignal.emit(index, 100)
            self.treeItemStatusSignal.emit(index, "已完成")
        elif self.animation.status[index] == 3:
            self.treeItemPercentageSignal.emit(index, 0)
            self.treeItemStatusSignal.emit(index, "下载失败")
        pass

    @QtCore.pyqtSlot()
    def on_queryButton_clicked(self):
        inputUrl = self.inputLineEdit.text()  # http://www.imomoe.la/player/8006-0-0.html
        if len(inputUrl) != 0:
            self.ui.videoNameLabel.setText("正在查询中，请稍候...")
            if inputUrl.startswith("www"):
                inputUrl = "http://" + inputUrl
            queryThread = Thread(name='Query Thread', target=self.query, args=(inputUrl,), daemon=True)
            queryThread.start()
        pass

    @QtCore.pyqtSlot(int)
    def showSelection(self, index: int):
        """
        显示选项

        :param index: 类型为int。默认值为-1，根据其值来选择数据源。
        :return: 无
        """
        if index == -1:
            self.animation.select(0)

            self.ui.videoNameLabel.setText(self.animation.title)

            self.ui.videoSourceComboBox.clear()
            for i in range(0, len(self.animation.videoList)):
                self.ui.videoSourceComboBox.addItem(str(i + 1))
        else:
            self.animation.select(index)

        self.animation.checkBoxItems.clear()
        self.animation.status.clear()
        self.ui.treeWidget.clear()
        for epi in self.animation.selectedUrls:
            self.animation.status.append(-1)

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
        if index != 0 or self.ui.treeWidget.topLevelItemCount() == 0:
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
        episodes = list(self.animation.selectedUrls.keys())
        for i in range(0, len(self.animation.selectedUrls)):
            if self.animation.checkBoxItems[i].isChecked() and self.animation.status[i] == -1:
                print(episodes[i] + ":" + self.animation.selectedUrls[episodes[i]])
                self.ui.treeWidget.topLevelItem(i).setText(3, "等待中")
                self.animation.status[i] = 0
                if ".m3u8" in self.animation.selectedUrls[episodes[i]]:
                    thread = Thread(name=self.animation.title + "-" + episodes[i] + "-Download",
                                    target=self.m3u8Download, args=(i,), daemon=True)
                else:
                    thread = Thread(name=self.animation.title + "-" + episodes[i] + "-Download",
                                    target=self.download, args=(i,), daemon=True)
                self.executor.add(thread)
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
        sys.exit(0)
        pass

    @QtCore.pyqtSlot()
    def on_aboutAction_triggered(self):
        QtWidgets.QMessageBox.about(self, "关于 樱花动漫下载器", "\n作者：DevilSpiderX")
        pass

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def on_treeWidget_itemDoubleClicked(self, treeWidgetItem):
        index = self.ui.treeWidget.indexOfTopLevelItem(treeWidgetItem)
        if self.animation.checkBoxItems[index].isChecked():
            self.animation.checkBoxItems[index].setChecked(False)
        else:
            self.animation.checkBoxItems[index].setChecked(True)
        pass

    @QtCore.pyqtSlot(str)
    def on_lineEditComboBox_activated(self, name):
        if name in self.recoding:
            self.inputLineEdit.setText(self.recoding[name])
        pass

    @QtCore.pyqtSlot()
    def inputLineEditRecord(self):
        isDifferent = False
        if self.animation.title not in self.recoding:
            self.recoding[self.animation.title] = self.inputLineEdit.text()
            isDifferent = True
        elif self.recoding[self.animation.title] != self.inputLineEdit.text():
            self.recoding[self.animation.title] = self.inputLineEdit.text()
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
