#coding:utf-8
import hashlib
import decimal
from Crypto.Cipher import DES,AES
from Crypto.Util.Padding import pad,unpad
import base64

def computeMD5(message):
    """
    计算字符串的MD5哈希值
    :param message: 输入字符串
    :return: MD5哈希值的十六进制字符串表示（32字符）
    """
    m = hashlib.md5()
    m.update(message.encode(encoding='utf-8'))
    return m.hexdigest()


def decimalEncoder(o):
    """
    JSON序列化Decimal类型转换器（将Decimal转为float）
    :param o: 需要序列化的对象
    :return: 可序列化的float类型
    """
    if isinstance(o, decimal.Decimal):
        return float(o)
    return o

def BytesEncoder(o):
    """
    JSON序列化bytes类型转换器（将bytes转为UTF-8字符串）
    :param o: 需要序列化的对象
    :return: 可序列化的字符串类型
    """
    if isinstance(o, bytes):
        return str(o, encoding='utf-8')
    return o


if __name__=='__main__':
    result = computeMD5('123456')
    print(result)