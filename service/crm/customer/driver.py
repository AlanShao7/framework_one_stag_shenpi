import logging
from os import path

import unittest2
# from parameterized import parameterized

from service.crm.pojo import UserPo, ApproveFlow, EnumOauth, Customer
from component.confiuration import Context, Provider, ServerConfig


#  客户相关业务
class CustomerDriver(unittest2.TestCase):
    # 初始化客户业务对象
    customer = Customer()

    @classmethod
    def setUpClass(cls):
        logging.info("====执行全局初始化程序====")
        cls.config = ServerConfig(path=path.join(path.dirname(__file__), "..", "config.yaml"), enum_oauths=EnumOauth)
        Context.instance(server_config=cls.config, user_po_klass=UserPo)
        cls.user_factory = Context.user_factory

    @classmethod
    def tearDownClass(cls):
        logging.info("====执行全局销毁程序====")

    def setUp(self):
        # 超级用户登录
        self.super_user = self.user_factory.find_authority_user("super")
        # 普通用户作为协作人
        self.normal_users = self.user_factory.find_authority_users("normal")
        # 操作人：超级用户
        self.customer.user_shift(session=self.super_user.session)
        # 关闭审批，所有申请能够直接通过
        self.customer.setting_on_off("off")


    def tearDown(self):
        logging.info("====调用tearDown模拟销毁固件====")

    # 批量编辑协作人
    @unittest2.skip
    def test_assist_user(self):
        self.customer.apply()
        self.assertTrue("批量编辑协作人成功！" in self.customer.assist_user(option="append", assists=self.normal_users[0].dto.id).session.http_response.text)
        self.assertTrue("批量编辑协作人成功！" in self.customer.assist_user(option="replace", assists=self.normal_users[1].dto.id).session.http_response.text)
        self.assertTrue("批量编辑协作人成功！" in self.customer.assist_user(option="remove", assists=self.normal_users[1].dto.id).session.http_response.text)

    # 合并客户
    @unittest2.skip
    def test_data_merge(self):
        self.customer.apply()
        merge_customer = Customer()
        merge_customer.user_shift(session=self.super_user.session)
        merge_customer.apply()
        # 正向合并
        # customer合并merge_customer,self.customer仍然存在，无需重新apply
        self.assertEqual(0,self.customer.data_merge(from_customer=merge_customer, clockwise=True).session.http_response.as_json("code").get())
        merge_customer.apply()
        # 反向合并
        self.assertEqual(0, self.customer.data_merge(from_customer=merge_customer, clockwise=False).session.http_response.as_json("code").get())

    #     删除客户 TODO 删除的功能搞不定
    @unittest2.skip
    def test_bulk_delete(self):
        self.customer.apply()
        self.customer.bulk_delete(del_associated=False)
        self.customer.batch_operation_perform()
        self.customer.apply()
        self.customer.bulk_delete(del_associated=True)
        self.customer.batch_operation_perform()



    # 批量编辑协作人
    @unittest2.skip
    def test_mass_transfer(self):
        self.customer.apply()
        self.assertTrue("批量转移客户成功！" in self.customer.mass_transfer(user = self.normal_users[0],transfer_contracts=False,transfer_opportunities=False,nowin_opportunities=False).session.http_response.text)
        self.customer.apply()
        self.assertTrue("批量转移客户成功！" in self.customer.mass_transfer(user = self.normal_users[0],transfer_contracts=False,transfer_opportunities=True,nowin_opportunities=False).session.http_response.text)
        self.customer.apply()
        self.assertTrue("批量转移客户成功！" in self.customer.mass_transfer(user = self.normal_users[0],transfer_contracts=True,transfer_opportunities=True,nowin_opportunities=False).session.http_response.text)

    # TODO 转移公海的功能搞不定
    @unittest2.skip
    def test_common_pool(self):
        self.customer.apply()
        self.assertTrue("批量转移客户公海成功！" in self.customer.common_pool().session.http_response.text)
