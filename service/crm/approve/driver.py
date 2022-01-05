import logging
from os import path

import unittest2
# from parameterized import parameterized

from service.crm.pojo import UserPo, ApproveFlow, EnumOauth, dict_business_klasses
from component.confiuration import Context, Provider, ServerConfig


# 审批流程测试驱动器
# 合同/商机/客户 通用型


class ApproveDriver(unittest2.TestCase):
    # 初始化环境参数
    business = dict_business_klasses["客户"]()
    int_approve_level = 2
    provider = Provider(workbook_path=path.join(path.dirname(__file__), "..", "approve.xlsx"))

    @classmethod
    def setUpClass(cls):
        logging.info("====执行全局初始化程序====")
        # 从config.yaml文件中读取账号信息以及平台对应的httpsessionclass名称
        cls.config = ServerConfig(path=path.join(path.dirname(__file__), "..", "config.yaml"), enum_oauths=EnumOauth)
        Context.instance(server_config=cls.config, user_po_klass=UserPo)
        cls.user_factory = Context.user_factory

    @classmethod
    def tearDownClass(cls):
        logging.info("====执行全局销毁程序====")

    def setUp(self):
        logging.info("====执行setUp模拟初始化固件====")
        self.__user_applier = self.user_factory.find_authority_user("applier")
        self.__user_super = self.user_factory.find_authority_user("super")
        self.__user_pc = self.user_factory.find_authority_user("pc")

    def tearDown(self):
        logging.info("====调用tearDown模拟销毁固件====")

    def __user_shift(self, user):
        logging.info("切换操作人：%s" % user)
        self.business.user_shift(session=user.session)

    # 测试驱动：审批业务
    @parameterized.expand(input=provider.record_provider(str(int_approve_level) + "级审批"))
    # @unittest2.skip
    def test_opportunity(self, provider):
        work_flow = ApproveFlow(provider, self.user_factory)
        self.setting(work_flow)
        self.apply()
        [self.approve_step(step) for step in work_flow]


    # 设置审批类型
    def setting(self, approve_flow):
        logging.info("设置%s审批" % self.business.singular)
        # 切换到admin
        self.__user_shift(self.__user_pc)
        # 清除所有已存在的审批
        self.__clear_all()
        # 设置审批级数及详情
        self.business.approve_setting(approve_flow)

    # 清除所有已存在的审批
    def __clear_all(self):
        self.business.setting_on_off("off")
        self.business.setting_on_off("on")

    # 新增商机/客户/线索/合同
    def apply(self):
        # 生成商机随机名称
        self.__user_shift(self.__user_applier)
        self.business.apply()
        self.assert_status("待1级审批")

    # 审批步骤
    def approve_step(self, step):
        # 遍历步骤中的所有用户
        for approval_step in step:
            logging.info(approval_step)
            # 第一步，切换用户
            self.__user_shift(approval_step.user)
            # 检查审批单状态
            response = self.business.approve(approval_step)
            # 处理无权限情况
            if "无权限" == step.str_result:
                self.assertFalse(response.session.http_response.ok)
                logging.info("无权限审批未完成验证通过")
            # 验证审批后状态
            self.assert_status(approval_step.str_expect)

    def assert_status(self, exp):
        expected = exp
        actual = self.business.approve_info().info
        self.assertEqual(expected, actual)
        logging.info("状态验证通过：title:%s;status:%s" % (self.business.title, actual))

    # 未使用需要修改优化
    def assert_notifications(self, test_step_list):
        logging.info("消息通知验证%s" % self.business.title)

        # self.__user_applier.oauth_klass = PcDeploy
        # self.__user_applier.login()

        list_expected = list()
        [list_expected.extend(step.get_str_notifications()) for step in test_step_list]
        list_actual = self.business.notifications()
        list_actual.reverse()

        for expexted, actual in zip(list_expected, list_actual):
            logging.info("预期值：%s；实际值：%s" % (expexted, actual))
            self.assertTrue(expexted in actual)
