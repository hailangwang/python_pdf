# coding=utf-8
import logging
from logging import handlers
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from flask import Flask,jsonify
import json
from flask import request
app = Flask(__name__)


binary_location = '/usr/bin/google-chrome'
chrome_driver_binary= '/usr/bin/chromedriver'
options = webdriver.ChromeOptions()
options.binary_location = binary_location  # 谷歌地址
options.add_argument('--no-sandbox')  # 解决DevToolsActivePort文件不存在的报错
options.add_argument('window-size=1920x3000')  # 指定浏览器分辨率
options.add_argument('--disable-gpu')  # 谷歌文档提到需要加上这个属性来规避bug
options.add_argument('--hide-scrollbars')  # 隐藏滚动条, 应对一些特殊页面
options.add_argument('blink-settings=imagesEnabled=false')  # 不加载图片, 提升速度
options.add_argument('--headless')  # 浏览器不提供可视化页面. linux下如果系统不支持可视化不加这条会启动失败
chromedriver = chrome_driver_binary

logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Log等级总开关
# 第四步，定义handler的输出格式
formatter = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
time_rotating_file_handler = handlers.TimedRotatingFileHandler(filename='pythonPdf.log', when='D')
time_rotating_file_handler.setLevel(logging.DEBUG)
time_rotating_file_handler.setFormatter(formatter)
logger.addHandler(time_rotating_file_handler)





def queryBookCatlog(goodsUrl,driver):


    driver.get(goodsUrl);
    try:
        catalog_btn = driver.find_element_by_id('catalog-btn')
        catalog_btn.click();
        catalog = driver.find_element_by_id('catalog').find_element_by_class_name('descrip')
        return catalog.text
    except Exception as e:
        print(e)

@app.route('/test/<seracrhName>/<count>')
def test(seracrhName,count):
    goodsList = []
    dic = dict(name=seracrhName, imgUrl=count)
    goodsList.append(dic)
    return json.dumps(goodsList)

@app.route('/searchGoods/<seracrhName>/<count>')
def search_goods(seracrhName,count):
    goodsList = []


    try:
        driver = webdriver.Chrome(chrome_options=options, executable_path=chromedriver)
        driver.implicitly_wait(10)
        logger.info("浏览器打开成功")
    except Exception as e:
        logger.error(e)
    url ='http://search.dangdang.com/?key='+seracrhName+'&act=input'
    response = requests.get(url)
    html = response.text
    soup = BeautifulSoup(html,'html.parser')
    books = soup.find_all('a', class_='pic')
    for i in range(len(books)):
        if i+1>3:
            break
        book = books[i]
        if len(list(book.children)[0].attrs) == 3:
            img = list(book.children)[0].attrs['data-original']
        else:
            img = list(book.children)[0].attrs['src']
        logger.info(driver)
        bookCatlog = queryBookCatlog(book.attrs['href'],driver)
        dic = dict(name=book.attrs['title'], imgUrl=img, url=book.attrs['href'],catlog=bookCatlog)
        goodsList.append(dic)
    driver.close();
    logger.info("searchGoods:"+json.dumps(goodsList))
    return json.dumps(goodsList)

@app.route('/ocr')
def ocr():
    url = request.args.get("url");
    imageUrl = request.args.get("imageUrl");
    try:
        driver = webdriver.Chrome(chrome_options=options, executable_path=chromedriver)
        driver.implicity_wait(10)
        logger.info("浏览器打开成功")
    except Exception as e:
        logger.error(e)

    driver.get(url);
    result ="";
    try:
        input = driver.find_element_by_id('upload-file-input1')
        input.send_keys(imageUrl)
        result = driver.find_element_by_id('result1').get_attribute('innerHTML')
    except Exception as e:
        driver.close()
        logger.error(e)

    driver.close()
    return  result



if __name__ == '__main__':
    app.run(host="localhost", port=5000, debug=False)


