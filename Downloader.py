import json
import os
import re
import sys
import time
import urllib.request
from threading import Thread

import requests
from PyQt5 import QtCore, QtWidgets

import Icon
import Log
from uic.UI_MainDownloader import Ui_MainWindow

checkBoxItems = []  # 集数下载复选框列表
Url = 'http://www.imomoe.ai'  # 网页前缀
Title = ''  # 视频的名字
allSize = 0  # 总大小
realUrl = []  # 真实视频地址
episodes = []  # 视频的集数名称
downloadSpeed = 0  # 下载速度
downloadDir = "."  # 下载目录
headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed"
              "-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.14"
                  "1 Safari/537.36 Edg/87.0.664.75"
}  # 请求头
recordingJson = {}  # 历史记录字典
proxies = urllib.request.getproxies()


def getHTML(url: str) -> str:
    """
    获取网页源码

    :param url: 类型为字符串。正确的网址。
    :return: 类型为字符串。网页源码。
    """
    r = requests.get(url, proxies=proxies)
    r.encoding = 'gb2312'
    return r.text


def getTitle(text: str) -> str:
    """
    获取视频的名字

    :param text: 类型为字符串。网页源码。
    :return: 类型为字符串。视频的名字。
    """
    return re.findall('var xTitle=\'.+\';</script>', text)[0].split('\'')[1]


def getSuffix(text: str) -> str:
    """
    获取网址的后缀

    :param text: 类型为字符串。网页源码。
    :return: 类型为字符串。从text中分离出的网址后缀字符串。
    """
    return re.findall('/playdata/\\d+/\\d+.js\\?\\d+.\\d+', text)[0]


def getJsonString(text: str) -> str:
    """
    获取VideoJson

    :param text: 类型为字符串。带有json的原始文本。一般是网页源码。
    :return: 类型为字符串。从text中分离出只含有json的字符串。
    """
    return re.split('Json=|,urlinfo', text)[1]


def getInputUrl(originUrl: str) -> str:
    """
    获取输入的网址
    
    :param originUrl: 类型为字符串。原始的网址，以防有些人输入网址时不带"http"。
    :return: 类型为字符串。带有"http"的网址的字符串。
    """
    regex = "http://"
    if re.search(regex, originUrl) is None:
        return regex + originUrl
    else:
        return originUrl


class QueryThread(Thread):
    """查询线程"""

    def __init__(self, inputUrl: str):
        super(QueryThread, self).__init__(name="QueryThread_0")
        self.setDaemon(True)
        self.inputUrl = inputUrl
        pass

    def run(self) -> None:
        global Title
        inputUrl = getInputUrl(self.inputUrl)

        HTML = getHTML(inputUrl)

        Title = getTitle(HTML)

        videoJsonUrl = Url + getSuffix(HTML)
        videoListJsonString = getJsonString(getHTML(videoJsonUrl))
        videoListJsonString = videoListJsonString.replace('\'', '\"')
        downloader.videoListJson = json.loads(videoListJsonString)
        downloader.addLineEditRecordingSignal.emit()
        downloader.showSelectionSignal.emit(-1)
        pass

    pass


def query(inputUrl: str):
    queryThread = QueryThread(inputUrl)
    queryThread.start()
    pass


class DownloaderFrame(QtWidgets.QMainWindow):
    """下载器窗体类"""

    showSelectionSignal = QtCore.pyqtSignal(int)
    addLineEditRecordingSignal = QtCore.pyqtSignal()

    def __init__(self):
        super(DownloaderFrame, self).__init__()

        self.ui = Ui_MainWindow()
        self.icon = Icon.getIcon()
        self.setWindowIcon(self.icon)

        self.ui.setupUi(self)
        self.lineEdit = QtWidgets.QLineEdit()
        self.videoListJson = json.loads('{\"1\":1}')
        self.ui.allSelectButton.setEnabled(False)
        self.ui.downloadButton.setEnabled(False)
        self.setLineEdit()
        self.lineEdit.returnPressed.connect(self.on_queryButton_clicked)
        self.showSelectionSignal.connect(self.showSelection)
        self.addLineEditRecordingSignal.connect(self.addLineEditRecording)
        pass

    @QtCore.pyqtSlot(int)
    def showSelection(self, index: int):
        """
        显示选项

        :param index: 类型为int。默认值为-1，根据其值来选择数据源。
        :return: 无
        """
        global realUrl, episodes
        if index == -1:
            videoUrls = self.videoListJson[0][1]

            self.ui.videoNameLabel.setText(Title)

            self.ui.videoSourceComboBox.clear()
            for i in range(0, len(self.videoListJson)):
                self.ui.videoSourceComboBox.addItem(str(i + 1))
        else:
            videoUrls = self.videoListJson[index][1]

        checkBoxItems.clear()
        episodes.clear()
        realUrl.clear()
        self.ui.treeWidget.clear()
        for i in range(0, len(videoUrls)):
            treeItem = QtWidgets.QTreeWidgetItem()
            treeItem.setTextAlignment(3, QtCore.Qt.AlignCenter)
            treeItem.setTextAlignment(1, QtCore.Qt.AlignCenter)
            self.ui.treeWidget.addTopLevelItem(treeItem)

            data = videoUrls[i].split('$')
            episode = data[0]
            episodes.append(episode)
            url = data[1]
            realUrl.append(url)

            checkBox = QtWidgets.QCheckBox()
            hLayout = QtWidgets.QHBoxLayout()
            hLayout.addWidget(checkBox, alignment=QtCore.Qt.AlignCenter)
            itemCheckBoxWidget = QtWidgets.QWidget()
            itemCheckBoxWidget.setLayout(hLayout)
            self.ui.treeWidget.setItemWidget(treeItem, 0, itemCheckBoxWidget)
            checkBoxItems.append(checkBox)
            checkBox.stateChanged.connect(self.changeAllSelectButtonText)

            treeItem.setText(1, episode)

            progressBar = QtWidgets.QProgressBar()
            progressBar.setValue(0)
            self.ui.treeWidget.setItemWidget(treeItem, 2, progressBar)

        self.ui.allSelectButton.setEnabled(True)
        self.ui.downloadButton.setEnabled(True)
        self.ui.allSelectButton.setText("全选")
        pass

    @QtCore.pyqtSlot()
    def on_queryButton_clicked(self):
        try:
            inputUrl = self.lineEdit.text()
            if len(inputUrl) != 0:
                self.ui.videoNameLabel.setText("正在查询中，请稍候...")
                query(inputUrl)
        except requests.exceptions.ConnectionError as ex:
            Log.openLogOutObject()
            msg = {
                "ErrorType": type(ex),
                "Title": "无",
                "Section": "无",
                "Event": "查询失败",
                "TextOfLineEdit": self.lineEdit.text(),
                "Reason": "输入了错误的网址"
            }
            Log.writeLog(msg)
            Log.closeLogOutObject()
            msgBox = QtWidgets.QMessageBox()
            msgBox.setWindowTitle('错误')
            msgBox.setWindowIcon(self.icon)
            msgBox.setIcon(QtWidgets.QMessageBox.Critical)
            msgBox.setText("请输入正确的网址")
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msgBox.setDefaultButton(QtWidgets.QMessageBox.Ok)
            msgBox.exec_()
        pass

    @QtCore.pyqtSlot()
    def on_allSelectButton_clicked(self):
        if self.ui.allSelectButton.text() == "全选":
            for item in checkBoxItems:
                item.setCheckState(QtCore.Qt.Checked)
            self.ui.allSelectButton.setText("取消")
        elif self.ui.allSelectButton.text() == "取消":
            for item in checkBoxItems:
                item.setCheckState(QtCore.Qt.Unchecked)
            self.ui.allSelectButton.setText("全选")
        elif self.ui.allSelectButton.text() == "反选":
            for item in checkBoxItems:
                if item.isChecked():
                    item.setChecked(False)
                else:
                    item.setChecked(True)
        pass

    @QtCore.pyqtSlot(str)
    def on_videoSourceComboBox_activated(self, text):
        # self.showSelection(index=int(text) - 1)
        self.showSelectionSignal.emit(int(text) - 1)
        self.ui.allSelectButton.setText("全选")
        pass

    @QtCore.pyqtSlot()
    def on_downloadButton_clicked(self):
        downloadThread = DownloadThread("downloadThread_0")
        downloadThread.start()
        self.ui.videoSourceComboBox.setEnabled(False)
        self.ui.downloadButton.setEnabled(False)
        self.ui.queryButton.setEnabled(False)
        self.ui.allSelectButton.setEnabled(False)
        for checkBox in checkBoxItems:
            checkBox.setEnabled(False)
        for i in range(0, self.ui.treeWidget.topLevelItemCount()):
            if checkBoxItems[i].isChecked():
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
    def changeAllSelectButtonText(self):
        statue = 0
        for item in checkBoxItems:
            if item.isChecked():
                statue += 1
        if statue == 0:
            self.ui.allSelectButton.setText("全选")
        elif statue == len(checkBoxItems):
            self.ui.allSelectButton.setText("取消")
        else:
            self.ui.allSelectButton.setText("反选")
        pass

    @QtCore.pyqtSlot()
    def on_downloadPathAction_triggered(self):
        global downloadDir
        downloadDir = QtWidgets.QFileDialog.getExistingDirectory(self, "选择下载目录", downloadDir)
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
        if checkBoxItems[index].isChecked():
            checkBoxItems[index].setChecked(False)
        else:
            checkBoxItems[index].setChecked(True)
        pass

    def setLineEdit(self):
        global recordingJson
        self.lineEdit.setClearButtonEnabled(True)
        self.ui.lineEditComboBox.setLineEdit(self.lineEdit)
        recordingPath = Log.getSoftwareSettingStoragePath() + "\\Recording\\recording.json"
        if os.path.lexists(recordingPath):
            with open(recordingPath, "r", encoding="utf-8")as reader:
                recordingJson = json.load(reader)
            recordingList = [""]
            for key in recordingJson.keys():
                recordingList.append(key)
            self.ui.lineEditComboBox.addItems(recordingList)
            pass

    @QtCore.pyqtSlot(str)
    def on_lineEditComboBox_activated(self, nameOfAnimation):
        if nameOfAnimation in recordingJson.keys():
            self.lineEdit.setText(recordingJson[nameOfAnimation])
        pass

    @QtCore.pyqtSlot()
    def addLineEditRecording(self):
        if Title not in recordingJson.keys():
            recordingJson[Title] = self.lineEdit.text()
            softwareSettingStoragePath = Log.getSoftwareSettingStoragePath()
            recordingStoragePath = softwareSettingStoragePath + "\\Recording"
            if not os.path.lexists(softwareSettingStoragePath):
                os.mkdir(softwareSettingStoragePath)
            if not os.path.lexists(recordingStoragePath):
                os.mkdir(recordingStoragePath)
            recordingPath = recordingStoragePath + "\\recording.json"
            with open(recordingPath, "w") as writer:
                json.dump(recordingJson, writer)
        pass

    pass


class DownloadThread(Thread):
    """下载线程"""

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.daemon = True

    def run(self) -> None:
        for i in range(0, len(checkBoxItems)):
            if checkBoxItems[i].isChecked():
                download(episodes[i], realUrl[i], i)
        pass

    pass


def download(episode: str, url: str, index: int):
    """
    进行下载

    :param episode: 类型为字符串。下载的视频的集数。
    :param url: 类型为字符串。视频原始地址。
    :param index: 类型为int。其值为treeWidget中的第几行。
    :return: 无
    """
    global allSize
    print(episode + ":" + url)
    showSizeThread = None
    try:
        if not os.path.lexists(downloadDir + "\\" + Title):
            os.mkdir(downloadDir + "\\" + Title)

        path = downloadDir + "\\" + Title + '\\' + episode + ".mp4"

        showSizeThread = ShowPercentageThread(path, index)

        r = requests.get(url, stream=True, headers=headers, proxies=proxies)

        allSize = float(r.headers.get('Content-Length')) / 1024 / 1024

        with open(path, "wb") as f:
            showSizeThread.start()
            for chunk in r.iter_content(chunk_size=1024):  # 这样就可以下载一定大小就写入文件
                if chunk:
                    f.write(chunk)
            showSizeThread.stop()
    except BaseException as ex:
        Log.openLogOutObject()
        msg = {
            "ErrorType": type(ex),
            "Title": Title,
            "Section": episode,
            "Event": "下载失败",
            "TextOfLineEdit": downloader.lineEdit.text(),
            "VideoURL": url
        }
        Log.writeLog(msg)
        Log.closeLogOutObject()

        showSizeThread.downloadFailed()
    pass


class ShowPercentageThread(QtCore.QThread):
    """显示下载完成度的线程"""
    treeItemPercentageSignal = QtCore.pyqtSignal(int, int)
    treeItemStatusSignal = QtCore.pyqtSignal(int, str)

    def __init__(self, path, index):
        super().__init__()
        self.path = path
        self.index = index
        self.isRun = True
        self.isFailed = False
        self.treeItemPercentageSignal.connect(downloader.on_treeWidget_progressBar_setValue)
        self.treeItemStatusSignal.connect(downloader.on_treeWidget_itemStatus_change)
        self.showNetSpeedThread = ShowNetSpeedThread(path, index)
        pass

    def run(self) -> None:
        global downloadSpeed
        self.treeItemStatusSignal.emit(self.index, "下载中")
        self.showNetSpeedThread.start()
        while self.isRun:
            if os.path.lexists(self.path):
                now = os.path.getsize(self.path) / 1024 / 1024
                self.treeItemPercentageSignal.emit(self.index, int(now / allSize * 100))
            if self.isRun:
                time.sleep(0.07)

        self.showNetSpeedThread.stop()
        if not self.isFailed:
            self.treeItemPercentageSignal.emit(self.index, 100)
            self.treeItemStatusSignal.emit(self.index, "已完成")
        pass

    def stop(self):
        self.isRun = False
        pass

    def downloadFailed(self):
        self.treeItemStatusSignal.emit(self.index, "下载失败")
        self.isFailed = True
        self.isRun = False
        pass

    pass


class ShowNetSpeedThread(Thread):
    """显示下载速度的线程"""

    def __init__(self, path, index):
        super().__init__()
        self.path = path
        self.index = index
        self.isRun = True
        pass

    def run(self) -> None:
        global downloadSpeed
        last = 0
        while self.isRun:
            if os.path.lexists(self.path):
                now = os.path.getsize(self.path) / 1024 / 1024
                downloadSpeed = (now - last) / 1
                last = now
                if downloadSpeed < 1:
                    downloader.ui.speedLabel.setText("Speed: %.0f KB/s" % (downloadSpeed * 1024))
                else:
                    downloader.ui.speedLabel.setText("Speed: %.2f MB/s" % downloadSpeed)
            time.sleep(1)
        pass

    def stop(self):
        self.isRun = False
        pass

    pass


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    downloader = DownloaderFrame()
    downloader.show()
    sys.exit(app.exec_())
