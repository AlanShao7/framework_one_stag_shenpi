from os import path

import pandas
from enum import IntEnum, unique

import yaml

from component.db_utils.config import DbConfig
from component.interface import IBuilder


@unique
class EnvironmentEnum(IntEnum):
    TEST = 1
    STAGE = 2
    私有化 = 99


@unique
class PlatformEnum(IntEnum):
    钉钉 = 1
    励销 = 2
    PC = 3
    ANDROID = 4
    IOS = 5


@unique
class ServerEnum(IntEnum):
    UC = 0
    CRM = 1
    JXC = 2
    SKB = 3


class Config:
    #   配置文件读取类
    def __init__(self, str_path):
        self.str_path = str_path
        with open(str_path, "r", encoding="utf-8") as f:
            self.dict_config = yaml.load(f.read(), Loader=yaml.FullLoader)

        # 当前运行设置：
        self.dict_setting = self.dict_config["setting"]
        self.enum_server = ServerEnum[self.dict_setting["server"]]
        self.enum_environment = EnvironmentEnum[self.dict_setting["environment"]]
        self.enum_platform = PlatformEnum[self.dict_setting["platform"]]
        # server配置
        self.dict_server = self.dict_config["SERVER"]
        # platform默认值
        self.dict_platform = self.dict_config["PLATFORM"]

        self.server = self.Server(config=self, dict_environment=self.dict_server[self.enum_server.name])
        self.uc = self.Server(config=self, dict_environment=self.dict_server["UC"], enum_platform=PlatformEnum.PC)

    class Server:
        # Server嵌套类
        def __init__(self, config, dict_environment, enum_platform=None):
            self.config = config
            self.dict_environment = dict_environment
            self.enum_environment = self.config.enum_environment
            self.enum_platform = enum_platform or self.config.enum_platform

            self.environment = self.Environment(server=self, dict_platform=self.dict_environment[self.enum_environment.name])

        class Environment:
            def __init__(self, server, dict_platform):
                self.server = server
                self.dict_platform = dict_platform
                self.enum_platform = self.server.enum_platform

                self.platform_kwargs = self.dict_platform[self.enum_platform.name] or {}
                self.platform_template = self.server.config.dict_platform.setdefault(self.enum_platform.name, {})

                self.platform = self.Platform(environment=self, kwargs=self.platform_kwargs, template=self.platform_template)

            class Platform(IBuilder):
                def __init__(self, environment, kwargs, template):
                    self.environment = environment
                    self.template = template
                    # 首先用template赋值装填基础数据
                    self.builder(**template)
                    # 如果字典中无attr_pointer，则默认值必有attr_pointer，否则配置错误
                    # 用pop，避免后续遍历时再次覆盖attr_pointer的枚举值
                    self.attr_pointer = PlatformEnum[kwargs.pop("attr_pointer", None) or self.attr_pointer]
                    # 遍历赋值指向的platform属性
                    self.environment.dict_platform[self.attr_pointer.name].pop("attr_pointer", None)
                    if self.attr_pointer: self.builder(**self.environment.dict_platform[self.attr_pointer.name])
                    # 遍历赋值当前platform属性
                    self.builder(**kwargs)
                    # # 将attr_poinger 改成枚举值
                    # 初始化数据源
                    self.db = DbConfig(**self.db).builder()


class Context(IBuilder):
    # 上下文类，全局容器
    # server：包含被加工的setting信息
    # users：user及其oauth对象信息
    str_path = path.join(path.dirname(__file__), "config.yaml")
    config = Config(str_path=str_path)

    # 默认userPo为基准类型

    @classmethod
    def instance(cls, server_config, user_po_klass):
        # server_config：config.yaml文件中读取账号信息以及平台对应的httpsessionclass名称
        cls.server_config = server_config
        # 不同的Server引入不同的User对象
        cls.user_po_klass = user_po_klass
        # user依赖server
        # kwargs输入一些全局参数
        # 例如crm等用例，需要输入business信息
        cls.user_factory = UserFactory(cls)


class UserFactory:
    # 用户列表/用户查询器
    def __init__(self, context):
        self.context = context
        self.config = self.context.config
        self.server = self.config.server.environment.platform
        self.uc = self.config.uc.environment.platform
        self.user_po_klass = context.user_po_klass

        self.oauth_klass = context.server_config.oauth_klasses[self.config.enum_environment][self.config.enum_platform]
        self.list_users = context.server_config.users[self.config.enum_environment][self.server.attr_pointer]["users"]
        self.organization = context.server_config.users[self.config.enum_environment][self.server.attr_pointer]["organization"]

        self.users = [self.user_po_klass(user, self.organization, self) for user in self.list_users]
        [user.login() for user in self.users]

    # 查找权限匹配的用户
    def find_authority_users(self, authority):
        return [user for user in self.users if user.match_authority(authority)]

    def find_authority_user(self, authority):
        list_users = self.find_authority_users(authority)
        return list_users.pop() if list_users else None

    def find_any(self):
        return self.users[0]


class Provider:
    def __init__(self, workbook_path):
        # 将excel转换为矩阵
        self.data_frames = pandas.read_excel(path.join(path.dirname(__file__), workbook_path), sheet_name=None)
        # for sheet_name, sheet_value in self.data_frames.items():
        #     # 将矩阵组织成provider数据
        #     self.data_frames[sheet_name] = [
        #         # 消除title和value的空格
        #         [dict(zip([column_name.strip() for column_name in sheet_value.keys()],
        #                   [cell.strip() if type(cell) == str else cell for cell in record]))]
        #         for record in sheet_value.values]

    def __record_2_map(self, title, record):
        # 将矩阵中的每一条记录转化成字典
        # 去除前后空格
        return dict(zip([column_name.strip() for column_name in title],
                        [cell.strip() if type(cell) == str else cell for cell in record]))

    def record_provider(self, sheet_name):
        # 遍历worksheet，每个record生成一个provider
        return [[self.__record_2_map(self.data_frames[sheet_name].keys(), record)] for record in self.data_frames[sheet_name].values]

    def sheet_provider(self):
        # 遍历workbook，每个sheet生成一个provider
        return [(name, [self.__record_2_map(sheet.keys(), record) for record in sheet.values]) for name, sheet in self.data_frames.items()]


class ServerConfig:
    def __init__(self, path, enum_oauths):
        # 读入ymal配置文件，输出字典
        with open(path, "r", encoding="utf-8") as f:
            self.dict_config = yaml.load(f.read(),Loader=yaml.FullLoader)

        # 分别初始化users和oauth_klasses
        self.users = self._enumerate(self.dict_config["users"])
        self.oauth_klasses = self._enumerate(self.dict_config["oauth_klasses"], enum_oauths)

    def _enumerate(self, dict_config, enum_values=None):
        return {EnvironmentEnum[ek]:
                    {PlatformEnum[pk]:
                         enum_values[pv].value if enum_values else pv
                     for pk, pv in ev.items()}
                for ek, ev in dict_config.items()}
