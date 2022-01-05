import logging
from os import path
import unittest2

from parameterized import parameterized

from service.crm.pojo import UserPo, EnumCategory, EnumStatus, EnumOauth, dict_business_klasses
from component.confiuration import ServerEnum, EnvironmentEnum, PlatformEnum, Context, ServerConfig


class DataMakerDriver(unittest2.TestCase):
    # 初始化环境参数
    business = business = dict_business_klasses["合同"]

    # business = BusinessFactory.get_instance(type=EnumBusiness.线索)

    @classmethod
    def setUpClass(cls):
        cls.config = ServerConfig(path=path.join(path.dirname(__file__), "..", "config.yaml"), enum_oauths=EnumOauth)
        Context.instance(server_config=cls.config, user_po_klass=UserPo)
        cls.user_factory = Context.user_factory
        logging.info("====执行全局初始化程序====")

    @classmethod
    def tearDownClass(cls):
        logging.info("====执行全局销毁程序====")

    def setUp(self):
        logging.info("====执行setUp模拟初始化固件====")
        # 初始化全局配置
        # 初始化环境参数

    def tearDown(self):
        logging.info("====调用tearDown模拟销毁固件====")

    # 测试驱动：生成测试数据
    # @parameterized.expand(input=provider.data)
    #  测试驱动改成excel形式
    @parameterized.expand(input=[(0,)])
    @unittest2.skip
    def test_data_init(self, provider):
        # 关闭审批，所有申请能够直接通过
        self.business.setting_on_off("off")
        # 任一人申请业务
        self.business.user_shift(session=self.user_factory.find_any().session).apply()
        # 所有人对该业务签到一遍
        [self.business.user_shift(session=user.session).revisit(category=EnumCategory.电话, status=EnumStatus.初访) for user in self.user_factory.users]
