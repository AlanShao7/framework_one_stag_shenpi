import logging
import unittest2

from service.jxc.info import provider
from component.confiuration import ServerEnum, EnvironmentEnum, PlatformEnum, Context


class InfoDriver(unittest2.TestCase):
    # 初始化环境参数
    enum_server = ServerEnum.JXC
    enum_environment = EnvironmentEnum.TEST
    enum_platform = PlatformEnum.钉钉

    @classmethod
    def setUpClass(cls):
        logging.info("====执行全局初始化程序====")

    @classmethod
    def tearDownClass(cls):
        logging.info("====执行全局销毁程序====")

    def setUp(self):
        logging.info("====执行setUp模拟初始化固件====")
        # 初始化业务类型
        # self.__business = BusinessFactory.get_instance(self.enum_business)
        # 初始化全局配置
        # 初始化环境参数
        Context.instance(enum_server=self.enum_server, enum_environment=self.enum_environment, enum_platform=self.enum_platform, enum_business=self.__business, server_config=provider)

    def tearDown(self):
        logging.info("====调用tearDown模拟销毁固件====")

    # 测试驱动：生成基础资料
    # @parameterized.expand(input=provider.data)
    # def test_data_init(self, provider):
    #     authority = provider.pop("authority")
    #     # 获取业务对象
    #     business = BusinessFactory.get_instance(self.enum_business, **provider)
    #     # 查找用户，注入业务对象，申请请求
    #     Context.user_factory.find_authority_user(authority).session.build(business).apply()
