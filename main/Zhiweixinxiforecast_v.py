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
import joblib
import pymysql
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 在导入pyplot之前设置
from matplotlib import pyplot as plt
from utils.configread import config_read
import os
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler, MinMaxScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error,accuracy_score
from sklearn.feature_extraction import DictVectorizer
from sklearn.tree import DecisionTreeClassifier, export_graphviz
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import classification_report, confusion_matrix,confusion_matrix, mean_squared_error, mean_absolute_error, r2_score
from sklearn.tree import DecisionTreeClassifier, export_graphviz
import seaborn as sns

pd.options.mode.chained_assignment = None  # default='warn'
#获取当前文件路径的根目录
parent_directory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dbtype, host, port, user, passwd, dbName, charset,hasHadoop = config_read(os.path.join(parent_directory,"config.ini"))
#MySQL连接配置
mysql_config = {
    'host': host,
    'user':user,
    'password': passwd,
    'database': dbName,
    'port':port
}

#获取预测可视化图表接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/forecastimgs", methods=['GET','POST'])
def zhiweixinxiforecast_forecastimgs():
    if request.method in ["POST", "GET"]:
        msg = {'code': normal_code, 'message': 'success'}
        # 指定目录
        directory = os.path.join(parent_directory, "api", "templates", "upload", "zhiweixinxiforecast")
        # 获取目录下的所有文件和文件夹名称
        all_items = os.listdir(directory)
        # 过滤出文件（排除文件夹）
        files = [f'upload/zhiweixinxiforecast/{item}' for item in all_items if os.path.isfile(os.path.join(directory, item))]
        msg["data"] = files
        return jsonify(msg)

@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/forecast", methods=['GET','POST'])
#预测接口
def zhiweixinxiforecast_forecast():
    import datetime
    if request.method in ["POST", "GET"]:#get、post请求
        msg = {'code': normal_code, 'message': 'success'}
        #获取数据集
        req_dict = session.get("req_dict")
        connection = pymysql.connect(**mysql_config)
        query = "SELECT jobname,gzjy,degree, salary FROM zhiweixinxi"
        #处理缺失值
        data = pd.read_sql(query, connection).dropna()
        id = req_dict.pop('id',None)
        req_dict.pop('addtime',None)
        df = to_forecast(data,req_dict,None)
        #创建数据库连接,将DataFrame 插入数据库
        connection_string = f"mysql+pymysql://{mysql_config['user']}:{mysql_config['password']}@{mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}"
        engine = create_engine(connection_string)
        try:
            if req_dict :
                #遍历 DataFrame，并逐行更新数据库
                with engine.connect() as connection:
                    for index, row in df.iterrows():
                        sql = """
                        INSERT INTO zhiweixinxiforecast (id
                        ,salary
                        )
                        VALUES (%(id)s
                    ,%(salary)s
                        )
                        ON DUPLICATE KEY UPDATE
                        salary = VALUES(salary)
                        """
                        connection.execute(sql, {'id': id
                            , 'salary': row['salary']
                        })
            else:
                df.to_sql('zhiweixinxiforecast', con=engine, if_exists='append', index=False)
            print("数据更新成功！")
        except Exception as e:
            print(f"发生错误: {e}")
        finally:
            engine.dispose()  # 关闭数据库连接
        return jsonify(msg)

#训练数据并进行预测
def to_forecast(data,req_dict,value):
    if len(data) < 5:
        print(f"的样本数量不足: {len(data)}")
        return pd.DataFrame()
    #处理特征值和目标值
    labels={}
    for key in data.keys():
        if pd.api.types.is_string_dtype(data[key]):
            label_encoder = LabelEncoder()
            labels[key] = label_encoder
            data[key] = label_encoder.fit_transform(data[key])
    #数据集划分
    X = data[[
        'jobname',
        'gzjy',
        'degree',
    ]]
    y = data[[
        'salary',
    ]]
    x_train, x_test, y_train, y_test = train_test_split(X, y,test_size=0.2, random_state=22)
    #构建预测特征值
    #根据输入的特征值去预测
    if req_dict:
        req_dict.pop('addtime',None)
        future_df = pd.DataFrame([req_dict])
        for key in future_df.keys():
           if key in labels:
               encoder = labels[key]
               values = future_df[key][0]
               try:
                   values = encoder.transform([values])[0]
               except ValueError as e: #处理未见过的标签
                   values = np.array([encoder.transform([v])[0] if v in encoder.classes_ else -1 for v in values]).sum()
               future_df[key][0] = values
    else:
        future_df = x_test
    #特征工程-标准化
    estimator_file = os.path.join(parent_directory, "zhiweixinxiforecast.pkl")
    estimator = RandomForestRegressor(n_estimators=100, random_state=42)
    _, num_columns = y_train.shape
    if num_columns>=2:
        estimator.fit(x_train, y_train)
    else:
        estimator.fit(x_train, y_train.values.ravel())
    y_pred = estimator.predict(x_test)
    plt.rcParams['font.sans-serif'] = ['SimHei','simhei']  # 使用黑体 SimHei
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号 '-' 显示为方块的问题
    # 绘制预测值与实际值的散点图
    plt.scatter(y_test, y_pred, alpha=0.5)
    plt.xlabel("实际值")
    plt.ylabel("预测值")
    plt.title("实际值与预测值(随机森林回归)")
    directory =os.path.join(parent_directory,"api", "templates","upload","zhiweixinxiforecast","figure.png")
    os.makedirs(os.path.dirname(directory), exist_ok=True)
    plt.savefig(directory)
    plt.clf()
    # 绘制特征重要性
    feature_importances = estimator.feature_importances_
    features = [
        'jobname',
        'gzjy',
        'degree',
    ]
    plt.figure(figsize=(8, 4))
    sns.barplot(x=feature_importances, y=features)
    plt.xlabel("重要性得分")
    plt.ylabel("特征")
    plt.title("特征重要性")
    if value!=None:
        directory =os.path.join(parent_directory,"api", "templates","upload","zhiweixinxiforecast","{value}_figure.png")
        os.makedirs(os.path.dirname(directory), exist_ok=True)
        plt.savefig(directory)
    else:
        directory =os.path.join(parent_directory,"api", "templates","upload","zhiweixinxiforecast","figure_other.png")
        os.makedirs(os.path.dirname(directory), exist_ok=True)
        plt.savefig(directory)
    plt.clf()
    #保存模型
    joblib.dump(estimator, estimator_file)

    y_pred  = estimator.predict(x_test)

    comparison_df = pd.DataFrame({'实际值': y_test.values.flatten(), '预测值': y_pred.flatten()})
    comparison_df = comparison_df.sort_values(by='实际值')  # 按实际销量排序，方便可视化

    # 绘制实际值 vs 预测值散点图
    plt.figure(figsize=(10, 6))
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体 SimHei
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号 '-' 显示为方块的问题
    sns.scatterplot(x=comparison_df['实际值'], y=comparison_df['预测值'], color='blue', label='预测值')
    plt.plot([comparison_df['实际值'].min(), comparison_df['实际值'].max()],
             [comparison_df['实际值'].min(), comparison_df['实际值'].max()],
             color='red', linestyle='--', label='完美预测线')
    plt.xlabel('实际值')
    plt.ylabel('预测值')
    plt.title('实际值 vs 预测值')
    plt.legend()
    directory =os.path.join(parent_directory, "api","templates","upload","zhiweixinxiforecast","figure.png")
    os.makedirs(os.path.dirname(directory), exist_ok=True)
    plt.savefig(directory)
    plt.clf()

    #进行预测
    y_predict = estimator.predict(future_df)
    if isinstance(y_predict[0], numbers.Number) or len(y_predict[0])<2:
        y_predict = np.mean(y_predict, axis=0)
        if not isinstance(y_predict, np.ndarray):
            y_predict = np.expand_dims(y_predict, axis=0)
    df = pd.DataFrame(y_predict, columns=[
        'salary',
    ])
    df['salary']=df['salary'].astype(int)
    df['salary'] = labels['salary'].inverse_transform(df['salary'])
    plt.close()
    return df

# 注册接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/register", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxiforecast_register():
    if request.method == 'POST':#post请求
        msg = {'code': normal_code, 'message': 'success', 'data': [{}]}
        req_dict = session.get("req_dict")


        #创建新用户数据
        error = zhiweixinxiforecast.createbyreq(zhiweixinxiforecast, zhiweixinxiforecast, req_dict)
        if error!=None and error is Exception:
            msg['code'] = crud_error_code
            msg['msg'] = "注册用户已存在"
        else:
            msg['data'] = error
        #返回结果
        return jsonify(msg)

# 登录接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/login", methods=['GET','POST'])
def pythoni2v8cf2c_zhiweixinxiforecast_login():
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
        datas = zhiweixinxiforecast.getbyparams(zhiweixinxiforecast, zhiweixinxiforecast, req_model)
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
        return Auth.authenticate(Auth, zhiweixinxiforecast, req_dict)


# 登出接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/logout", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxiforecast_logout():
    if request.method == 'POST':#post请求
        msg = {
            "msg": "退出成功",
            "code": 0
        }
        req_dict = session.get("req_dict")

        return jsonify(msg)

# 重置密码接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/resetPass", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxiforecast_resetpass():
    if request.method == 'POST':#post请求
        msg = {"code": normal_code, "msg": "success"}
        #获取传递的参数
        req_dict = session.get("req_dict")

        if req_dict.get('mima') != None:
            req_dict['mima'] = '123456'
        #更新重置后的密码
        error = zhiweixinxiforecast.updatebyparams(zhiweixinxiforecast, zhiweixinxiforecast, req_dict)

        if error != None:
            msg['code'] = crud_error_code
            msg['msg'] = error
        else:
            msg['msg'] = '密码已重置为：123456'
        return jsonify(msg)

# 获取会话信息接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/session", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxiforecast_session():
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "data": {}}
        #获取token里的id，查找对应的用户数据返回
        req_dict={"id":session.get('params').get("id")}
        msg['data']  = zhiweixinxiforecast.getbyparams(zhiweixinxiforecast, zhiweixinxiforecast, req_dict)[0]

        return jsonify(msg)

# 分类接口（后端）
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/page", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxiforecast_page():
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success",  "data":{"currPage":1,"totalPage":1,"total":1,"pageSize":10,"list":[]}}
        #获取传递的参数
        req_dict = session.get("req_dict")
        userinfo = session.get("params")
        try:#判断是否有消息
            __hasMessage__=zhiweixinxiforecast.__hasMessage__
        except:
            __hasMessage__=None
        if __hasMessage__ and __hasMessage__!="否":
            tablename=session.get("tablename")
            if tablename!="users" and session.get("params")!=None and zhiweixinxiforecast!='chat':
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
            if  __isAdmin__ == "是" and 'zhiweixinxiforecast' != 'forum':
                if req_dict.get("userid") and 'zhiweixinxiforecast' != 'chat':
                    del req_dict["userid"]
            else:
                #非管理员权限的表,判断当前表字段名是否有userid
                if tablename!="users" and 'zhiweixinxiforecast'[:7]!='discuss'and "userid" in zhiweixinxiforecast.getallcolumn(zhiweixinxiforecast,zhiweixinxiforecast):
                    req_dict["userid"] = session.get("params").get("id")

        clause_args = []
        or_clauses = or_(*clause_args)
        #查询列表数据
        msg['data']['list'], msg['data']['currPage'], msg['data']['totalPage'], msg['data']['total'], \
        msg['data']['pageSize']  = zhiweixinxiforecast.page(zhiweixinxiforecast, zhiweixinxiforecast, req_dict, or_clauses)
        return jsonify(msg)

# 排序接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/autoSort", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxiforecast_autosort():
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success",  "data":{"currPage":1,"totalPage":1,"total":1,"pageSize":10,"list":[]}}
        #获取传递的参数
        req_dict = session.get("req_dict")
        req_dict['sort']='clicktime'
        req_dict['order']='desc'

        try:#获取需要排序的内容
            __browseClick__= zhiweixinxiforecast.__browseClick__
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
        msg['data']['pageSize']  = zhiweixinxiforecast.page(zhiweixinxiforecast, zhiweixinxiforecast, req_dict)

        return jsonify(msg)

#查询单条数据
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/query", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxiforecast_query():
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success",  "data":{}}
        #获取传递的参数，根据参数获取单条结果
        req_dict = session.get("req_dict")
        query = db.session.query(zhiweixinxiforecast)
        for key, value in req_dict.items():
            query = query.filter(getattr(zhiweixinxiforecast, key) == value)
        query_result = query.first()
        query_result.__dict__.pop('_sa_instance_state', None)
        msg['data'] = query_result.__dict__
        return jsonify(msg)

# 分页接口（前端）
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/list", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxiforecast_list():
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success",  "data":{"currPage":1,"totalPage":1,"total":1,"pageSize":10,"list":[]}}
        #获取传递的参数
        req_dict = session.get("req_dict")
        if req_dict.__contains__('vipread'):
            del req_dict['vipread']
            
        userinfo = session.get("params")

        try:#判断是否有列表权限
            __foreEndListAuth__=zhiweixinxiforecast.__foreEndListAuth__
        except:
            __foreEndListAuth__=None
        #不需要权限判断就去掉userid
        if __foreEndListAuth__ and __foreEndListAuth__!="否":
            tablename=session.get("tablename")
            if tablename!="users" and session.get("params")!=None:
                req_dict['userid']=session.get("params").get("id")

        tablename=session.get("tablename")

        if 'luntan' in 'zhiweixinxiforecast':
            if 'userid' in req_dict.keys():
                del req_dict["userid"]

        if 'discuss' in 'zhiweixinxiforecast':
            if 'userid' in req_dict.keys():
                del req_dict["userid"]
        #根据封装的req_dict字典去筛选获取列表数据
        msg['data']['list'], msg['data']['currPage'], msg['data']['totalPage'], msg['data']['total'], \
        msg['data']['pageSize']  = zhiweixinxiforecast.page(zhiweixinxiforecast, zhiweixinxiforecast, req_dict)
        return jsonify(msg)

# 保存接口（后端）
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/save", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxiforecast_save():
    if request.method == 'POST':#post请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        #获取传递的参数
        req_dict = session.get("req_dict")
        for key in req_dict:#将空值转为None
            if req_dict[key] == '':
                req_dict[key] = None

        #保存数据
        error= zhiweixinxiforecast.createbyreq(zhiweixinxiforecast, zhiweixinxiforecast, req_dict)
        if error!=None and error is Exception:
            msg['code'] = crud_error_code
            msg['msg'] = error
        else:
            msg['data'] = error
        return jsonify(msg)

# 添加接口（前端）
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/add", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxiforecast_add():
    if request.method == 'POST':#post请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        #获取参数
        req_dict = session.get("req_dict")
        #判断用户权限
        try:
            __foreEndListAuth__=zhiweixinxiforecast.__foreEndListAuth__
        except:
            __foreEndListAuth__=None
        #不需要权限则去掉userid
        if __foreEndListAuth__ and __foreEndListAuth__!="否":
            tablename=session.get("tablename")
            if tablename!="users":
                req_dict['userid']=session.get("params").get("id")

        #保存数据
        error= zhiweixinxiforecast.createbyreq(zhiweixinxiforecast, zhiweixinxiforecast, req_dict)
        if error!=None and error is Exception:
            msg['code'] = crud_error_code
            msg['msg'] = error
            return jsonify(msg)
        else:
            msg['data'] = error
        return jsonify(msg)

# 踩、赞接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/thumbsup/<id_>", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxiforecast_thumbsup(id_):
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        req_dict = session.get("req_dict")
        id_=int(id_)
        type_=int(req_dict.get("type",0))
        #获取要踩赞的记录
        rets=zhiweixinxiforecast.getbyid(zhiweixinxiforecast, zhiweixinxiforecast,id_)
        update_dict={
            "id":id_,
        }
        #加减数据
        if type_==1:#赞
            update_dict["thumbsupnum"]=int(rets[0].get('thumbsupnum'))+1
        elif type_==2:#踩
            update_dict["crazilynum"]=int(rets[0].get('crazilynum'))+1
        #更新记录
        error = zhiweixinxiforecast.updatebyparams(zhiweixinxiforecast, zhiweixinxiforecast, update_dict)
        if error!=None:
            msg['code'] = crud_error_code
            msg['msg'] = error
        return jsonify(msg)

# 获取详情信息（后端）
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/info/<id_>", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxiforecast_info(id_):
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        #根据id获取对应记录
        data = zhiweixinxiforecast.getbyid(zhiweixinxiforecast, zhiweixinxiforecast, int(id_))
        if len(data)>0:
            msg['data']=data[0]
        #浏览点击次数
        try:
            __browseClick__= zhiweixinxiforecast.__browseClick__
        except:
            __browseClick__=None

        if __browseClick__  and  "clicknum"  in zhiweixinxiforecast.__table__.columns:
            click_dict={"id":int(id_),"clicknum":str(int(data[0].get("clicknum") or 0)+1)}#增加点击次数
            ret=zhiweixinxiforecast.updatebyparams(zhiweixinxiforecast,zhiweixinxiforecast,click_dict)#更新记录
            if ret!=None:
                msg['code'] = crud_error_code
                msg['msg'] = ret
        return jsonify(msg)

# 获取详情信息（前端）
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/detail/<id_>", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxiforecast_detail(id_):
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        #根据id获取对应记录
        data = zhiweixinxiforecast.getbyid(zhiweixinxiforecast, zhiweixinxiforecast, int(id_))
        if len(data)>0:
            msg['data']=data[0]

        #浏览点击次数
        try:
            __browseClick__= zhiweixinxiforecast.__browseClick__
        except:
            __browseClick__=None

        if __browseClick__ and "clicknum" in zhiweixinxiforecast.__table__.columns:
            click_dict={"id":int(id_),"clicknum":str(int(data[0].get("clicknum") or 0)+1)}#增加点击次数
            ret=zhiweixinxiforecast.updatebyparams(zhiweixinxiforecast,zhiweixinxiforecast,click_dict)#更新记录
            if ret!=None:
                msg['code'] = crud_error_code
                msg['msg'] = ret
        return jsonify(msg)

# 更新接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/update", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxiforecast_update():
    if request.method == 'POST':#post请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        req_dict = session.get("req_dict")
        #如果存在密码或点击次数则不更新
        if req_dict.get("mima") and "mima" not in zhiweixinxiforecast.__table__.columns :
            del req_dict["mima"]
        if req_dict.get("password") and "password" not in zhiweixinxiforecast.__table__.columns :
            del req_dict["password"]
        try:
            del req_dict["clicknum"]
        except:
            pass

        #更新记录
        error = zhiweixinxiforecast.updatebyparams(zhiweixinxiforecast, zhiweixinxiforecast, req_dict)
        if error!=None:
            msg['code'] = crud_error_code
            msg['msg'] = error

        return jsonify(msg)

# 删除接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/delete", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxiforecast_delete():
    if request.method == 'POST':#post请求
        msg = {"code": normal_code, "msg": "success", "data": {}}
        req_dict = session.get("req_dict")
        #删除记录
        error=zhiweixinxiforecast.delete(
            zhiweixinxiforecast,
            req_dict
        )
        if error!=None:
            msg['code'] = crud_error_code
            msg['msg'] = error
        return jsonify(msg)

# 投票接口
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/vote/<int:id_>", methods=['POST'])
def pythoni2v8cf2c_zhiweixinxiforecast_vote(id_):
    if request.method == 'POST':#post请求
        msg = {"code": normal_code, "msg": "success"}
        #根据id获取记录
        data= zhiweixinxiforecast.getbyid(zhiweixinxiforecast, zhiweixinxiforecast, int(id_))
        for i in data:
            #增加投票数并更新记录
            votenum=i.get('votenum')
            if votenum!=None:
                params={"id":int(id_),"votenum":votenum+1}
                error=zhiweixinxiforecast.updatebyparams(zhiweixinxiforecast,zhiweixinxiforecast,params)
                if error!=None:
                    msg['code'] = crud_error_code
                    msg['msg'] = error
        return jsonify(msg)




#获取所有记录列表
@main_bp.route("/pythoni2v8cf2c/zhiweixinxiforecast/lists", methods=['GET'])
def pythoni2v8cf2c_zhiweixinxiforecast_lists():
    if request.method == 'GET':#get请求
        msg = {"code": normal_code, "msg": "success", "data": []}
        list,_,_,_,_ = zhiweixinxiforecast.page(zhiweixinxiforecast,zhiweixinxiforecast,{})
        msg['data'] = list
        return jsonify(msg)

