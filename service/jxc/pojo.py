from enum import Enum, unique, IntEnum
from component.oauth import BaseUserPo


class UserPo(BaseUserPo):
    def __init__(self, dict_user, organization, factory):
        self.dict_user = dict_user
        [self.__setattr__(k, v) for k, v in dict_user.items()]
        self.factory = factory
        self.db_session = self.factory.server.db.session

        if not hasattr(self, "oauth_klass"):
            # 用于处理pc的情况
            # 如果本身包含oauth，则使用oauth
            # 否则使用server提供的oauth
            self.oauth_klass = self.factory.oauth_klass

        self.stringify = ["uid"]


class Warehouse:
    #  仓库，key：仓库名称,value：仓库id
    warehouses = {314: 329, 315: 330}

    def __init__(self, name):
        self.name = int(name)
        self.id = self.warehouses[self.name]



@unique
class EnumCustomer(IntEnum):
    张海艳 = 6799


@unique
class EnumSeller(IntEnum):
    张海艳 = 1000013611
    施亮赜 = 1000013625
    王乐 = 1000013612
