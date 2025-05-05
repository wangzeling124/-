# # -*- coding: utf-8 -*-

# 数据爬取文件

import scrapy
import pymysql
import pymssql
from ..items import ZhiweixinxiItem
import time
from datetime import datetime,timedelta
import datetime as formattime
import re
import random
import platform
import json
import os
import urllib
from urllib.parse import urlparse
import requests
import emoji
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from selenium.webdriver import ChromeOptions, ActionChains
from scrapy.http import TextResponse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
# 职位信息
class ZhiweixinxiSpider(scrapy.Spider):
    name = 'zhiweixinxiSpider'
    spiderUrl = 'https://we.51job.com/api/job/search-pc?api_key=51job&timestamp=1713708420&keyword=%E5%A4%A7%E6%95%B0%E6%8D%AE%E5%BC%80%E5%8F%91&searchType=2&function=&industry=&jobArea=010000&jobArea2=&landmark=&metro=&salary=&workYear=&degree=&companyType=&companySize=&jobType=&issueDate=&sortType=0&pageNum={}&requestId=dff2a85ed9c9ddc7d6f97b3f73bf0e6c&pageSize=20&source=1&accountId=239785586&pageCode=sou%7Csou%7Csoulb'
    start_urls = spiderUrl.split(";")
    protocol = ''
    hostname = ''
    realtime = False

    headers = {
        'Referer':'https://we.51job.com/pc/search?jobArea=&keyword=%E6%95%B0%E6%8D%AE%E5%88%86%E6%9E%90%E5%B7%A5%E7%A8%8B%E5%B8%88&searchType=2&keywordType=guess_exp_tag5',
'Cookie':'用自己的Cookie'
    }

    def __init__(self,realtime=False,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.realtime = realtime=='true'

    def start_requests(self):

        plat = platform.system().lower()
        if not self.realtime and (plat == 'linux' or plat == 'windows'):
            connect = self.db_connect()
            cursor = connect.cursor()
            if self.table_exists(cursor, 'e7mzzleh_zhiweixinxi') == 1:
                cursor.close()
                connect.close()
                self.temp_data()
                return
        pageNum = 1 + 1

        for url in self.start_urls:
            if '{}' in url:
                for page in range(1, pageNum):

                    next_link = url.format(page)
                    yield scrapy.Request(
                        url=next_link,
                        headers=self.headers,
                        callback=self.parse
                    )
            else:
                yield scrapy.Request(
                    url=url,
                    headers=self.headers,
                    callback=self.parse
                )

    # 列表解析
    def parse(self, response):
        _url = urlparse(self.spiderUrl)
        self.protocol = _url.scheme
        self.hostname = _url.netloc
        plat = platform.system().lower()
        if not self.realtime and (plat == 'linux' or plat == 'windows'):
            connect = self.db_connect()
            cursor = connect.cursor()
            if self.table_exists(cursor, 'e7mzzleh_zhiweixinxi') == 1:
                cursor.close()
                connect.close()
                self.temp_data()
                return
        data = json.loads(response.body)
        try:
            list = data["resultbody"]["job"]["items"]
        except:
            pass
        for item in list:
            fields = ZhiweixinxiItem()


            try:
                fields["jobname"] = emoji.demojize(self.remove_html(str( item["jobName"] )))

            except:
                pass
            try:
                fields["jobarea"] = emoji.demojize(self.remove_html(str( item["jobAreaString"] )))

            except:
                pass
            try:
                fields["salary"] = emoji.demojize(self.remove_html(str( item["provideSalaryString"] )))

            except:
                pass
            try:
                fields["fbsj"] = emoji.demojize(self.remove_html(str( item["issueDateString"] )))

            except:
                pass
            try:
                fields["degree"] = emoji.demojize(self.remove_html(str( item["degreeString"] )))

            except:
                pass
            try:
                fields["gsmc"] = emoji.demojize(self.remove_html(str( item["companyName"] )))

            except:
                pass
            try:
                fields["gslogo"] = emoji.demojize(self.remove_html(str( item["companyLogo"] )))

            except:
                pass
            try:
                fields["zwlx"] = emoji.demojize(self.remove_html(str( item["termStr"] )))

            except:
                pass
            try:
                fields["gzjy"] = int( item["workYear"])
            except:
                pass
            try:
                fields["jobdescribe"] = emoji.demojize(self.remove_html(str( item["jobDescribe"] )))

            except:
                pass
            try:
                fields["jyyq"] = emoji.demojize(self.remove_html(str( item["workYearString"] )))

            except:
                pass
            try:
                fields["laiyuan"] = emoji.demojize(self.remove_html(str( item["jobHref"] )))

            except:
                pass
            yield fields

    # 详情解析
    def detail_parse(self, response):
        fields = response.meta['fields']
        return fields

    # 数据清洗
    def pandas_filter(self):
        engine = create_engine('mysql+pymysql://root:123456@localhost/spidere7mzzleh?charset=UTF8MB4')
        df = pd.read_sql('select * from zhiweixinxi limit 50', con = engine)

        # 重复数据过滤
        df.duplicated()
        df.drop_duplicates()

        #空数据过滤
        df.isnull()
        df.dropna()

        # 填充空数据
        df.fillna(value = '暂无')

        # 异常值过滤

        # 滤出 大于800 和 小于 100 的
        a = np.random.randint(0, 1000, size = 200)
        cond = (a<=800) & (a>=100)
        a[cond]

        # 过滤正态分布的异常值
        b = np.random.randn(100000)
        # 3σ过滤异常值，σ即是标准差
        cond = np.abs(b) > 3 * 1
        b[cond]

        # 正态分布数据
        df2 = pd.DataFrame(data = np.random.randn(10000,3))
        # 3σ过滤异常值，σ即是标准差
        cond = (df2 > 3*df2.std()).any(axis = 1)
        # 不满⾜条件的⾏索引
        index = df2[cond].index
        # 根据⾏索引，进⾏数据删除
        df2.drop(labels=index,axis = 0)

    # 去除多余html标签
    def remove_html(self, html):
        if html == None:
            return ''
        pattern = re.compile(r'<[^>]+>', re.S)
        return pattern.sub('', html).strip()

    # 数据库连接
    def db_connect(self):
        type = self.settings.get('TYPE', 'mysql')
        host = self.settings.get('HOST', 'localhost')
        port = int(self.settings.get('PORT', 3306))
        user = self.settings.get('USER', 'root')
        password = self.settings.get('PASSWORD', '123456')

        try:
            database = self.databaseName
        except:
            database = self.settings.get('DATABASE', '')

        if type == 'mysql':
            connect = pymysql.connect(host=host, port=port, db=database, user=user, passwd=password, charset='utf8')
        else:
            connect = pymssql.connect(host=host, user=user, password=password, database=database)
        return connect

    # 断表是否存在
    def table_exists(self, cursor, table_name):
        cursor.execute("show tables;")
        tables = [cursor.fetchall()]
        table_list = re.findall('(\'.*?\')',str(tables))
        table_list = [re.sub("'",'',each) for each in table_list]

        if table_name in table_list:
            return 1
        else:
            return 0

    # 数据缓存源
    def temp_data(self):

        connect = self.db_connect()
        cursor = connect.cursor()
        sql = '''
            replace into `zhiweixinxi`(
                id
                ,jobname
                ,jobarea
                ,salary
                ,fbsj
                ,degree
                ,gsmc
                ,gslogo
                ,zwlx
                ,gzjy
                ,jobdescribe
                ,jyyq
                ,laiyuan
            )
            select
                id
                ,jobname
                ,jobarea
                ,salary
                ,fbsj
                ,degree
                ,gsmc
                ,gslogo
                ,zwlx
                ,gzjy
                ,jobdescribe
                ,jyyq
                ,laiyuan
            from `e7mzzleh_zhiweixinxi`
            where(not exists (select
                id
                ,jobname
                ,jobarea
                ,salary
                ,fbsj
                ,degree
                ,gsmc
                ,gslogo
                ,zwlx
                ,gzjy
                ,jobdescribe
                ,jyyq
                ,laiyuan
            from `zhiweixinxi` where
                `zhiweixinxi`.id=`e7mzzleh_zhiweixinxi`.id
            ))
            order by rand()
            limit 50;
        '''

        cursor.execute(sql)
        connect.commit()
        connect.close()
