import getpass
import os
import time

logOut = None  # 日志输出对象


def getSoftwareSettingStoragePath() -> str:
    """
    获取下载器设置属性存放路径

    :return: 类型为字符串。下载器设置属性存放路径的字符串。
    """
    return "C:\\Users\\" + getpass.getuser() + "\\AppData\\Local\\SakuraAnimationDownloader"


def openLogOutObject():
    """
    开启日志输出对象

    :return: 无
    """
    global logOut
    softwareSettingStoragePath = getSoftwareSettingStoragePath()
    logStoragePath = softwareSettingStoragePath + "\\Log"
    if not os.path.lexists(softwareSettingStoragePath):
        os.mkdir(softwareSettingStoragePath)
    if not os.path.lexists(logStoragePath):
        os.mkdir(logStoragePath)
    logPath = logStoragePath + "\\log.txt"
    logOut = open(logPath, "a", encoding='utf-8')
    logOut.write("--------------------------------------------------------------------------------\n")
    writeLog({"Time": time.strftime("%Y-%m-%d %H:%M:%S")})
    pass


def writeLog(msg: dict):
    """
    写日志到log.txt

    :param msg: 类型是dict。它必须包含Time, ErrorType, Title, Section 和 Event。
    :return: 无
    """
    for key in msg.keys():
        logOut.write(key + " : " + str(msg[key]) + "\n")
    pass


def closeLogOutObject():
    """
    关闭日志输出对象

    :return: 无
    """
    logOut.write("--------------------------------------------------------------------------------\n")
    logOut.close()
    pass
