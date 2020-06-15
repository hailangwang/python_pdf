import time
import requests
import random
import execjs
import re
import logging
from functools import reduce



logging.basicConfig(format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s',
                    level=logging.DEBUG,
                    filename='test.log',
                    filemode='a')
class BaiduTrans(object):
    def __init__(self,user_agent,stoken_bduss,bdstoken):
        self.user_agent = user_agent;
        self._stoken_bduss = stoken_bduss
        self.pan_post = 'https://pan.baidu.com/share/verify?surl={}&t={}&channel=chunlei&web=1&app_id=250528&bdstoken='+bdstoken+'d&logid={}&clienttype=0'
        self.create_dir_post = 'https://pan.baidu.com/api/create?a=commit&channel=chunlei&app_id=250528&bdstoken=undefined&channel=chunlei&web=1&app_id=250528&bdstoken='+bdstoken+'&logid={}&clienttype=0'
        self.transfer_post = 'https://pan.baidu.com/share/transfer?shareid={}&from={}&ondup=newcopy&async=1&channel=chunlei&web=1&app_id=250528&bdstoken='+bdstoken+'&logid={}&clienttype=0'
        self.pan_s_url = 'https://pan.baidu.com/s/1{}'
        self.create_dir_data = {
            'isdir': '1',
            'size':	'',
            'block_list': [],
            'method': 'post',
            'dataType':	'json'
        }
        self.pwd_data = {
            'vcode': '',
            'vcode_str': '',
        }
        self.headers = {
            'User-Agent': user_agent,
            'Host': 'pan.baidu.com',
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Origin': 'https://pan.baidu.com',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.t = int(round(time.time() * 1000))

    def get_logid(self, baidu_id):
        with open('baiduyun.js', encoding='utf-8') as f:
            bootjs = f.read()
        js_obj = execjs.compile(bootjs)
        res = js_obj.call('getLogId', baidu_id)
        # print(res)
        return res

    def enter_pwd(self, source_filename, get_pan_url,pan_url, pan_pwd):
        """
        通过execjs运行生成logid的代码，获取后跟密码等参数一起发送post请求，将返回的BDCLND参数作为cookie加入到get
        'https://pan.baidu.com/s/1xxx' 的请求头中，可以正常访问资源文件页面
        """
        session = requests.session()
        # 请求需要密码的网盘资源的url；verify=False 避免频繁尝试被封，断开SSL，但是这个请求是不安全的
        r_baiduid = session.get(get_pan_url, headers={'user-agent': self.user_agent}, verify=False)
        # 获得当前的BAIDUID用于生成logid
        baiduid = r_baiduid.cookies['BAIDUID']
        logid = self.get_logid(baiduid)
        surl = get_pan_url.split('surl=')[1]
        self.pwd_data['pwd'] = pan_pwd
        self.headers['Referer'] = pan_url
        # 带密码的post请求，成功可以访问'https://pan.baidu.com/s/1xxx'页面
        r = session.post(self.pan_post.format(surl, self.t, logid), data=self.pwd_data, headers=self.headers,verify=False)

        # 返回带有randsk的json数据，取得bdclnd
        bdclnd = 'BDCLND=' + r.json()['randsk']
        # 访问'https://pan.baidu.com/s/1xxx'的请求头
        self.headers['Cookie'] = bdclnd
        # 'https://pan.baidu.com/s/1xxx'
        s_url = self.pan_s_url.format(surl)
        r_s_url = session.get(s_url, headers=self.headers, verify=False)
        r_s_url.encoding = 'utf-8'
        # 利用正则 获取 转存资源的post请求 所需的三个参数
        params = re.findall(r'yunData\.SHARE_ID = "(.*?)";.*?yunData\.SHARE_UK = "(.*?)";.*?yunData\.FS_ID = "(.*?)";',
                            r_s_url.text, re.S)[0]
        # 调用新建文件夹以及转存的请求
        self.create_dir(baiduid, s_url, source_filename, params, bdclnd)

    def create_dir(self, baiduid, s_url, source_filename, params, bdclnd):
        logid = self.get_logid(baiduid)
        shareid, from_id, fsidlist = params[0], params[1], params[2]
        transfer_url = self.transfer_post.format(shareid, from_id, logid)
        create_path = '/动漫/' + source_filename
        # 新建文件夹请求所需的data参数
        self.create_dir_data['path'] = create_path
        self.headers['Referer'] = s_url
        self.headers['Cookie'] = bdclnd + ';' + self._stoken_bduss
        # 需要两个参数BDUSS，STOKEN
        r_create_dir = requests.post(self.create_dir_post.format(logid), data=self.create_dir_data,
                                     headers=self.headers, verify=False)
        print(r_create_dir.json())
        # 需要三个参数BDUSS，BDCLND，STOKEN
        r_transfer = requests.post(transfer_url, data={'fsidlist': '[' + str(fsidlist) + ']', 'path': create_path},
                                   headers=self.headers, verify=False)
        print(r_transfer.text)



class BaiduShare(object):
    def __init__(self,user_agent,stoken_bduss,bdstoken):
        self.user_agent = user_agent;
        self._stoken_bduss = stoken_bduss;
        self.pan_list_get = 'https://pan.baidu.com/api/list?order=time&desc=1&showempty=0&web=1&page={}&num={}&dir={}&t={}&channel=chunlei&web=1&app_id=250528&bdstoken='+bdstoken+'&logid={}&clienttype=0&startLogTime={}'
        self.pan_share='https://pan.baidu.com/share/set?channel=chunlei&clienttype=0&web=1&channel=chunlei&web=1&app_id=250528&bdstoken='+bdstoken+'&logid={}==&clienttype=0'

        self.pan_share_data = {
            'schannel':4,
            'period':7,
            'channel_list':"[]"
        }
        self.headers = {
            'User-Agent': user_agent,
            'Host': 'pan.baidu.com',
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Origin': 'https://pan.baidu.com',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

        self.t = int(round(time.time() * 1000))

    def get_logid(self, baidu_id):
        with open('baiduyun.js', encoding='utf-8') as f:
            bootjs = f.read()
        js_obj = execjs.compile(bootjs)
        res = js_obj.call('getLogId', baidu_id)
        # print(res)
        return res

    def gen_code(self):
        lst1 = [] # 字母
        for i in range(97, 123):
            lst1.append(chr(i))

        for i in range(97, 123):
            lst1.append(chr(i))

        lst2 = []
        for i in range(10):
            lst2.append(i)

        zimu = random.randint(1, 3)
        shuzi = 4-zimu # 1 2

        z = random.sample(lst1, zimu)
        s = random.sample(lst2, shuzi)

        s1 = reduce(lambda x, y: str(x) + str(y), z, "")
        s2 = reduce(lambda x, y: str(x) + str(y), s, "")
        return s1 + s2

    def share(self,name,fsid,code,logid):
        self.pan_share_data['pwd'] = code
        self.pan_share_data['fid_list'] =fsid
        self.headers['Referer'] = 'https://pan.baidu.com/disk/home?'
        self.headers['Cookie']='BIDUPSID=D86AD4F8815CB6DB53BCA9125E703A5B; PSTM=1583739941; BAIDUID=D86AD4F8815CB6DBC232415D0578768A:FG=1; PANWEB=1; Hm_lvt_bff7b396e3d9f5901f8eec42a2ad3017=1584583466; MCITY=-315%3A; BDORZ=B490B5EBF6F3CD402E515D22BCDA1598; recommendTime=guanjia2020-06-09%2016%3A11%3A00; pan_login_way=1; BDUSS=FN3MmZ-bHp6WFBrLVB2c3VCU0Rvb3NMRTkyRXRxV2E2ODZ1b1oyZ042clFzQXBmSVFBQUFBJCQAAAAAAAAAAAEAAADg7wOfsKK2xbXn07AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANAj417QI-NeR; STOKEN=35fbac30b1702ccd0d07a4e089009fd53d40712da07e49231440dcb6697cc3d6; SCRC=a95832891ec5bab973e9c313f2908454; H_PS_PSSID=31725_1433_31672_21112_31069_32046_30824; Hm_lvt_7a3960b6f067eb0085b7f96ff5e660b0=1592016135,1592028673,1592034154,1592036202; csrfToken=WkrXFYZ5R_LvnU-HFdx-SmMk; BDRCVFR[feWj1Vr5u3D]=I67x6TjHwwYf0; delPer=0; PSINO=5; ZD_ENTRY=empty; cflag=13%3A3; BDCLND=ZAInqcxXZQnkFUWKIWaiFtqf19%2BL11OJgeQ2pzTGTyw%3D; Hm_lpvt_7a3960b6f067eb0085b7f96ff5e660b0=1592052487; PANPSC=393084746562946189%3AHSTAF2XekfqoPamKud4ouJgtJeEFa7WQslpo6nILLqvW2UKv9qdC5lKjRkjbnnAJslLqRqRv9%2FSaV1QHy3lx2xSLaspo12snBdDbbkvvmXYu%2FGN14ZZ7XmuoI1hzYu44o6EbltYhkHtjy4bwAz5jQiHq5mg%2FcPBDd4%2BXMkQBTi3ihEIzmOtMnQEMKGmQS2qL';
        re = requests.post(self.pan_share.format(logid), data=self.pan_share_data,headers=self.headers, verify=False)
        text = re.text
        print(text)




    def queryList(self,dir,get_pan_url):
        session = requests.session();
        page = 1;
        num = 100;
        self.headers['Cookie'] = self._stoken_bduss
        home = session.get("https://pan.baidu.com/disk/home?", headers=self.headers, verify=False)
        baiduid = home.cookies['BAIDUID']
        self.headers['Cookie'] = self._stoken_bduss + '; BAIDUID:' + baiduid
        logid = self.get_logid(baiduid)
        pandlist = session.get(self.pan_list_get.format(page, num, dir,time.time(), logid, time.time()), headers=self.headers, verify=False)

        errno = pandlist.json()["errno"]
        if(errno == 0):
            list = pandlist.json()["list"]
            for i in list:
                server_filename = i["server_filename"]
                fs_id = "["+str(i["fs_id"])+"]"
                self.share(server_filename,fs_id,self.gen_code(),logid = self.get_logid(baiduid))
        else:
            return






if __name__ == "__main__":

    USER_AGENT_LIST = [
        "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; AcooBrowser; .NET CLR 1.1.4322; .NET CLR 2.0.50727)",
        "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; Acoo Browser; SLCC1; .NET CLR 2.0.50727; Media Center PC 5.0; .NET CLR 3.0.04506)",
        "Mozilla/4.0 (compatible; MSIE 7.0; AOL 9.5; AOLBuild 4337.35; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)",
        "Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US)",
        "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Win64; x64; Trident/5.0; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 2.0.50727; Media Center PC 6.0)",
        "Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 1.0.3705; .NET CLR 1.1.4322)",
        "Mozilla/4.0 (compatible; MSIE 7.0b; Windows NT 5.2; .NET CLR 1.1.4322; .NET CLR 2.0.50727; InfoPath.2; .NET CLR 3.0.04506.30)",
        "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN) AppleWebKit/523.15 (KHTML, like Gecko, Safari/419.3) Arora/0.3 (Change: 287 c9dfb30)",
        "Mozilla/5.0 (X11; U; Linux; en-US) AppleWebKit/527+ (KHTML, like Gecko, Safari/419.3) Arora/0.6",
        "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.2pre) Gecko/20070215 K-Ninja/2.1.1",
        "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9) Gecko/20080705 Firefox/3.0 Kapiko/3.0",
        "Mozilla/5.0 (X11; Linux i686; U;) Gecko/20070322 Kazehakase/0.4.5",
        "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.8) Gecko Fedora/1.9.0.8-1.fc10 Kazehakase/0.5.6",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/535.20 (KHTML, like Gecko) Chrome/19.0.1036.7 Safari/535.20",
        "Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; fr) Presto/2.9.168 Version/11.52",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.11 TaoBrowser/2.0 Safari/536.11",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.71 Safari/537.1 LBBROWSER",
        "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; LBBROWSER)",
        "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E; LBBROWSER)",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.84 Safari/535.11 LBBROWSER",
        "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)",
        "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; QQBrowser/7.0.3698.400)",
        "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)",
        "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; SV1; QQDownload 732; .NET4.0C; .NET4.0E; 360SE)",
        "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; QQDownload 732; .NET4.0C; .NET4.0E)",
        "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E)",
        "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.89 Safari/537.1",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/21.0.1180.89 Safari/537.1",
        "Mozilla/5.0 (iPad; U; CPU OS 4_2_1 like Mac OS X; zh-cn) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8C148 Safari/6533.18.5",
        "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:2.0b13pre) Gecko/20110307 Firefox/4.0b13pre",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11",
        "Mozilla/5.0 (X11; U; Linux x86_64; zh-CN; rv:1.9.2.10) Gecko/20100922 Ubuntu/10.10 (maverick) Firefox/3.6.10",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    ]
    user_agent = USER_AGENT_LIST[random.randint(0, 34)]
    stoken_bduss ="PANWEB=1; Hm_lvt_bff7b396e3d9f5901f8eec42a2ad3017=1584583466; MCITY=-315%3A; BDORZ=B490B5EBF6F3CD402E515D22BCDA1598; recommendTime=guanjia2020-06-09%2016%3A11%3A00; pan_login_way=1; BDUSS=FN3MmZ-bHp6WFBrLVB2c3VCU0Rvb3NMRTkyRXRxV2E2ODZ1b1oyZ042clFzQXBmSVFBQUFBJCQAAAAAAAAAAAEAAADg7wOfsKK2xbXn07AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANAj417QI-NeR; STOKEN=35fbac30b1702ccd0d07a4e089009fd53d40712da07e49231440dcb6697cc3d6; SCRC=a95832891ec5bab973e9c313f2908454; BDCLND=eV0jUqw8sVjLUWvZJNiuwwlEZpVmH2BQuXO1d2qr7M8%3D; H_PS_PSSID=31725_1433_31672_21112_31069_32046_30824; delPer=0; PSINO=5; ZD_ENTRY=empty; BDRCVFR[feWj1Vr5u3D]=I67x6TjHwwYf0; cflag=13%3A3; Hm_lvt_7a3960b6f067eb0085b7f96ff5e660b0=1592016135,1592028673,1592034154,1592036202; Hm_lpvt_7a3960b6f067eb0085b7f96ff5e660b0=1592036202; PANPSC=17374896381691355910%3AHSTAF2XekfqoPamKud4ouJgtJeEFa7WQslpo6nILLqvW2UKv9qdC5lKjRkjbnnAJslLqRqRv9%2FSaV1QHy3lx208IpaWjq1cvID1grIx3okQu%2FGN14ZZ7XmuoI1hzYu44o6EbltYhkHtjy4bwAz5jQiHq5mg%2FcPBDd4%2BXMkQBTi3ihEIzmOtMnQEMKGmQS2qL";
    bdstoken="d3f64422ac46176f3a18f8d4f622433d"

    # 转存
    baiduTrans = BaiduTrans(user_agent,stoken_bduss,bdstoken);
    baiduTrans.enter_pwd("","https://pan.baidu.com/share/init?surl=WgS9x7aJ881YlhqxN2os-w","https://pan.baidu.com/s/1WgS9x7aJ881YlhqxN2os-w","k7na")

    # 分享
    # baiduShare = BaiduShare(user_agent,stoken_bduss,bdstoken);
    # baiduShare.queryList("/动漫","https://pan.baidu.com/share/init?surl=PNHbzQNIRnBsqq5o_p5NkQ");
