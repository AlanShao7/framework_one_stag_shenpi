import logging
from os import path

import unittest2

from parameterized import parameterized

from component.confiuration import Context, ServerConfig, Provider
from service.skb.utils import EnumOauth
from service.uc.pojo import UcUserPo


class ReportDriver(unittest2.TestCase):
    # 初始化环境参数
    provider = Provider(workbook_path=path.join(path.dirname(__file__), "..", "report.xlsx"))

    @classmethod
    def setUpClass(cls):
        logging.info("====执行全局初始化程序====")
        # 初始化数据类型
        cls.config = ServerConfig(path=path.join(path.dirname(__file__), "..", "config.yaml"), enum_oauths=EnumOauth)
        Context.instance(server_config=cls.config, user_po_klass=UcUserPo)
        cls.user_factory = Context.user_factory

    @classmethod
    def tearDownClass(cls):
        # 生成报表预期数据
        logging.info("====执行全局销毁程序====")

    def setUp(self):
        logging.info("====执行setUp模拟初始化固件====")
        # 设定用例环境参数

    def tearDown(self):
        logging.info("====调用tearDown模拟销毁固件====")

    # 测试驱动：生成销售数据
    # def test_data_init(self):
    # # 通过类型字段获取枚举中的业务类型
    # sale_class = self.enum_business.value[provider["类型"]].value
    # # 实例化业务对象
    # business = sale_class(**provider)
    # # 查找用户，注入业务对象，申请请求
    # user_session = Context.user_factory.find_any().session.build(business)
    # user_session.apply()
    # user_session.approve(EnumStatus.通过)

    @parameterized.expand(input=provider.record_provider("流量额度消耗统计报表"))
    def test_quota(self,provider):
        self.user_factory.find_any().session.quota(provider)
