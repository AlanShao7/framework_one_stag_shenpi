from enum import Enum


class EntrySet:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class DynamicEnum(Enum):
    # 动态枚举方法，获取动态枚举值
    @classmethod
    def dynamic(cls, value):
        return EntrySet(DynamicEnum, {cls._key.value: value})


class IBuilder:
    # 动态参数构造器
    def builder(self, **kwargs):
        [self.__setattr__(k, v) for k, v in kwargs.items()]
        return self


class IWrapper:
    # 委托类型
    def __init__(self, delegate):
        self.wrapper = delegate

    def __getattr__(self, item):
        return getattr(self.wrapper, item)


class IStringify:
    # 指定属性构造显示串
    @property
    def stringify(self):
        return "；".join(["%s：%s" % (attr, getattr(self, attr)) for attr in self.stringifies if hasattr(self, attr)])

    @stringify.setter
    def stringify(self, stringifies):
        self.stringifies = stringifies

    def __str__(self):
        return self.stringify if hasattr(self, "stringifies") else super().__str__()
