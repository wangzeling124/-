# coding:utf-8
__author__ = "ila"

import logging, os, json, configparser
import time
import numbers
import requests
from werkzeug.utils import redirect

from flask import request, jsonify,session
from sqlalchemy.sql import func,and_,or_,case
from sqlalchemy import cast, Integer,Float
from api.models.brush_model import *
from . import main_bp
from utils.codes import *
from utils.jwt_auth import Auth
from configs import configs
from utils.helper import *
import random
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from email.header import Header
from utils.baidubce_api import BaiDuBce
from api.models.config_model import config
from flask import current_app as app
from utils.spark_func import spark_read_mysql
from utils.hdfs_func import upload_to_hdfs
from utils.mapreduce1 import MRMySQLAvg
import pandas as pd
# 注册接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/register", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxi_register():
    if request.method == 'POST':#post请求
        msg = {'code': normal_code, 'message': 'success', 'data': [{}]}
        req_dict = session.get("req_dict")


        #创建新用户数据
        error = zhiweixinxi.createbyreq(zhiweixinxi, zhiweixinxi, req_dict)
        if error!=None and error is Exception:
            msg['code'] = crud_error_code
            msg['msg'] = "注册用户已存在"
        else:
            msg['data'] = error
        #返回结果
        return jsonify(msg)

# 登录接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/login", methods=['GET','POST'])
def pythoni2v8cf2c_zhiweixinxi_login():
    if request.method == 'GET' or request.method == 'POST':#get、post请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        #获取用户名和密码参数
        req_dict = session.get("req_dict")
        req_model = session.get("req_dict")
        try:
            del req_model['role']
        except:
            pass
        #根据用户名获取用户数据
        datas = zhiweixinxi.getbyparams(zhiweixinxi, zhiweixinxi, req_model)
        if not datas:#如果为空则代表账号密码错误或用户不存在
            msg['code'] = password_error_code
            msg['msg']='密码错误或用户不存在'
            return jsonify(msg)


        req_dict['id'] = datas[0].get('id')
        try:
            del req_dict['mima']
        except:
            pass

        #新建用户缓存数据并返回结果
        return Auth.authenticate(Auth, zhiweixinxi, req_dict)


# 登出接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/logout", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxi_logout():
    if request.method == 'POST':#post请求
        msg = {
            "msg": "退出成功",
            "code": 0
        }
        req_dict = session.get("req_dict")

        return jsonify(msg)

# 重置密码接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/resetPass", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxi_resetpass():
    if request.method == 'POST':#post请求
        msg = {"code": normal_code, "msg": "success"}
        #获取传递的参数
        req_dict = session.get("req_dict")

        if req_dict.get('mima') != None:
            req_dict['mima'] = '123456'
        #更新重置后的密码
        error = zhiweixinxi.updatebyparams(zhiweixinxi, zhiweixinxi, req_dict)

        if error != None:
            msg['code'] = crud_error_code
            msg['msg'] = error
        else:
            msg['msg'] = '密码已重置为：123456'
        return jsonify(msg)

# 获取会话信息接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/session", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_session():
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "data": {}}
        #获取token里的id，查找对应的用户数据返回
        req_dict={"id":session.get('params').get("id")}
        msg['data']  = zhiweixinxi.getbyparams(zhiweixinxi, zhiweixinxi, req_dict)[0]

        return jsonify(msg)

# 分类接口（后端）
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/page", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_page():
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success",  "data":{"currPage":1,"totalPage":1,"total":1,"pageSize":10,"list":[]}}
        #获取传递的参数
        req_dict = session.get("req_dict")
        userinfo = session.get("params")
        try:#判断是否有消息
            __hasMessage__=zhiweixinxi.__hasMessage__
        except:
            __hasMessage__=None
        if __hasMessage__ and __hasMessage__!="否":
            tablename=session.get("tablename")
            if tablename!="users" and session.get("params")!=None and zhiweixinxi!='chat':
                req_dict["userid"]=session.get("params").get("id")

        tablename=session.get("tablename")
        #非管理员账号则需要判断用户的相应权限
        if tablename!="users" :
            mapping_str_to_object = {}
            for model in Base_model._decl_class_registry.values():
                if hasattr(model, '__tablename__'):
                    mapping_str_to_object[model.__tablename__] = model

            try:#是否有管理员权限
                __isAdmin__=mapping_str_to_object[tablename].__isAdmin__
            except:
                __isAdmin__=None
            try:#是否有用户权限
                __authSeparate__ =mapping_str_to_object[tablename].__authSeparate__
            except:
                __authSeparate__ = None

            if __isAdmin__!="是" and __authSeparate__ == "是" and session.get("params")!=None:
                req_dict["userid"]=session.get("params").get("id")
            else:
                try:
                    del req_dict["userid"]
                except:
                    pass

            # 当前表也是有管理员权限的表
            if  __isAdmin__ == "是" and 'zhiweixinxi' != 'forum':
                if req_dict.get("userid") and 'zhiweixinxi' != 'chat':
                    del req_dict["userid"]
            else:
                #非管理员权限的表,判断当前表字段名是否有userid
                if tablename!="users" and 'zhiweixinxi'[:7]!='discuss'and "userid" in zhiweixinxi.getallcolumn(zhiweixinxi,zhiweixinxi):
                    req_dict["userid"] = session.get("params").get("id")

        clause_args = []
        or_clauses = or_(*clause_args)
        #查询列表数据
        msg['data']['list'], msg['data']['currPage'], msg['data']['totalPage'], msg['data']['total'], \
        msg['data']['pageSize']  = zhiweixinxi.page(zhiweixinxi, zhiweixinxi, req_dict, or_clauses)
        return jsonify(msg)

# 排序接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/autoSort", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_autosort():
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success",  "data":{"currPage":1,"totalPage":1,"total":1,"pageSize":10,"list":[]}}
        #获取传递的参数
        req_dict = session.get("req_dict")
        req_dict['sort']='clicktime'
        req_dict['order']='desc'

        try:#获取需要排序的内容
            __browseClick__= zhiweixinxi.__browseClick__
        except:
            __browseClick__=None
        #根据排序字段进行排序
        if __browseClick__ =='是':
            req_dict['sort']='clicknum'
        elif __browseClick__ =='时长':
            req_dict['sort']='browseduration'
        else:
            req_dict['sort']='clicktime'
        #获取排序内容
        msg['data']['list'], msg['data']['currPage'], msg['data']['totalPage'], msg['data']['total'], \
        msg['data']['pageSize']  = zhiweixinxi.page(zhiweixinxi, zhiweixinxi, req_dict)

        return jsonify(msg)

#查询单条数据
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/query", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_query():
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success",  "data":{}}
        #获取传递的参数，根据参数获取单条结果
        req_dict = session.get("req_dict")
        query = db.session.query(zhiweixinxi)
        for key, value in req_dict.items():
            query = query.filter(getattr(zhiweixinxi, key) == value)
        query_result = query.first()
        query_result.__dict__.pop('_sa_instance_state', None)
        msg['data'] = query_result.__dict__
        return jsonify(msg)

# 分页接口（前端）
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/list", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_list():
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success",  "data":{"currPage":1,"totalPage":1,"total":1,"pageSize":10,"list":[]}}
        #获取传递的参数
        req_dict = session.get("req_dict")
        if req_dict.__contains__('vipread'):
            del req_dict['vipread']
            
        userinfo = session.get("params")

        try:#判断是否有列表权限
            __foreEndListAuth__=zhiweixinxi.__foreEndListAuth__
        except:
            __foreEndListAuth__=None
        #不需要权限判断就去掉userid
        if __foreEndListAuth__ and __foreEndListAuth__!="否":
            tablename=session.get("tablename")
            if tablename!="users" and session.get("params")!=None:
                req_dict['userid']=session.get("params").get("id")

        tablename=session.get("tablename")

        if 'luntan' in 'zhiweixinxi':
            if 'userid' in req_dict.keys():
                del req_dict["userid"]

        if 'discuss' in 'zhiweixinxi':
            if 'userid' in req_dict.keys():
                del req_dict["userid"]
        #根据封装的req_dict字典去筛选获取列表数据
        msg['data']['list'], msg['data']['currPage'], msg['data']['totalPage'], msg['data']['total'], \
        msg['data']['pageSize']  = zhiweixinxi.page(zhiweixinxi, zhiweixinxi, req_dict)
        return jsonify(msg)

# 保存接口（后端）
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/save", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxi_save():
    if request.method == 'POST':#post请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        #获取传递的参数
        req_dict = session.get("req_dict")
        for key in req_dict:#将空值转为None
            if req_dict[key] == '':
                req_dict[key] = None

        #保存数据
        error= zhiweixinxi.createbyreq(zhiweixinxi, zhiweixinxi, req_dict)
        if error!=None and error is Exception:
            msg['code'] = crud_error_code
            msg['msg'] = error
        else:
            msg['data'] = error
        return jsonify(msg)

# 添加接口（前端）
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/add", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxi_add():
    if request.method == 'POST':#post请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        #获取参数
        req_dict = session.get("req_dict")
        #判断用户权限
        try:
            __foreEndListAuth__=zhiweixinxi.__foreEndListAuth__
        except:
            __foreEndListAuth__=None
        #不需要权限则去掉userid
        if __foreEndListAuth__ and __foreEndListAuth__!="否":
            tablename=session.get("tablename")
            if tablename!="users":
                req_dict['userid']=session.get("params").get("id")

        #保存数据
        error= zhiweixinxi.createbyreq(zhiweixinxi, zhiweixinxi, req_dict)
        if error!=None and error is Exception:
            msg['code'] = crud_error_code
            msg['msg'] = error
            return jsonify(msg)
        else:
            msg['data'] = error
        return jsonify(msg)

# 踩、赞接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/thumbsup/<id_>", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_thumbsup(id_):
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        req_dict = session.get("req_dict")
        id_=int(id_)
        type_=int(req_dict.get("type",0))
        #获取要踩赞的记录
        rets=zhiweixinxi.getbyid(zhiweixinxi, zhiweixinxi,id_)
        update_dict={
            "id":id_,
        }
        #加减数据
        if type_==1:#赞
            update_dict["thumbsupnum"]=int(rets[0].get('thumbsupnum'))+1
        elif type_==2:#踩
            update_dict["crazilynum"]=int(rets[0].get('crazilynum'))+1
        #更新记录
        error = zhiweixinxi.updatebyparams(zhiweixinxi, zhiweixinxi, update_dict)
        if error!=None:
            msg['code'] = crud_error_code
            msg['msg'] = error
        return jsonify(msg)

# 获取详情信息（后端）
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/info/<id_>", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_info(id_):
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        #根据id获取对应记录
        data = zhiweixinxi.getbyid(zhiweixinxi, zhiweixinxi, int(id_))
        if len(data)>0:
            msg['data']=data[0]
        #浏览点击次数
        try:
            __browseClick__= zhiweixinxi.__browseClick__
        except:
            __browseClick__=None

        if __browseClick__  and  "clicknum"  in zhiweixinxi.__table__.columns:
            click_dict={"id":int(id_),"clicknum":str(int(data[0].get("clicknum") or 0)+1)}#增加点击次数
            ret=zhiweixinxi.updatebyparams(zhiweixinxi,zhiweixinxi,click_dict)#更新记录
            if ret!=None:
                msg['code'] = crud_error_code
                msg['msg'] = ret
        return jsonify(msg)

# 获取详情信息（前端）
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/detail/<id_>", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_detail(id_):
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        #根据id获取对应记录
        data = zhiweixinxi.getbyid(zhiweixinxi, zhiweixinxi, int(id_))
        if len(data)>0:
            msg['data']=data[0]

        #浏览点击次数
        try:
            __browseClick__= zhiweixinxi.__browseClick__
        except:
            __browseClick__=None

        if __browseClick__ and "clicknum" in zhiweixinxi.__table__.columns:
            click_dict={"id":int(id_),"clicknum":str(int(data[0].get("clicknum") or 0)+1)}#增加点击次数
            ret=zhiweixinxi.updatebyparams(zhiweixinxi,zhiweixinxi,click_dict)#更新记录
            if ret!=None:
                msg['code'] = crud_error_code
                msg['msg'] = ret
        return jsonify(msg)

# 更新接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/update", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxi_update():
    if request.method == 'POST':#post请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        req_dict = session.get("req_dict")
        #如果存在密码或点击次数则不更新
        if req_dict.get("mima") and "mima" not in zhiweixinxi.__table__.columns :
            del req_dict["mima"]
        if req_dict.get("password") and "password" not in zhiweixinxi.__table__.columns :
            del req_dict["password"]
        try:
            del req_dict["clicknum"]
        except:
            pass

        #更新记录
        error = zhiweixinxi.updatebyparams(zhiweixinxi, zhiweixinxi, req_dict)
        if error!=None:
            msg['code'] = crud_error_code
            msg['msg'] = error

        return jsonify(msg)

# 删除接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/delete", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxi_delete():
    if request.method == 'POST':#post请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        req_dict = session.get("req_dict")
        #删除记录
        error=zhiweixinxi.delete(
            zhiweixinxi,
            req_dict
        )
        if error!=None:
            msg['code'] = crud_error_code
            msg['msg'] = error
        return jsonify(msg)

# 投票接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/vote/<int:id_>", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxi_vote(id_):
    if request.method == 'POST':#post请求
        msg = {"code": normal_code, "msg": "success"}
        #根据id获取记录
        data= zhiweixinxi.getbyid(zhiweixinxi, zhiweixinxi, int(id_))
        for i in data:
            #增加投票数并更新记录
            votenum=i.get('votenum')
            if votenum!=None:
                params={"id":int(id_),"votenum":votenum+1}
                error=zhiweixinxi.updatebyparams(zhiweixinxi,zhiweixinxi,params)
                if error!=None:
                    msg['code'] = crud_error_code
                    msg['msg'] = error
        return jsonify(msg)

#分组统计接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/group/<columnName>", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_group(columnName):
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        #获取传递的参数
        req_dict = session.get("req_dict")
        limit = 0
        order = ""
        if "limit" in req_dict:
            limit = req_dict["limit"]
            del req_dict["limit"]
        if "order" in req_dict:
            order = req_dict["order"]
            del req_dict["order"]
        userinfo = session.get("params")
        #获取hadoop分析后的数据文件
        json_filename = f'zhiweixinxi_group{columnName}.json'

        if os.path.exists(json_filename) == True:
            with open(json_filename, encoding='utf-8') as f:
                msg['data'] = json.load(f)
        else:
            #查询记录
            msg['data'] = zhiweixinxi.groupbycolumnname(zhiweixinxi,zhiweixinxi,columnName,req_dict)
            msg['data'] = msg['data'][:10]
            msg['data'] = [ {**i,columnName:str(i[columnName])} if columnName in i else i for i in msg['data']]
        #对结果进行升序可降序排序
        if order == "desc":
            msg['data'] = sorted((x for x in msg['data'] if x['total'] is not None),key=lambda x: x['total'],reverse=True)
        elif order == "asc":
            msg['data'] = sorted((x for x in msg['data'] if x['total'] is not None),key=lambda x: x['total'])
        #截取列表个数
        if 0 < int(limit) < len(msg['data']):
            msg['data'] = msg['data'][:int(limit)]
        return jsonify(msg)#返回封装的json结果

# 按值统计接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/value/<xColumnName>/<yColumnName>", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_value(xColumnName, yColumnName):
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        #获取参数
        req_dict = session.get("req_dict")
        limit = 0
        order = ""
        if "limit" in req_dict:
            limit = req_dict["limit"]
            del req_dict["limit"]
        if "order" in req_dict:
            order = req_dict["order"]
            del req_dict["order"]
        userinfo = session.get("params")
        #获取hadoop分析后的数据文件
        json_filename = f'zhiweixinxi_value{xColumnName}{yColumnName}.json'
        if os.path.exists(json_filename) == True:
            with open(json_filename, encoding='utf-8') as f:
                msg['data'] = json.load(f)
        else:
            #查询记录
            msg['data'] = zhiweixinxi.getvaluebyxycolumnname(zhiweixinxi,zhiweixinxi,xColumnName,yColumnName,req_dict)
            msg['data'] = msg['data'][:10]
        #对结果进行升序可降序排序
        if order == "desc":
            msg['data'] = sorted((x for x in msg['data'] if x['total'] is not None),key=lambda x: x['total'],reverse=True)
        elif order == "asc":
            msg['data'] = sorted((x for x in msg['data'] if x['total'] is not None),key=lambda x: x['total'])
        #截取列表个数
        if 0 < int(limit) < len(msg['data']):
            msg['data'] = msg['data'][:int(limit)]
        return jsonify(msg)#返回封装的json结果

# 按日期统计接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/value/<xColumnName>/<yColumnName>/<timeStatType>", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_value_riqi(xColumnName, yColumnName, timeStatType):
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        req_dict = session.get("req_dict")
        #获取hadoop分析后的数据文件
        date_type = ""
        if timeStatType == '日':
            date_type = "date"
        if timeStatType == '月':
            date_type = "month"
        if timeStatType == '季':
            date_type = "quarter"
        if timeStatType == '年':
            date_type = "year"
        json_filename = f'zhiweixinxi_value{xColumnName}{yColumnName}{date_type}.json'

        if os.path.exists(json_filename) == True:
            with open(json_filename, encoding='utf-8') as f:
                msg['data'] = json.load(f)
        else:
            userinfo = session.get("params")
            where = ' where 1 = 1 '
            #定义查询统计语句
            for key, value in req_dict.items():
                if key!="limit" and key!="order":
                    where = where + " and {0} ='{1}' ".format(key,value)
            sql = ''
            if timeStatType == '日':
                sql = "SELECT DATE_FORMAT({0}, '%Y-%m-%d') {0}, sum({1}) total FROM zhiweixinxi {2} GROUP BY DATE_FORMAT({0}, '%Y-%m-%d')".format(xColumnName, yColumnName, where, '%Y-%m-%d')

            if timeStatType == '月':
                sql = "SELECT DATE_FORMAT({0}, '%Y-%m') {0}, sum({1}) total FROM zhiweixinxi {2} GROUP BY DATE_FORMAT({0}, '%Y-%m')".format(xColumnName, yColumnName, where, '%Y-%m')

            if timeStatType == '季':
                sql = "SELECT CONCAT(YEAR(MIN({0})), '-Q', QUARTER(MIN({0}))) AS {0}, SUM({1}) AS total FROM orders {2} GROUP BY YEAR({0}), QUARTER({0})".format(xColumnName, yColumnName, where)

            if timeStatType == '年':
                sql = "SELECT DATE_FORMAT({0}, '%Y') {0}, sum({1}) total FROM zhiweixinxi {2} GROUP BY DATE_FORMAT({0}, '%Y')".format(xColumnName, yColumnName, where, '%Y')
            #执行查询
            data = db.session.execute(sql)
            data = data.fetchall()
            #封装结果
            results = []
            for i in range(len(data)):
                result = {
                    xColumnName: decimalEncoder(data[i][0]),
                    'total': decimalEncoder(data[i][1])
                }
                results.append(result)

            msg['data'] = results
            json_filename='zhiweixinxi'+f'_value_{xColumnName}_{yColumnName}.json'
            with open(json_filename, 'w', encoding='utf-8') as f:
                f.write(json.dumps(results, indent=4, ensure_ascii=False))
            app.executor.submit(upload_to_hdfs, json_filename)
            app.executor.submit(MRMySQLAvg.run)
        req_dict = session.get("req_dict")
        #对结果进行排序
        if "order" in req_dict:
            order = req_dict["order"]
            if order == "desc":
                msg['data'] = sorted((x for x in msg['data'] if x['total'] is not None),key=lambda x: x['total'],reverse=True)
            else:
                msg['data'] = sorted((x for x in msg['data'] if x['total'] is not None),key=lambda x: x['total'])
        #截取列表个数
        if "limit" in req_dict and int(req_dict["limit"]) < len(msg['data']):
            msg['data'] = msg['data'][:int(req_dict["limit"])]
        return jsonify(msg)#返回封装的json结果

# 按值统计（多）
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/valueMul/<xColumnName>", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_valueMul(xColumnName):
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success", "data": []}

        req_dict = session.get("req_dict")
        #获取hadoop分析后的数据文件
        json_filename = f'''zhiweixinxi_value{xColumnName}{req_dict['yColumnNameMul'].replace(",","")}.json'''
        if os.path.exists(json_filename) == True:
            with open(json_filename, encoding='utf-8') as f:
                msg['data'] = json.load(f)
        else:
            userinfo = session.get("params")
            where = ' where 1 = 1 '
            for item in req_dict['yColumnNameMul'].split(','):
                #定义查询语句
                sql = "SELECT {0}, sum({1}) AS total FROM zhiweixinxi {2} GROUP BY {0} LIMIT 10".format(xColumnName, item, where)
                L = []
                #执行查询
                data = db.session.execute(sql)
                data = data.fetchall()
                for i in range(len(data)):
                    result = {
                        xColumnName: decimalEncoder(data[i][0]),
                        'total': decimalEncoder(data[i][1])
                    }
                    L.append(result)
                msg['data'].append(L)
        return jsonify(msg)

# 按值统计（多）
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/valueMul/<xColumnName>/<timeStatType>", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_valueMul_time(xColumnName,timeStatType):
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success", "data": []}

        req_dict = session.get("req_dict")
        #获取hadoop分析后的数据文件
        date_type = ""
        if timeStatType == '日':
            date_type = "date"
        if timeStatType == '月':
            date_type = "month"
        if timeStatType == '季':
            date_type = "quarter"
        if timeStatType == '年':
            date_type = "year"

        json_filename = f'''zhiweixinxi_value{xColumnName}{req_dict['yColumnNameMul'].replace(",","")}{date_type}.json'''

        if os.path.exists(json_filename) == True:
            with open(json_filename, encoding='utf-8') as f:
                msg['data'] = json.load(f)
        else:
            userinfo = session.get("params")
            where = ' where 1 = 1 '
            for item in req_dict['yColumnNameMul'].split(','):
                #定义查询语句
                sql = ''
                if timeStatType == '日':
                    sql = "SELECT DATE_FORMAT({0}, '%Y-%m-%d') {0}, sum({1}) total FROM zhiweixinxi {2} GROUP BY DATE_FORMAT({0}, '%Y-%m-%d') LIMIT 10".format(xColumnName, item, where, '%Y-%m-%d')

                if timeStatType == '月':
                    sql = "SELECT DATE_FORMAT({0}, '%Y-%m') {0}, sum({1}) total FROM zhiweixinxi {2} GROUP BY DATE_FORMAT({0}, '%Y-%m') LIMIT 10".format(xColumnName, item, where, '%Y-%m')

                if timeStatType == '季':
                    sql = "SELECT CONCAT(YEAR(MIN({0})), '-Q', QUARTER(MIN({0}))) {0}, sum({1}) total FROM zhiweixinxi {2} GROUP BY YEAR({0}), QUARTER({0}) LIMIT 10".format(xColumnName, item, where)

                if timeStatType == '年':
                    sql = "SELECT DATE_FORMAT({0}, '%Y') {0}, sum({1}) total FROM zhiweixinxi {2} GROUP BY DATE_FORMAT({0}, '%Y') LIMIT 10".format(xColumnName, item, where, '%Y')
                L = []
                #执行查询
                data = db.session.execute(sql)
                data = data.fetchall()
                for i in range(len(data)):
                    result = {
                        xColumnName: decimalEncoder(data[i][0]),
                        'total': decimalEncoder(data[i][1])
                    }
                    L.append(result)
                msg['data'].append(L)
        return jsonify(msg)

import math
#计算相似度
def cosine_similarity(a, b):
    numerator = sum([a[key] * b[key] for key in a if key in b])
    denominator = math.sqrt(sum([a[key]**2 for key in a])) * math.sqrt(sum([b[key]**2 for key in b]))
    return numerator / denominator

#收藏协同算法
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/autoSort2", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_autoSort2():
    if request.method == 'GET':#get请求
        user_ratings = {}
        req_dict = session.get("req_dict")
        userinfo = session.get("params")
        #查询收藏了的记录
        sql = "select * from storeup where type = 1 and tablename = 'zhiweixinxi' order by addtime desc"
        #执行查询
        data = db.session.execute(sql)
        data_dict = [dict(zip(result.keys(), result)) for result in data.fetchall()]

        for item in data_dict:
            #封装userid、refid的矩阵
            if user_ratings.__contains__(item["userid"]):
                ratings_dict = user_ratings[item["userid"]]
                if ratings_dict.__contains__(item["refid"]):
                    ratings_dict[str(item["refid"])]+=1
                else:
                    ratings_dict[str(item["refid"])] =1
            else:
                user_ratings[item["userid"]] = {
                    str(item["refid"]):1
                }
        sorted_recommended_goods=[]
        try:
            # 计算目标用户与其他用户的相似度
            similarities = {other_user: cosine_similarity(user_ratings[userinfo.get("id")], user_ratings[other_user])
                            for other_user in user_ratings if other_user != userinfo.get("id")}
            # 找到与目标用户最相似的用户
            most_similar_user = sorted(similarities, key=similarities.get, reverse=True)[0]
            # 找到最相似但目标用户未购买过的商品
            recommended_goods = {goods: rating for goods, rating in user_ratings[most_similar_user].items() if
                                 goods not in user_ratings[userinfo.get("id")]}
            # 按评分降序排列推荐
            sorted_recommended_goods = sorted(recommended_goods, key=recommended_goods.get, reverse=True)
        except:
            pass

        L = []
        #按评分顺序查询要推荐列表(当前用户收藏关注过的同类型优先)
        where = " AND ".join([f"{key} = '{value}'" for key, value in req_dict.items() if key!="page" and key!="limit" and key!="order"and key!="sort"])
        if where:
            sql = f'''SELECT * FROM (SELECT * FROM zhiweixinxi WHERE {where}) AS table1 WHERE id IN ('{"','".join(sorted_recommended_goods)}') union all SELECT * FROM (SELECT * FROM zhiweixinxi WHERE {where}) AS table1 WHERE id NOT IN ('{"','".join(sorted_recommended_goods)}')'''
        else:
            sql ="select * from zhiweixinxi where id in ('%s"%("','").join(sorted_recommended_goods)+"') union all select * from zhiweixinxi where id not in('%s"%("','").join(sorted_recommended_goods)+"')"
        #执行查询
        data = db.session.execute(sql)
        #封装结果
        data_dict = [dict(zip(result.keys(), result)) for result in data.fetchall()]
        for online_dict in data_dict:
            for key in online_dict:
                if 'datetime.datetime' in str(type(online_dict[key])):
                    online_dict[key] = online_dict[key].strftime(
                        "%Y-%m-%d %H:%M:%S")
                elif 'datetime' in str(type(online_dict[key])):
                    online_dict[key] = online_dict[key].strftime(
                        "%Y-%m-%d %H:%M:%S")
                else:
                    pass
            L.append(online_dict)
        #返回封装的json结果
        return jsonify({"code": 0, "msg": '',  "data":{"currPage":1,"totalPage":1,"total":1,"pageSize":5,"list": L[0:int(req_dict['limit'])]}})


#查询记录总数量接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/count", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_count():
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success",  "data": 0}
        req_dict = session.get("req_dict")
        userinfo = session.get("params")

        #查询记录个数
        msg['data']  = zhiweixinxi.count(zhiweixinxi, zhiweixinxi, req_dict)
        #返回json结果
        return jsonify(msg)


#获取所有记录列表
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/lists", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxi_lists():
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success", "data": []}
        list,_,_,_,_ = zhiweixinxi.page(zhiweixinxi,zhiweixinxi,{})
        msg['data'] = list
        return jsonify(msg)

import math
#数据清洗接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxi/cleanse", methods=['GET','POST'])
def pythoni2v8cf2c_zhiweixinxi_cleanse():
    if request.method == 'GET' or request.method == 'POST':
        msg = {'code': normal_code, 'message': 'success', 'data': {}}
        try:
            #获取要清理的数据列表
            list, _,_,total,_ = zhiweixinxi.page(zhiweixinxi, zhiweixinxi,{})
            df = pd.DataFrame(list)
            #删除重复
            df = df.drop_duplicates(subset=['gsmc'])
            #随机填充
            df['gslogo'].replace([None, ''], pd.NA,inplace = True)
            gslogo_non_na = df['gslogo'].dropna()  # 获取非空值
            for i in df.index:
                if pd.isna(df.loc[i, 'gslogo']):
                    df.loc[i, 'gslogo'] = gslogo_non_na.sample(n=1,replace=True).values[0]
            #随机填充
            df['jobname'].replace([None, ''], pd.NA,inplace = True)
            jobname_non_na = df['jobname'].dropna()  # 获取非空值
            for i in df.index:
                if pd.isna(df.loc[i, 'jobname']):
                    df.loc[i, 'jobname'] = jobname_non_na.sample(n=1,replace=True).values[0]
            #随机填充
            df['jobarea'].replace([None, ''], pd.NA,inplace = True)
            jobarea_non_na = df['jobarea'].dropna()  # 获取非空值
            for i in df.index:
                if pd.isna(df.loc[i, 'jobarea']):
                    df.loc[i, 'jobarea'] = jobarea_non_na.sample(n=1,replace=True).values[0]
            #随机填充
            df['salary'].replace([None, ''], pd.NA,inplace = True)
            salary_non_na = df['salary'].dropna()  # 获取非空值
            for i in df.index:
                if pd.isna(df.loc[i, 'salary']):
                    df.loc[i, 'salary'] = salary_non_na.sample(n=1,replace=True).values[0]
            #随机填充
            df['fbsj'].replace([None, ''], pd.NA,inplace = True)
            fbsj_non_na = df['fbsj'].dropna()  # 获取非空值
            for i in df.index:
                if pd.isna(df.loc[i, 'fbsj']):
                    df.loc[i, 'fbsj'] = fbsj_non_na.sample(n=1,replace=True).values[0]
            #随机填充
            df['degree'].replace([None, ''], pd.NA,inplace = True)
            degree_non_na = df['degree'].dropna()  # 获取非空值
            for i in df.index:
                if pd.isna(df.loc[i, 'degree']):
                    df.loc[i, 'degree'] = degree_non_na.sample(n=1,replace=True).values[0]
            #随机填充
            df['zwlx'].replace([None, ''], pd.NA,inplace = True)
            zwlx_non_na = df['zwlx'].dropna()  # 获取非空值
            for i in df.index:
                if pd.isna(df.loc[i, 'zwlx']):
                    df.loc[i, 'zwlx'] = zwlx_non_na.sample(n=1,replace=True).values[0]
            #随机填充
            df['gzjy'].replace([None, ''], pd.NA,inplace = True)
            gzjy_non_na = df['gzjy'].dropna()  # 获取非空值
            for i in df.index:
                if pd.isna(df.loc[i, 'gzjy']):
                    df.loc[i, 'gzjy'] = gzjy_non_na.sample(n=1,replace=True).values[0]
            #随机填充
            df['jyyq'].replace([None, ''], pd.NA,inplace = True)
            jyyq_non_na = df['jyyq'].dropna()  # 获取非空值
            for i in df.index:
                if pd.isna(df.loc[i, 'jyyq']):
                    df.loc[i, 'jyyq'] = jyyq_non_na.sample(n=1,replace=True).values[0]
            #将DataFrame 转换为列表
            data_list = df.to_dict(orient='records')
            db.session.query(zhiweixinxi).delete()
            for dl in data_list:
                filtered_data = {k: v for k, v in dl.items() if v not in [None, '', float('nan')] and (not isinstance(v, float) or not math.isnan(v))}
                db.session.add(zhiweixinxi(**filtered_data))
            db.session.commit()
            return jsonify(msg)
        except Exception as e:
            msg["code"] = other_code
            msg["message"] = e.__str__()
            return jsonify(msg)
