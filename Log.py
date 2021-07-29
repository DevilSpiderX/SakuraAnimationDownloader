import os
import threading
import time

import Config

if not os.path.lexists(Config.setting["LOG_DIR"]):
    os.mkdir(Config.setting["LOG_DIR"])

logLock = threading.RLock()


def writeLog(name: str, msg: dict):
    """

    :param name: 日志文件名
    :param msg: 类型是dict。它必须包含Time, ErrorType, Title, Section 和 Event。
    :return: 无
    """
    logPath = os.path.join(Config.setting["LOG_DIR"], name + '.log')
    msg["Time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    logLock.acquire()
    with open(logPath, "a", encoding='utf-8') as writer:
        writer.write("--------------------------------------------------------------------------------\n")
        for key in msg.keys():
            writer.write(key + " : " + str(msg[key]) + "\n")
        writer.write("--------------------------------------------------------------------------------\n")
    logLock.release()
    pass


def cleanLog():
    logList = os.listdir(Config.setting["LOG_DIR"])
    dif = len(logList) - Config.setting["MAX_LOG"]
    if dif > 0:
        for i in range(0, dif):
            path = os.path.join(Config.setting["LOG_DIR"], logList[i])
            os.remove(path)
    pass


cleanLog()
