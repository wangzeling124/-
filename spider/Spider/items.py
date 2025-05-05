# 数据容器文件

import scrapy

class SpiderItem(scrapy.Item):
    pass

class ZhiweixinxiItem(scrapy.Item):
    # 职位名称
    jobname = scrapy.Field()
    # 工作地点
    jobarea = scrapy.Field()
    # 待遇
    salary = scrapy.Field()
    # 发布时间
    fbsj = scrapy.Field()
    # 学历要求
    degree = scrapy.Field()
    # 公司名称
    gsmc = scrapy.Field()
    # 公司LOGO
    gslogo = scrapy.Field()
    # 职位类型
    zwlx = scrapy.Field()
    # 工作经验
    gzjy = scrapy.Field()
    # 职位描述
    jobdescribe = scrapy.Field()
    # 经验要求
    jyyq = scrapy.Field()
    # 来源
    laiyuan = scrapy.Field()

