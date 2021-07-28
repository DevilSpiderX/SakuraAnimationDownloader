import json
import os.path

setting = {}
''' 
DOWNLOAD_DIR 下载保存路径\n
TEMP_DIR 缓存路径\n
PROXY 代理地址\n
MAX_NUM_PARALLEL_DOWNLOAD 最大并发下载数\n
'''
REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed"
              "-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.14"
                  "1 Safari/537.36 Edg/87.0.664.75"
}


def saveSetting():
    with open("config.json", "w", encoding="utf8") as writer:
        json.dump(setting, writer, indent='\t')
    pass


if os.path.exists("config.json"):
    with open("config.json", "r", encoding="utf8") as reader:
        setting = json.load(reader)
if "DOWNLOAD_DIR" not in setting:
    setting["DOWNLOAD_DIR"] = os.path.abspath(".")
if "TEMP_DIR" not in setting:
    setting["TEMP_DIR"] = os.path.abspath("./temp")
if "PROXY" not in setting:
    setting["PROXY"] = ""
if "MAX_NUM_PARALLEL_DOWNLOAD" not in setting:
    setting["MAX_NUM_PARALLEL_DOWNLOAD"] = 3
if "RECORDING_PATH" not in setting:
    setting["RECORDING_PATH"] = os.path.abspath("./recording.json")
if "LOG_DIR" not in setting:
    setting["LOG_DIR"] = os.path.abspath("./log")

saveSetting()
