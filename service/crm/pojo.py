import logging
import re
import time
from enum import Enum, IntEnum, unique
import random
import arrow
import collections
from bs4 import BeautifulSoup

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, backref

from component.confiuration import Context
from component.oauth import BaseUserPo, BaseSession, HeaderFactory
from component.utils import Random

Base = declarative_base()
db_config = Context.config.server.environment.platform.db


# ———————————————————数据持久化对象———————————————————

class UserDto(Base):
    @declared_attr
    def __tablename__(self):
        return db_config.table_name[self.__name__]

    id = Column(Integer, primary_key=True)
    superior_id = Column(Integer)
    name = Column(String)
    phone = Column(String)

    @declared_attr
    def organization_id(self):
        return Column(Integer, ForeignKey("%s.id" % db_config.table_name["OrganizationDto"]))

    @declared_attr
    def organization(self):
        return relationship("OrganizationDto", backref=backref(self.__tablename__, uselist=False))

    @declared_attr
    def departments(self):
        return relationship("UserDepDto", back_populates="user")


class DepartmentDto(Base):
    @declared_attr
    def __tablename__(self):
        return db_config.table_name[self.__name__]

    id = Column(Integer, primary_key=True)
    name = Column(String)
    organization_id = Column(Integer)
    parent_id = Column(Integer)

    @declared_attr
    def users(self):
        return relationship("UserDepDto", back_populates="department")


class UserDepDto(Base):
    @declared_attr
    def __tablename__(self):
        return db_config.table_name[self.__name__]

    @declared_attr
    def user_id(self):
        return Column(Integer, ForeignKey("%s.id" % db_config.table_name["UserDto"]), primary_key=True)

    @declared_attr
    def department_id(self):
        return Column(Integer, ForeignKey("%s.id" % db_config.table_name["DepartmentDto"]), primary_key=True)

    @declared_attr
    def user(self):
        return relationship("UserDto", back_populates="departments")

    @declared_attr
    def department(self):
        return relationship("DepartmentDto", back_populates="users")


class OrganizationDto(Base):
    @declared_attr
    def __tablename__(self):
        return db_config.table_name[self.__name__]

    id = Column(Integer, primary_key=True)
    name = Column(String)


class FieldValuesDto(Base):
    @declared_attr
    def __tablename__(self):
        return "field_values"

    @declared_attr
    def field_map_id(self):
        return Column(Integer, ForeignKey("field_maps.id"))

    id = Column(Integer, primary_key=True)
    value = Column(String)


# 输入域表
class FieldMapsDto(Base):
    @declared_attr
    def __tablename__(self):
        return "field_maps"

    id = Column(Integer, primary_key=True)
    # 所属业务（客户/线索/商机/合同）
    klass_name = Column(String)
    # 域名称
    field_name = Column(String)
    # 企业编号
    organization_id = Column(Integer)


class UserPo(BaseUserPo):
    def _get_user_dto(self, organization):
        Base.metadata = db_config.metadata
        return self.db_session.query(UserDto).join(OrganizationDto).filter(UserDto.phone == self.phone).filter(OrganizationDto.name == organization["name"]).first()

    # 查找category/status等参数集合
    def get_field_values(self, klass_name, field_name):
        return self.db_session.query(FieldValuesDto).join(FieldMapsDto).filter(FieldValuesDto.field_map_id == FieldMapsDto.id).filter(
            FieldMapsDto.organization_id == self.dto.organization_id).filter(
            FieldMapsDto.klass_name == klass_name).filter(FieldMapsDto.field_name == field_name).all()

        # return {entry.value: entry.id for entry in entries}


# ———————————————————CRM枚举对象———————————————————
@unique
class EnumCategory(IntEnum):
    电话 = 323050
    QQ = 323051
    微信 = 323052
    拜访 = 323053
    邮件 = 323054
    短信 = 323055
    其他 = 323056


@unique
class EnumStatus(IntEnum):
    初访 = 322937
    意向 = 322938
    报价 = 322939
    成交 = 322940
    暂时搁置 = 322941
    # lead
    未处理 = 242719


# ———————————————————业务审批对象———————————————————


class Multistep:
    @property
    def participant(self):
        # 是否需要手动指定参与人
        return self._participant

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value


class Superior(Multistep):
    def __init__(self):
        super().__init__()
        self._name = "负责人主管"
        self._value = "superior"
        # 会根据申请人自动生成审批参与人
        self._participant = False


class PreviousSuperior(Multistep):
    def __init__(self):
        super().__init__()
        self._name = "上一级审批人主管"
        self._value = "previous_superior"
        # 会根据上一步的审批人自动生成审批参与人
        self._participant = False


class Specified(Multistep):
    def __init__(self):
        super().__init__()
        self._name = "任意一人"
        self._value = "specified"
        self._participant = True


class SpecifiedJointly(Multistep):
    def __init__(self):
        super().__init__()
        self._name = "多人会签"
        self._value = "specified_jointly"
        self._participant = True


class Administrator(Specified):
    # 执行时用超管
    # 设定任意一人
    def __init__(self):
        super().__init__()
        self._name = "超管"


class CrossLevel(Superior):
    # 执行时越级主管
    # 设定时负责人主管
    def __init__(self):
        super().__init__()
        self._name = "越级主管"


dict_result = {"通过": "approve", "否决": "deny", "撤销": "revert", "驳回": "deny", "无权限": "approve"}

dict_multistep = {"负责人主管": Superior(), "越级主管": CrossLevel(), "上一级审批人主管": PreviousSuperior(), "任意一人": Specified(), "多人会签": SpecifiedJointly(), "超管": Administrator()}


# ———————————————————CRM业务对象———————————————————
class CRM:
    str_revisit = "revisit_log"

    def __init__(self):
        # 非必填项
        # self.singular = None
        self.random = Random()
        self.time = arrow.now()
        self.__url_api = self.UrlApi(self)

        #  审批设置开关
        # 关闭后，所有审批自动通过
        self.setting_switch = {"off": 0, "on": 1}

        # 默认值：数量，电话号码，评语
        self.telephone = Random(boolean_lower_case=False, boolean_upper_case=False).return_sample(11)
        self.amount = 999
        self.description = Random().return_sample(99)

        self.setting_body = {"utf8": "✓", "_method": "put"}

        self.apply_body = {"utf8": "✓"}

        self.approve_body = {"utf8": "✓", "_method": "put", "key": self.singular, "%s[approve_description]" % self.singular: self.description}
        self.revisit_body = {"utf8": "✓",
                             "%s[content]" % self.str_revisit: self.description,
                             "%s[real_revisit_at]" % self.str_revisit: self.time.format("YYYY-MM-DD HH:mm:ss"),
                             "%s[remind_at]" % self.str_revisit: self.time.format("YYYY-MM-DD HH:mm:ss")}
        self.checkin_body = {
            "checkin": {"message": "", "checkin_name": "111", "checkable_type": self.singular.capitalize(), "address_attributes": {
                "off_distance": 39, "detail_address": "123", "lng": 121.602001, "lat": 31.200028}}, "update_entity_address": False}

        self.show_body = {"type": "advance", "section_only": "true", "order": "desc", "sort": "customers.updated_at",
                          "page": "1", "per_page": "10"}

    @property
    def url_api(self):
        return self.__url_api

    def user_shift(self, session):
        # 在business构造之后，session异步注入
        # 因此所有调用session相关的方法，例如csrf等，都要在业务方法体内部完成
        self.session = session
        return self

    # 审批设置开关
    def setting_on_off(self, switch):
        self.session._set_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.FORM, HeaderFactory.XCsrfToken.dynamic(self.session.csrf))
        url = self.session._server.domain + "/settings/%s_approve/update" % self.singular
        body = {
            "%s_approve[enable_%s_approve]" % (self.singular, self.singular): self.setting_switch[switch]
        }
        self.http_response = self.session.put(url, body=body)

    # 审批级数设置
    def approve_setting(self, approve_flow):
        logging.info("设置%s级%s审批" % (len(approve_flow.list_settings), self.singular))
        self.session._set_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.FORM, HeaderFactory.XCsrfToken.dynamic(self.session.csrf))
        url = self.session._server.domain + "/settings/%s_approve/update" % self.singular
        self.setting_body.update({"authenticity_token": self.session.csrf})
        for key, value in approve_flow.setting_body.items():
            self.setting_body["%s%s" % (self.singular, key)] = value
        self.session.put(url, body=self.setting_body)
        return self

    # 查重
    def check_duplicate_field(self, field, value):
        body = {"field": field, "field_value": value}
        self.session.check_duplicate_field(body)
        return self

    # 提交合同/商机/客户
    def apply(self):
        # 每一次apply生成不同的title
        self.title = Random().return_sample(20)
        body = {"authenticity_token": self.session.csrf, "%s[title]" % self.singular: self.title,
                "%s[approve_status]" % self.singular: "applying", "%s[total_amount]" % self.singular: self.amount,
                "%s[user_id]" % self.singular: self.session.user.dto.id, "%s[contract_token]" % self.singular: self.session.user.session.csrf,
                "%s[want_department_id]" % self.singular: self.session.user.dto.departments[0].department.id}
        logging.info("新增%s：%s" % (self.singular, self.title))
        self.id = self.session.apply(self, {**self.apply_body, **body}).as_json("data", "id").get()
        return self

    # 审批合同/商机/客户
    def approve(self, approve_step):
        logging.info("审批%s：%s" % (self.singular, self.title))
        body = {"%s[step]" % self.singular: approve_step.int_num, "authenticity_token": self.session.csrf}
        self.session.approve(self, {**self.approve_body, **body}, approve_step)
        return self

    # 跟进
    def revisit(self, **kwargs):
        logging.info("跟进%s：%s" % (self.singular, self.title))
        body = {"%s_id" % self.singular: self.id, "authenticity_token": self.session.csrf,
                "%s[loggable_attributes][id]:" % self.str_revisit: self.id,
                "%s[category]" % self.str_revisit: kwargs.setdefault("category", EnumCategory.电话).value,
                "%s[loggable_attributes][status]" % self.str_revisit: kwargs.setdefault("status", EnumStatus.初访).value}
        self.session.revisit(self, {**self.revisit_body, **body})
        return self

    # 签到
    def checkin(self):
        logging.info("签到%s：%s" % (self.singular, self.title))
        self.checkin_body["checkin"].update({"checkable_id": self.id})
        self.session.checkin(self.checkin_body)
        return self

    # 审批信息
    def approve_info(self):
        logging.info("获取%s：%s审批状态" % (self.singular, self.title))
        self.info = self.session.approve_info(self)
        return self

    # 查询业务信息
    def show(self, kwargs):
        logging.info("查询%s；参数：%s" % (self.singular, kwargs))
        body = {"scope": kwargs["scope"]}
        self.session.show(self, {**self.approve_body, **body, **self.Filters(kwargs).get})
        return self

    # 批量操作
    def batch_operation_perform(self):
        body = {"task_id": self.task_id}
        logging.info("批量操作：%s" % self.title)
        self.session.batch_operation_perform(body)
        return self

    class UrlApi:
        def __init__(self, business):
            self.business = business
            self.singular = business.singular
            self.plural = business.plural
            self.info = self.plural

    class Filters:
        name = list()
        operator = list()
        query = list()

        def __init__(self, kwargs):
            self.kwargs = kwargs
            self.__parameters("status", "category")

        def __parameters(self, *args):
            for arg in args:
                if self.kwargs.get(arg):
                    self.name.append(arg)
                    self.operator.append("equal")
                    self.query.append(self.kwargs[arg])

        @property
        def get(self):
            return {"filters[][name]": self.name, "filters[][operator]": self.operator,
                    "filters[][query]": self.query} if self.name else dict()


class Contract(CRM):
    # 合同
    # 单数形式
    singular = "contract"
    # 复数形式
    plural = "contracts"


class Opportunity(CRM):
    # 单数形式
    singular = "opportunity"
    # 复数形式
    plural = "opportunities"


class Customer(CRM):
    # 单数形式
    singular = "customer"
    # 复数形式
    plural = "customers"

    # 提交客户
    def apply(self):
        # 每一次apply生成不同的title
        self.title = Random().return_sample(20)
        body = {
            "authenticity_token": self.session.csrf, "%s[approve_status]" % self.singular: "applying",
            "%s[name]" % self.singular: self.title, "%s[user_id]" % self.singular: self.session.user.dto.id,
            "%s[address_attributes][tel]" % self.singular: self.telephone,
            "%s[want_department_id]" % self.singular: self.session.user.dto.departments[0].department.id,
            "%s[customer_token]" % self.singular: self.session.user.session.csrf
        }
        logging.info("新增%s：%s" % (self.singular, self.title))


        # self.check_duplicate_field(field="name",value=self.title)
        # self.check_duplicate_field(field="tel",value=self.telephone)
        self.id = self.session.apply(self, {**self.apply_body, **body}).as_json("data", "id").get()
        return self

    # 批量编辑协作人
    def assist_user(self, option, assists):
        body = {
            "utf8": "✓", "authenticity_token": self.session.csrf, "operation_selection": option + "_assist_user",
            "customer[assist_user_ids][]": assists, "ids[]": self.id
        }
        logging.info("%s客户%s协作人" % (self.title, option))
        self.session.assist_user(body)
        return self

    # 合并客户
    def data_merge(self, from_customer, clockwise=True):
        customers = [from_customer, self]
        if not clockwise:
            customers.reverse()
        body = {
            "utf8": "✓", "_method": "patch", "authenticity_token": self.session.csrf,
            "from_customer_id": customers[0].id, "target_customer_id": customers[1].id,
            "customer[name]": customers[1].title,
            # 初访
            "customer[status]": "250867",
            "customer[user_id]": self.session.user.dto.id
        }
        logging.info("客户：%s合并客户：%s" % tuple([cust.title for cust in customers][::-1]))
        self.session.data_merge(body)
        return self

    def bulk_delete(self, del_associated=False):
        body = {"customer_ids[]": self.id, "authenticity_token": self.session.csrf, "del_associated": del_associated}
        logging.info("删除客户：%s" % self.title)

        self.task_id = re.findall(r"\"task_id\":\"(\w+)\",", self.session.bulk_delete(body).text).pop()
        return self

    def mass_transfer(self, user, transfer_contracts=False, transfer_opportunities=False, nowin_opportunities=False):
        body = {"authenticity_token": self.session.csrf, "user_id": user.dto.id, "transfer_contracts": transfer_contracts,
                "transfer_opportunities": transfer_opportunities, "nowin_opportunities": nowin_opportunities,
                "customer_ids[]": self.id}
        logging.info("将客户：%s从用户：%s转移至用户：%s" % (self.title, self.session.user.dto.name, user.dto.name))
        self.session.mass_transfer(body)
        return self

    def common_pool(self):
        body = {"common_id": "2154", "authenticity_token": self.session.csrf, "customer_ids[]": self.id}
        logging.info("将客户：%s，转移至公海" % self.title)
        self.session.common_pool(body)
        return self


class Lead(CRM):
    # 线索
    # 单数形式
    singular = "lead"
    # 复数形式
    plural = "leads"

    # 提交线索
    def apply(self):
        # 每一次apply生成不同的title
        self.title = Random().return_sample(20)
        body = {
            "authenticity_token": self.session.csrf, "%s[approve_status]" % self.singular: "applying",
            "%s[is_draft]" % self.singular: False, "%s[name]" % self.singular: self.title,
            "%slead[address_attributes][tel]" % self.singular: self.telephone, "china_tag_id": 4,
            "%s[address_attributes][country_id]" % self.singular: 4, "%s[user_id]" % self.singular: self.session.user.dto.id,
            "%s[want_department_id]" % self.singular: self.session.user.dto.departments[0].department.id}
        logging.info("新增%s：%s" % (self.singular, self.title))
        self.id = self.session.apply(self, {**self.apply_body, **body}).as_json("data", "id").get()
        return self


class Expense(CRM):
    # 费用
    # 单数形式
    singular = "expense"
    # 复数形式
    plural = "expenses"

    # 提交费用
    def apply(self):
        # 每一次apply生成不同的title
        self.title = Random().return_sample(20)
        body = {
            "authenticity_token": self.session.csrf, "%s[sn]" % self.singular: self.title,
            "%s[description]" % self.singular: self.description, "%s[amount]" % self.singular: self.amount,
            "%s[incurred_at] % self.singular": self.time.format("YYYY-MM-DD"), "%s[user_id]" % self.singular: self.session.user.dto.id}
        logging.info("新增%s：%s" % (self.singular, self.title))
        self.id = self.session.apply(self, {**self.apply_body, **body}).as_json("expense", "id").get()
        return self


class ExpenseAccount(CRM):
    # 报销
    # 单数形式
    singular = "expense_account"
    # 复数形式
    plural = "expense_accounts"

    def __init__(self):
        super().__init__()
        self.url_api.info = "expense_center/expense_accounts"
        self.expense = Expense()

    def user_shift(self, session):
        super().user_shift(session)
        self.expense.user_shift(self.session)

    # 提交报销
    def apply(self):
        self.expense.apply()
        # 每一次apply生成不同的title
        self.title = Random().return_sample(20)
        body = {
            "authenticity_token": self.session.csrf, "%s[approve_status]" % self.singular: "applying",
            "%s[sn]" % self.singular: self.title, "%s[user_id]" % self.singular: self.session.user.dto.id,
            "%s[department_id]" % self.singular: self.session.user.dto.departments[0].department.id,
            "%s[note]" % self.singular: self.description, "expense_ids[]": self.expense.id}
        logging.info("新增%s：%s" % (self.singular, self.title))
        self.id = self.session.apply(self, {**self.apply_body, **body}).as_json("expense", "id").get()
        return self


#  业务类型
dict_business_klasses = {"合同": Contract, "商机": Opportunity, "客户": Customer, "线索": Lead, "费用": Expense, "报销": ExpenseAccount}


# ———————————————————Http_Session对象———————————————————
# http_session类，保存会话信息
# session基类，子类为不同平台的
class Session(BaseSession):
    def __init__(self, user):
        super().__init__(user)

    # 查询业务信息
    def show(self, business, dict_body):
        self._set_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.FORM)
        self.set_authorization(token=self.token)
        url = "%s/api/pc/%s" % (self._server.domain, business.plural)
        return self.get(url=url, body=dict_body)

    def check_duplicate_field(self,dict_body):
        self._set_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.FORM,HeaderFactory.XCsrfToken.dynamic(self.csrf))
        url = "%s/api/customers/check_duplicate_field.json" % self._server.domain
        return self.post(url=url, body=dict_body)

    # 申请
    def apply(self, business, dict_body):
        self._set_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.FORM)
        url = "%s/api/%s" % (self._server.domain, business.plural)
        return self.post(url=url, body=dict_body)


    #  审批
    def approve(self, business, dict_body, approve_step):
        self._set_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.FORM)
        url = "%s/api/approvals/%s/%s" % (self._server.domain, business.id, dict_result[approve_step.str_result])
        return self.post(url=url, body=dict_body)

    # 跟进
    def revisit(self, business, dict_body):
        self._set_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.FORM)
        url = "%s/api/%s/%s/revisit_logs" % (self._server.domain, business.plural, business.id)
        return self.post(url=url, body=dict_body)

    # 签到
    def checkin(self, dict_body):
        self._clear_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.JSON)
        self.set_authorization(token=self.token, device=self._server.device, version_code=self._server.version_code)
        url = "%s/api/v2/checkins" % self._server.domain
        return self.post(url=url, body=dict_body)

    # 协作人操作
    def assist_user(self, dict_body):
        self._clear_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM)
        url = "%s/api/customers/batch_update_assist_user" % self._server.domain
        return self.put(url=url, body=dict_body)

    # 用户合并
    def data_merge(self, dict_body):
        self._clear_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM)
        url = "%s/api/customers/data_merge" % self._server.domain
        return self.put(url=url, body=dict_body)

    #  删除用户
    def bulk_delete(self, dict_body):
        self._clear_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM)
        url = "%s/customers/bulk_delete" % self._server.domain
        return self.delete(url=url, body=dict_body)

    # 转移用户
    def mass_transfer(self, dict_body):
        self._clear_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM)
        url = "%s/api/customers/mass_transfer" % self._server.domain
        return self.put(url=url, body=dict_body)

    def common_pool(self, dict_body):
        self._clear_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM)
        url = "%s/api/customers/mass_transfer_to_common_pool" % self._server.domain
        return self.put(url=url, body=dict_body)

    # 批量操作
    def batch_operation_perform(self, dict_body):
        self._clear_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM)
        url = "%s/api/batch_operation/perform" % self._server.domain
        return self.post(url=url, body=dict_body)

    # 获取审批状态
    def approve_info(self, business):
        self._set_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.FORM)
        url = "%s/%s" % (self._server.domain, business.url_api.info)
        body = {"scope": "all_own", "per_page": 10, "type": "advance", "section_only": True}
        return BeautifulSoup(self.get(url, body=body).text, "html5lib").select("table>tbody>tr[data-id=\"%s\"]>td[data-column=\"approve_status_i18n\"]>div.value" % business.id).pop().text.strip()

    # 消息通知
    # 与业务类型无关
    def notifications(self, business):
        url = "%s/notifications" % self._server.domain
        self.http_response = self.get(url)
        return [node.text.strip() for node in BeautifulSoup(self.http_response.text, "html5lib").select("section#notification_table tbody>tr>td>a.text-primary[href$=\"%s\"]" % business.id)]

    # def


# # 私有化平台
# class PrivateDeploy(Session):
#     def __init__(self, user):
#         super().__init__(user)
#         self.token = None
#
#     # 私有化环境登录方式
#     def login(self):
#         self.get(self._server.domain)
#         # time.sleep(2)
#         self.csrf = self.get_csrf()
#         # 然后，以csrf作为参数
#         # 用phone和pwd登录
#         body = {
#             "utf8": "✓",
#             "authenticity_token": self.csrf,
#             "user[login]": self.user.phone,
#             "user[password]": self.user.password,
#             "commit": "登 录"
#         }
#         self.http_response = self.post(self._server.domain + "/users/sign_in", body=body)
#         # 获取最终的cookie和csrf
#         self.cookie = self.get_cookies()
#         self.csrf = self.get_csrf()
#         return self


# 钉钉平台
class DingdingDeploy(Session):
    def login(self):
        time.sleep(2)
        self._set_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.FORM, HeaderFactory.XRequestedWith.XML)
        body = {
            "login": self.user.phone,
            "password": self.user.password,
            "device": "web"
        }
        # verify=False:不验证ssl
        self.token = self.post(url=self._server.domain + "/api/v2/auth/login", body=body).get_json_property("data", "user_token")

        url = self._server.domain + "/dingtalk/sessions/new"
        body = {"user_token": self.token}
        self._set_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.FORM, HeaderFactory.XRequestedWith.XML)
        self.get(url, body=body)
        self.csrf = self.get_csrf()
        self.token = re.findall(r"window.current_user_token\s+=\s+\'(\w+)\';", BeautifulSoup(self.http_response.text, "html5lib").text).pop()
        logging.info("钉钉登陆成功：用户信息：phone=%s;name=%s" % (self.user.phone, self.user.dto.name))
        return self


# # 移动端平台
# class AndroidDeploy(Session):
#     def login(self):
#         # self._set_head(Accept.HTML, ContentType.FORM)
#         body = {"device": "android", "login": self.user.phone, "password": self.user.password, "corp_id": "wwjupSAg8YPnH24E71ZF"}
#         self.token = self.post(url=self._server.domain + "/api/v2/auth/login", body=body).as_json("data", "user_token")
#         return self
#
#     # 新增商机
#     def apply(self, business):
#         time.sleep(5)
#         self._set_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.FORM, HeaderFactory.XRequestedWith.XML)
#         self.set_authorization(token=self.token, device=self._server.device, version_code=self._server.version_code)
#         url = "%s/api/v2/%s" % (self._server.domain, business.plural)
#         return self.post(url=url, body=business.apply_body)
#
#     # 执行审批
#     def approve(self, business, approve_step):
#         time.sleep(3)
#         self.set_authorization(token=self.token, device=self._server.device, version_code=self._server.version_code)
#         url = "%s/api/v2/approvals/%s/%s" % (self._server.domain, business.id, dict_result[approve_step.str_result])
#         return self.post(url=url, body=business.approve_body)
#
#     # 获取审批状态
#     def approve_info(self, business):
#         url = "%s/api/v2/%s/%s" % (self._server.domain, business.plural, business.id)
#         self.set_authorization(token=self.token, device=self._server.device, version_code=self._server.version_code)
#         return self.get(url).as_json("data", "approve_status_i18n")


# PC平台
class PcDeploy(Session):
    def login(self):
        super().login()
        self.uid = self.http_response.as_json("data", "uid").get()
        self.ticket = self.http_response.as_json("data", "ticket").get()
        self._set_head(HeaderFactory.Accept.HTML, HeaderFactory.ContentType.FORM, HeaderFactory.XRequestedWith.XML)
        self.get(self._server.domain, body={"st": self.ticket})
        self.cookie = self.get_cookies()
        self.csrf = self.get_csrf()
        # window.current_user_token = '9bcde08732965e629dd74364ce719cc9';
        self.token = re.findall(r"window.current_user_token\s+=\s+\'(\w+)\';", BeautifulSoup(self.http_response.text, "html5lib").text).pop()
        return self


class EnumOauth(Enum):
    Oauth = Session
    # PrivateDeploy = PrivateDeploy
    DingdingDeploy = DingdingDeploy
    # AndroidDeploy = AndroidDeploy
    PcDeploy = PcDeploy


# ———————————————————审批业务对象———————————————————
class ApproveFlow:
    def __init__(self, kwargs, user_factory):
        self.kwargs = kwargs
        self.user_factory = user_factory
        self.str_result = self.kwargs.pop("result")
        # 运行的审批级数
        self.int_interrupt = self.kwargs.pop("interrupt")
        if "无权限" == self.str_result:
            self.int_interrupt = 1
        elif self.str_result not in ("通过", "驳回"):
            self.int_interrupt = len(self.kwargs)
        # 排序后的执行序列
        self.list_steps = sorted([(int(k[0]), dict_multistep[v]) for k, v in self.kwargs.items()],
                                 key=lambda item: item[0])
        # 该数组将反复用到
        # setting_body通过该数组生成
        # approve每个步骤都要依赖list_settings进行比对
        # 所以用变量替代属性
        self.list_settings = [self.SettingStep(self, int_num, step) for int_num, step in self.list_steps]
        # self.list_settings已生成完毕，对list_approve_steps进行切片操作
        self.list_approve_steps = self.list_steps[:self.int_interrupt]
        # 驳回处理方案：
        # 1.ApproveFlow层，self.list_approve_steps最后一步*2，形成类似[步骤1，步骤2，步骤3.步骤3]的结构
        # 2.ApproveStep迭代时，第一次遇到步骤3，因为has_next == True，会按照通过方案执行
        # 3.第二次遇到步骤3，has_next==false，将会按照驳回/否决方案执行
        if "驳回" == self.str_result:
            self.list_approve_steps.append(self.list_approve_steps[-1])

        logging.info(self.__str__())

    @property
    def setting_body(self):
        return collections.ChainMap(*[step.body for step in self.list_settings])

    @property
    def business_finished(self):
        return ("驳回" == self.str_result and self.has_next <= 1) or not self.has_next

    @property
    def has_next(self):
        return len(self.list_approve_steps)

    def __iter__(self):
        return self

    def __next__(self):
        if not self.has_next:
            raise StopIteration()
        return self.ApproveStep(self, *self.list_approve_steps.pop(0))

    def __str__(self):
        return "设置审批级别：%s；实际审批级别：%s；最终审批结果：%s" % (len(self.list_settings), self.int_interrupt, self.str_result)

    class SettingStep:
        # 审批设置对象：提供设置审批级数的功能
        def __init__(self, flow, int_num, enum_step):
            self.flow = flow
            self.user_factory = self.flow.user_factory
            #  当前审批级数
            # x级审批，截取第一个字符，转换成数字
            self.int_num = int_num
            # 步骤类型
            self.enum_step = enum_step

        @property
        def list_users(self):
            # 负责人主管/上一级审批人主管，参与人参数为空数组
            return self.user_factory.find_authority_users("normal") if self.enum_step.participant else tuple()

        @property
        def body(self):
            return {
                "_approve[multistep][%s][step]" % self.int_num: str(self.int_num),
                "_approve[multistep][%s][enable]" % self.int_num: "1",
                "_approve[multistep][%s][type]" % self.int_num: self.enum_step.value,
                "_approve[multistep][%s][user_ids][]" % self.int_num: [user.dto.id for user in self.list_users] if self.list_users else ""
            }

    class ApproveStep:
        def __init__(self, flow, int_num, enum_step):
            self.flow = flow
            self.int_num = int_num
            self.enum_step = enum_step
            self.str_result = self.flow.str_result
            self.setting = self.flow.list_settings[int_num - 1]
            self.user_factory = self.flow.user_factory
            # 将当前步骤user存入flow，供下一步骤作为before_user使用
            self._get_users()
            # 迭代时，list_users会被pop
            self.flow.step_user = self.list_users.copy()

        def _get_users(self):
            #  返回运行时实际审批人
            if "负责人主管" == self.enum_step.name:
                self.list_users = self.user_factory.find_authority_user("applier").list_superiors
            elif "上一级审批人主管" == self.enum_step.name:
                # 业务上，上一级审批人主管的前一步骤不允许会签，因此必定只有一人
                self.list_users = self.flow.step_user[0].list_superiors
            elif "任意一人" == self.enum_step.name:
                # 随机选择一人，choices以数组形式返回
                self.list_users = random.choices(self.setting.list_users)
            elif "多人会签" == self.enum_step.name:
                self.list_users = self.setting.list_users
            elif "超管" == self.enum_step.name:
                self.list_users = self.user_factory.find_authority_users("super")[:1]
            elif "越级主管" == self.enum_step.name:
                self.list_users = self.user_factory.find_authority_user("applier").list_superiors[0].list_superiors

            if "撤销" == self.str_result:
                self.list_users = self.user_factory.find_authority_users("applier")[:1]
            elif "无权限" == self.str_result:
                # 切片操作，取第一个元素，以数组形式返回
                self.list_users = self.user_factory.find_authority_users("illegal")[:1]
            elif "驳回" == self.str_result and not self.flow.has_next:
                # 随机抽取上一步骤的审批人，执行驳回操作
                self.list_users = random.choices(self.flow.step_user)
            elif "否决" == self.str_result and not self.flow.has_next:
                # 否决操作，从本步骤标准操作取一个用户
                self.list_users = random.choices(self.list_users)

        @property
        def has_next(self):
            # 该审批级别是否有下一个操作人
            return len(self.list_users)

        def __iter__(self):
            return self

        def __next__(self):
            if not self.has_next:
                raise StopIteration()
            return self.UserStep(self, self.list_users.pop(0))

        class UserStep:
            # 实现功能：每一个User提交approve的具体参数
            # 对外暴露内容：步骤数/状态枚举
            def __init__(self, approve_step, user):
                self.approve_step = approve_step
                self.user = user
                # 会签是否完成
                self.int_num = self.approve_step.int_num

            @property
            def str_result(self):
                # 有下一级审批，则该级别审批设置为通过状态
                return "通过" if self.approve_step.flow.has_next else self.approve_step.str_result

            @property
            def str_expect(self):
                if "撤销" == self.str_result:
                    return "已撤销"
                elif "无权限" == self.str_result or self.approve_step.has_next:
                    # 未完成会签 或无权限
                    return "待%s级审批" % self.int_num
                elif not self.approve_step.has_next and self.str_result in ("否决", "驳回"):
                    return "已否决"
                elif self.approve_step.flow.business_finished:
                    # 当前处于最后一步，所有操作（驳回除外）已完成
                    return "已通过"
                else:
                    return "待%s级审批" % (self.int_num + 1)

            @property
            def str_notifications(self):
                if "驳回" == self.str_result:
                    return ["%s级审批人 %s 审批通过了你的" % (self.int_num, self.user.dto.name), "%s审批驳回了你的" % self.dto.name]
                else:
                    return ["%s级审批人 %s 审批%s了你的" % (self.int_num, self.user.dto.name, self.str_result)]

            def __str__(self):
                return "步骤编号：%s；操作人：%s；操作类型：%s" % (
                    self.int_num, self.user.__str__(), self.str_result)
