import logging
import unittest2

from parameterized import parameterized

from service.jxc.sale import provider
from component.confiuration import ServerEnum, EnvironmentEnum, PlatformEnum, Context
#
#
# class SaleDriver(unittest2.TestCase):
#     # 初始化环境参数
#     enum_server = ServerEnum.JXC
#     enum_environment = EnvironmentEnum.TEST
#     enum_platform = PlatformEnum.钉钉
#     statistic = Statistic(workbook="进销存.xlsx", worksheet=enum_business.name)
#
#     @classmethod
#     def setUpClass(cls):
#         logging.info("====执行全局初始化程序====")
#         # 初始化数据类型
#         cls.statistic.to_datetime("日期")
#         cls.statistic.restore().set_index("日期")
#         logging.info("☆☆☆☆☆☆☆☆☆☆按时间：天☆☆☆☆☆☆☆☆☆☆")
#         cls.statistic.resample("d").log()
#         logging.info("☆☆☆☆☆☆☆☆☆☆按时间：周☆☆☆☆☆☆☆☆☆☆")
#         cls.statistic.resample("w").log()
#         logging.info("☆☆☆☆☆☆☆☆☆☆按时间：月☆☆☆☆☆☆☆☆☆☆")
#         cls.statistic.resample("M").log()
#         logging.info("☆☆☆☆☆☆☆☆☆☆按时间：年☆☆☆☆☆☆☆☆☆☆")
#         cls.statistic.resample("y").log()
#         logging.info("☆☆☆☆☆☆☆☆☆☆按产品: 当日☆☆☆☆☆☆☆☆☆☆")
#         cls.statistic.restore().set_index("日期")
#         cls.statistic.day().group("产品名称").log()
#         logging.info("☆☆☆☆☆☆☆☆☆☆按产品: 昨日☆☆☆☆☆☆☆☆☆☆")
#         cls.statistic.restore().set_index("日期")
#         cls.statistic.day(-1).group("产品名称").log()
#         logging.info("☆☆☆☆☆☆☆☆☆☆按产品: 当月☆☆☆☆☆☆☆☆☆☆")
#         cls.statistic.restore().set_index("日期")
#         cls.statistic.month().group("产品名称").log()
#         logging.info("☆☆☆☆☆☆☆☆☆☆按产品: 上月☆☆☆☆☆☆☆☆☆☆")
#         cls.statistic.restore().set_index("日期")
#         cls.statistic.month(-1).group("产品名称").log()
#         logging.info("☆☆☆☆☆☆☆☆☆☆按客户: 当月☆☆☆☆☆☆☆☆☆☆")
#         cls.statistic.restore().set_index("日期")
#         cls.statistic.month().group("客户").log()
#         logging.info("☆☆☆☆☆☆☆☆☆☆按销售员: 当月☆☆☆☆☆☆☆☆☆☆")
#         cls.statistic.restore().set_index("日期")
#         cls.statistic.month().group("销售员").log()
#         logging.info("☆☆☆☆☆☆☆☆☆☆按仓库: 当月☆☆☆☆☆☆☆☆☆☆")
#         cls.statistic.restore().set_index("日期")
#         cls.statistic.month().group("仓库").log()
#
#     @classmethod
#     def tearDownClass(cls):
#         # 生成报表预期数据
#         logging.info("====执行全局销毁程序====")
#
#     def setUp(self):
#         logging.info("====执行setUp模拟初始化固件====")
#         # 初始化全局配置
#         # 初始化环境参数
#         Context.instance(enum_server=self.enum_server, enum_environment=self.enum_environment, enum_platform=self.enum_platform, server_config=provider)
#
#     def tearDown(self):
#         logging.info("====调用tearDown模拟销毁固件====")
#
#     # 测试驱动：生成销售数据
#     @parameterized.expand(statistic.providers)
#     def test_data_init(self, provider):
#         # 通过类型字段获取枚举中的业务类型
#         sale_class = self.enum_business.value[provider["类型"]].value
#         # 实例化业务对象
#         business = sale_class(**provider)
#         # 查找用户，注入业务对象，申请请求
#         user_session = Context.user_factory.find_any().session.build(business)
#         user_session.apply()
#         user_session.approve(EnumStatus.通过)
