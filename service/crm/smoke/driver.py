import logging
from os import path
import unittest2

from parameterized import parameterized

from component.utils import Arrays
from service.crm.pojo import UserPo, EnumOauth, dict_business_klasses
from component.confiuration import Context, ServerConfig, Provider


# 冒烟测试
# 检查每个页面请求是否正常
class SmokeDriver(unittest2.TestCase):
    # business = dict_business_klasses["客户"]
    # 初始化环境参数
    # business = EnumBusiness.客户.value()
    # provider = Provider(workbook_path=path.join(path.dirname(__file__), "..", "smoke.xlsx"))

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
        # 用超级用户执行操作
        self.current_user = self.user_factory.find_authority_user("super")
        # 初始化全局配置
        # 初始化环境参数

    def tearDown(self):
        logging.info("====调用tearDown模拟销毁固件====")

    #  遍历业务主页面菜单按钮，并校验返回
    @parameterized.expand(input=[("客户",)])
    # @unittest2.skip
    def test_show(self, provider):
        # 当前处理业务类型
        business = dict_business_klasses[provider]()
        # 将用户session装配入业务
        business.user_shift(session=self.current_user.session)

        list_scope = ["all_own", "my", "assist", "applying"]
        # status参数集合
        list_status = [field.id for field in self.current_user.get_field_values(type(business).__name__, "status")]
        # category参数集合
        list_category = [field.id for field in self.current_user.get_field_values(type(business).__name__, "category")]
        # 构造正交表
        orthogonal_table = Arrays().orthogonal_table(scope=list_scope, status=list_status, category=list_category)
        [self.assertEqual(business.show(ot).session.http_response.as_json("code").actual) for ot in orthogonal_table]


