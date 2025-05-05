# coding:utf-8
__author__ = "ila"
import json
import logging, os, time
from flask import request, jsonify,session, send_from_directory,redirect
from utils.helper import *
import requests
from api.models.brush_model import *
from . import main_bp
from utils.codes import *
from api.models.config_model import config
from utils.locate import geocoding
from utils.baidubce_api import BaiDuBce
from configs import configs

@main_bp.route("/pythoni2v8cf2c/cal/<tableName>/<columnName>", methods=['GET'])
def pythoni2v8cf2c_cal(tableName, columnName):
    '''
    计算规则接口
    '''
    if request.method == 'GET':
        msg = {"code": normal_code, 'data': []}
        mapping_str_to_object = {}
        for model in Base_model._decl_class_registry.values():
            if hasattr(model, '__tablename__'):
                mapping_str_to_object[model.__tablename__] = model

        data = mapping_str_to_object[tableName].getcomputedbycolumn(
            mapping_str_to_object[tableName],
            mapping_str_to_object[tableName],
            columnName
        )
        if data:
            msg['data'] = {
                "sum": '%.05f' % float(data[0][0]),
                "max": '%.05f' % float(data[0][1]),
                "min": '%.05f' % float(data[0][2]),
                "avg": '%.05f' % float(data[0][3]),
            }

        return jsonify(msg)


@main_bp.route("/pythoni2v8cf2c/file/download", methods=['GET'])
def pythoni2v8cf2c_file_download():
    '''
    '''
    if request.method == 'GET':
        req_dict = session.get("req_dict")
        filename = req_dict.get("fileName")
        filepath = '{}/api/templates/upload'.format(os.getcwd())

        return send_from_directory(filepath, filename, as_attachment=True)

@main_bp.route("/pythoni2v8cf2c/file/upload", methods=['POST'])
def pythoni2v8cf2c_file_upload():
    '''
    '''
    if request.method == 'POST':
        msg = {"code": normal_code, "msg": "success", "data": {}}

        req_dict = session.get("req_dict")
        type = req_dict.get("type")

        file = request.files.get("file")
        if file:
            filename=file.filename
            filesuffix=filename.split(".")[-1]
            file_name="{}.{}".format(int(float(time.time()) * 1000),filesuffix)
            if type != None and '_template' in type:
                file_name="{}.{}".format(type,filesuffix)
            file_path = '{}/api/templates/upload/{}'.format(os.getcwd(),file_name )
            file_path = file_path if "unit_test" not in file_path else file_path.replace("unit_test/", '')
            file.save(file_path)
            msg["file"]=file_name
            #判断是否需要保存为人脸识别基础照片
            type1 = request.args.get("type", 0, type=int)
            if type1==1:
                params = {"faceFile":file_name}
                config.createbyreq(config,config,params)
        return jsonify(msg)


@main_bp.route("/pythoni2v8cf2c/follow/<tableName>/<columnName>/<level>/<parent>", methods=['GET'])
def pythoni2v8cf2c_follow_level(tableName, columnName, level,parent):
    '''
    '''
    if request.method == 'GET':
        msg = {"code": normal_code, 'data': []}
        # 组合查询参数
        params = {
            "level": level,
            "parent":parent
                  }

        mapping_str_to_object = {}
        for model in Base_model._decl_class_registry.values():
            if hasattr(model, '__tablename__'):
                mapping_str_to_object[model.__tablename__] = model

        data = mapping_str_to_object[tableName].getbyparams(
            mapping_str_to_object[tableName],
            mapping_str_to_object[tableName],
            params
        )
        #只需要此列的数据
        for i in data:
            msg['data'].append(i.get(columnName))

        return jsonify(msg)

@main_bp.route("/pythoni2v8cf2c/follow/<tableName>/<columnName>", methods=['GET'])
def pythoni2v8cf2c_follow(tableName, columnName):
    '''
    根据option字段值获取某表的单行记录接口
    组合columnName和columnValue成dict，传入查询方法
    '''
    if request.method == 'GET':
        msg = {"code": normal_code, 'data': []}
        # 组合查询参数
        params=session.get('req_dict')
        columnValue=params.get("columnValue")
        params = {columnName: columnValue}

        mapping_str_to_object = {}
        for model in Base_model._decl_class_registry.values():
            if hasattr(model, '__tablename__'):
                mapping_str_to_object[model.__tablename__] = model

        data = mapping_str_to_object[tableName].getbyparams(
            mapping_str_to_object[tableName],
            mapping_str_to_object[tableName],
            params
        )

        msg['data'] = data[0]
        return jsonify(msg)

@main_bp.route("/pythoni2v8cf2c/location", methods=['GET'])
def pythoni2v8cf2c_location():
    '''

    :return:
    '''
    if request.method == 'GET':
        msg = {"code": normal_code, "msg": "success", "address": ''}
        req_dict = session.get('req_dict')

        datas=config.getbyparams(config,config,{"name":"baidu_ditu_ak"})
        if len(datas)>0:
            baidu_ditu_ak=datas[0].get("baidu_ditu_ak")
        else:
            baidu_ditu_ak='QvMZVORsL7sGzPyTf5ZhawntyjiWYCif'
        lat = req_dict.get("lat", 24.2943350100)
        lon = req_dict.get("lng", 116.1287866600)
        msg['address'] = geocoding(baidu_ditu_ak, lat, lon)

        return jsonify(msg)

@main_bp.route("/pythoni2v8cf2c/matchFace", methods=['GET'])
def pythoni2v8cf2c_matchface():
    '''
    baidubce百度人脸识别
    '''
    if request.method == 'GET':
        msg = {"code": normal_code}
        req_dict = session.get("req_dict")


        face1 = req_dict.get("face1")
        file_path1 = '{}/api/templates/upload/{}'.format(
            os.getcwd(),
            face1
        )

        face2 = req_dict.get("face2")
        file_path2 = '{}/api/templates/upload/{}'.format(
            os.getcwd(),
            face2
        )

        data =config.getbyparams(config,config,{"name":"APIKey"})
        client_id=data[0].get("value")
        data = config.getbyparams(config, config, {"name": "SecretKey"})
        client_secret = data[0].get("value")

        bdb = BaiDuBce()
        score = bdb.bd_check2pic(file_path1, file_path2)
        msg['score'] = score
    return jsonify(msg)

@main_bp.route("/pythoni2v8cf2c/option/<tableName>/<columnName>", methods=['GET'])
def pythoni2v8cf2c_option(tableName, columnName):
    '''
    '''
    if request.method == 'GET':
        msg = {"code": normal_code, 'data': []}

        req_dict = session.get("req_dict")
        if req_dict.get('conditionColumn') != None and req_dict.get('conditionValue') != None:
            req_dict[req_dict['conditionColumn']] = req_dict['conditionValue']
            del req_dict['conditionColumn']
            del req_dict['conditionValue']

        mapping_str_to_object = {}
        for model in Base_model._decl_class_registry.values():
            if hasattr(model, '__tablename__'):
                mapping_str_to_object[model.__tablename__] = model

        data = mapping_str_to_object[tableName].getbyColumn(
            mapping_str_to_object[tableName],
            mapping_str_to_object[tableName],
            getattr(mapping_str_to_object[tableName], columnName),
            req_dict
        )
        # 去重处理（使用集合保证唯一性）
        unique_data = list(set(data)) if data else []
        unique_data.sort(key=lambda x: data.index(x))
        msg['data'] = unique_data
        return jsonify(msg)

@main_bp.route("/pythoni2v8cf2c/remind/<tableName>/<columnName>/<type>", methods=['GET'])  #
def pythoni2v8cf2c_remind(tableName, columnName,type):
    '''
    '''
    if request.method == 'GET':
        msg = {"code": normal_code, 'data': []}
        # 组合查询参数
        params = session.get("req_dict")
        if int(type)==1:#数字
            if params.get('remindStart') == None and params.get('remindEnd') != None:
                params['remindStart'] = 0
            elif params.get('remindStart') != None and params.get('remindEnd') == None:
                params['remindEnd'] = 999999
            elif params.get('remindStart') == None and params.get('remindEnd') == None:
                params['remindStart'] = 0
                params['remindEnd'] = 999999
        elif int(type)==2:#日期
            current_time=int(time.time())
            if params.get('remindStart') == None and params.get('remindEnd') != None:
                starttime=current_time-60*60*24*365*2
                params['remindStart'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(starttime))
                endtime=current_time+60*60*24*params.get('remindEnd')
                params['remindEnd'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(endtime))

            elif params.get('remindStart') != None and params.get('remindEnd') == None:
                starttime= current_time - 60 * 60 * 24 * params.get('remindStart')
                params['remindStart']=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(starttime))
                endtime=current_time+60*60*24*365*2
                params['remindEnd'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(endtime))
            elif params.get('remindStart') == None and params.get('remindEnd') == None:
                starttime = current_time - 60 * 60 * 24 * 365 * 2
                params['remindStart'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(starttime))
                endtime = current_time + 60 * 60 * 24 * 365 * 2
                params['remindEnd'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(endtime))


        mapping_str_to_object = {}
        for model in Base_model._decl_class_registry.values():
            if hasattr(model, '__tablename__'):
                mapping_str_to_object[model.__tablename__] = model


        data = mapping_str_to_object[tableName].getbetweenparams(
            mapping_str_to_object[tableName],
            mapping_str_to_object[tableName],
            getattr(mapping_str_to_object[tableName], columnName),
            params
        )

        msg['data'] = data
        return jsonify(msg)

@main_bp.route("/pythoni2v8cf2c/sh/<tableName>", methods=['POST'])
def pythoni2v8cf2c_sh(tableName):
    '''
    '''
    if request.method == 'POST':
        print('tableName=========>', tableName)
        msg = {"code": normal_code, "msg": "success", "data": {}}
        req_dict = session.get("req_dict")
        mapping_str_to_object = {}
        for model in Base_model._decl_class_registry.values():
            if hasattr(model, '__tablename__'):
                mapping_str_to_object[model.__tablename__] = model
        # 查询结果
        data1 = mapping_str_to_object[tableName].getbyid(
            mapping_str_to_object[tableName],
            mapping_str_to_object[tableName],
            req_dict.get('id')
        )
        if data1.sfsh == '是':
            req_dict['sfsh'] = '否'
        else:
            req_dict['sfsh'] = '否'

        # 更新
        res = mapping_str_to_object[tableName].updatebyparams(
            mapping_str_to_object[tableName],
            mapping_str_to_object[tableName],
            req_dict
        )
        logging.warning("pythoni2v8cf2c_sh.res=====>{}".format(res))
        return jsonify(msg)

@main_bp.route("/pythoni2v8cf2c/upload/<path:filepath>", methods=['GET'])
def pythoni2v8cf2c_upload(filepath):
    '''
    上传接口
    '''
    if request.method == 'GET':
        file_list = filepath.rsplit('/', 1)
        if len(file_list)>=2:
            filepath = f'{os.getcwd()}/api/templates/upload/{file_list[0]}/'
            return send_from_directory(filepath, file_list[1])
        else:
            filepath = f'{os.getcwd()}/api/templates/upload/'
            return send_from_directory(filepath, file_list[0])

@main_bp.route("/pythoni2v8cf2c/group/<tableName>/<columnName>", methods=['GET'])
def schema_group_quyu(tableName,columnName):
    '''
    '''
    if request.method == 'GET':
        msg = {"code": normal_code, "msg": "success", "data": {}}
        mapping_str_to_object = {}
        for model in Base_model._decl_class_registry.values():
            if hasattr(model, '__tablename__'):
                mapping_str_to_object[model.__tablename__] = model
        msg['data'] = mapping_str_to_object[tableName].groupbycolumnname(
        mapping_str_to_object[tableName],
        mapping_str_to_object[tableName],
        columnName
        )
        return jsonify(msg)

@main_bp.route("/pythoni2v8cf2c/value/<tableName>/<xColumnName>/<yColumnName>", methods=['GET'])
def schema_value_quyu(tableName,xColumnName,yColumnName):
    '''
    按值统计接口,
    {
    "code": 0,
    "data": [
        {
            "total": 10.0,
            "shangpinleibie": "aa"
        },
        {
            "total": 20.0,
            "shangpinleibie": "bb"
        },
        {
            "total": 15.0,
            "shangpinleibie": "cc"
        }
    ]
}
    '''
    if request.method == 'GET':
        msg = {"code": normal_code, "msg": "success", "data": {}}
        mapping_str_to_object = {}
        for model in Base_model._decl_class_registry.values():
            if hasattr(model, '__tablename__'):
                mapping_str_to_object[model.__tablename__] = model
        msg['data'] = mapping_str_to_object[tableName].getvaluebyxycolumnname(
        mapping_str_to_object[tableName],
        mapping_str_to_object[tableName],
        xColumnName,
        yColumnName
        )
        return jsonify(msg)

# 爬取数据
@main_bp.route("/pythoni2v8cf2c/spider/<tableName>", methods=['GET'])
def schema_spider(tableName):
    msg = {"code": normal_code, "msg": "success", "data": []}

    # Linux
    cmd = "cd /yykj/python/9999/spidere7mzzleh && scrapy crawl "+tableName+"Spider -a databaseName=pythoni2v8cf2c"
    # Windows
    # cmd = "cd C:\\test1\\spider && scrapy crawl " + tableName + "Spider -a databaseName=pythoni2v8cf2c"
    os.system(cmd)

    return jsonify(msg)



