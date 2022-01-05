import logging
import random
import re
import string

# 公共工具类组件，提供各种定制化工具
import types
from enum import Enum

from component.interface import IWrapper


class EnumRegx(Enum):
    # 数字正则
    NUMBER = r"^[-+]?[0-9]+\.[0-9]+$"


class Strings:
    def __init__(self, str_arg):
        self.arg = str(str_arg)

    def is_number(self):
        return re.compile(EnumRegx.NUMBER.value).match(self.arg)

    def set_default(self, default):
        list_judgment = list()
        # 是否空/None/空数组/空字典
        list_judgment.append(self.arg)
        # 是否无穷大
        list_judgment.append(self.arg == self.arg)
        # 非空值、有穷值，所有条件皆满足感，返回原值，否则返回默认值
        return self.arg if all(list_judgment) else default


class Random:
    # 随机数工具类

    def __init__(self, boolean_number=True, boolean_lower_case=True, boolean_upper_case=True):
        # 初始化随机数工具
        # 可选参数：
        # boolean_number：生成的随机数是否包含数字
        # boolean_lower_case：生成的随机数是否包含小写字母
        # boolean_upper_case：生成的随机数是否包含大写字母
        self.__universal_set = ""
        if boolean_number: self.__universal_set += string.digits
        if boolean_lower_case: self.__universal_set += string.ascii_lowercase
        if boolean_upper_case: self.__universal_set += string.ascii_uppercase

    def return_sample(self, int_number):
        # 放回抽样：返回的字符串按照放回抽样随机，可以重复
        # int_number：生成的数组长度，长度不限，因为是放回抽样，生成长度可大于样本
        return "".join([random.choice(self.__universal_set) for n in range(int_number)])


class Arrays:
    # def __init__(self, list_input):
    #     self.list_input = list_input

    # def dimensionality_reduction(self, list_input):
    #     # 如果该维度的孙子元素都是数组，对下一级进行降维
    #     if all([all([list == type(i) for i in input]) for input in list_input]):
    #         return [self.dimensionality_reduction(input) for input in list_input]
    #     else:
    #         l = list()
    #         [l.append(input) for input in list_input]
    #         return l

    # 二向箔，任意维数组转换成二维数组
    def dual_vector_foil(self, list_input):
        list_result = list()
        self.__expansion(list_result, list_input)
        return list_result

    def __expansion(self, list_result, element):
        if list == type(element):
            [self.__expansion(list_result, e) for e in element]
        else:
            list_result.append(element)

    # 多个数组生成正交表
    # 该方法临时用，未来应该用numpy或pandas实现
    def orthogonal_table(self, **kwargs):
        list_results = list()
        # 第一步：构建正交表
        # 遍历所有key和value
        for key, values in kwargs.items():
            for value in values:
                list_results.append({key: value})
        # 第二步：遍历正交表补充正交表中其余部分
        for result in list_results:
            # 遍历kwargs，补充正交表其余部分
            for key, values in kwargs.items():
                result.setdefault(key, values[0])

        return  list_results


class Contains:
    # 包含关系判断类
    def __init__(self, sup):
        self.sup = sup
        logging.info("包含关系比较：父集合：%s" % self.sup)

    # 字典包含
    def dict(self, sub):
        logging.info("字典包含关系比较：子集合：%s" % sub)
        if isinstance(sub, dict):
            #  遍历sub，每个sub元素都满足Contains(self.sup[k]).scalar(v)
            return all([Contains(self.sup[k]).scalar(v) for k, v in sub.items()])
        else:
            return False

    # 数组包含
    def list(self, sub):
        logging.info("数组包含关系比较：子集合：%s" % sub)
        if any([isinstance(sub, t) for t in [list, tuple]]):
            # 外层：遍历sub，每个sub元素都属于self.sup
            # 内层：遍历self.sup，至少一个sup元素能满足[Contains(p).scalar(b)
            return all([any([Contains(p).scalar(b) for p in self.sup]) for b in sub])
        else:
            return False

    # 标量
    def scalar(self, sub):
        if isinstance(self.sup, dict):
            return self.dict(sub)
        elif any([isinstance(self.sup, t) for t in [list, tuple]]):
            return self.list(sub)
        # 标量比较
        if Strings(self.sup).is_number() and Strings(sub).is_number():
            logging.info("数字相等关系比较：子集合：%s" % sub)
            return float(self.sup) == float(sub)
        else:
            logging.info("字符串相等关系比较：子集合：%s" % sub)
            return self.sup == sub


class Equals:
    # 相等关系判断类
    def __init__(self, sup):
        self.sup = sup
        logging.info("相等关系比较：父集合：%s" % self.sup)

    # 字典相等
    def dict(self, sub):
        logging.info("字典相等关系比较：子集合：%s" % sub)
        if isinstance(sub, dict) and len(self.sup) == len(sub):
            # dict的key不允许相同
            # 当两个dict长度相等，且遍历dict1的key，都有dict2与之对应，且value相等，即可判定两个dict全等
            return all([Contains(self.sup[k]).scalar(v) for k, v in sub.items()])
        else:
            return False

    def list(self, sub):
        logging.info("数组相等关系比较：子集合：%s" % sub)
        if any([isinstance(sub, t) for t in [list, tuple]]) and len(self.sup) == len(sub):
            # 遍历sub，是否每个元素都∈self.sup
            # 当sup与sub长度相同，且不放回抽全等校验通过，则判定该两个数组全等
            return all([self.contain_pop(b) for b in sub])
        else:
            return False

    def contain_pop(self, element):
        # self.sup由response.json()生成，不可能是tuple，所以可以用pop
        # 判断element是否∈self.sup
        for p in self.sup:
            if Equals(p).scalar(element):
                self.sup.remove(p)
                return True
        # for运行完毕，仍未匹配成功，则返回false
        return False

    def scalar(self, sub):
        if isinstance(self.sup, dict):
            return self.dict(sub)
        elif any([isinstance(self.sup, t) for t in [list, tuple]]):
            return self.list(sub)
        # 标量比较
        elif Strings(self.sup).is_number() and Strings(sub).is_number():
            logging.info("数字相等关系比较：子集合：%s" % sub)
            return float(self.sup) == float(sub)
        else:
            logging.info("字符串相等关系比较：子集合：%s" % sub)
            return self.sup == sub
