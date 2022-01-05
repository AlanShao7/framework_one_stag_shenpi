import logging
import operator
# from datetime import datetime, timedelta
import arrow
from enum import unique, Enum
from os import path

import pandas
# 通用功能模块
# 审批人类型
from component.interface import IBuilder
from component.oauth import BaseSession, HeaderFactory
from component.utils import Random
from service.jxc.pojo import Warehouse, EnumSeller, EnumCustomer


class Session(BaseSession):
    def __init__(self, user):
        super().__init__(user)
        # 主产品
        self.__product = self.Product(self)
        # 辅助产品：用于组装拆装等流程
        self.__excipient = self.Product(self)
        self.__purchase = self.Purchase(self)
        self.__sale = self.Sale(self)
        self.__storage = self.Storage(self)
        self.__warehouses = {}

    # 设置功能函数

    # 负库存设置
    def negative_inventory(self):
        logging.info("设置为允许负库存")
        self._set_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM, HeaderFactory.XCsrfToken.dynamic(self.csrf))
        url = "%s/settings/system_settings.json" % self._server.domain
        # 发送请求，并从响应中获取id
        self.put(url, body={"key": "negative_inventory", "value": "allow_negative_inventory"})

    # 业务功能函数

    def warehouse(self, name):
        # 获取/生成仓库：注册表单例模式
        if not self.__warehouses.get(name):
            self.__warehouses[name] = Warehouse(name)
        return self.__warehouses[name]

    @property
    def product(self):
        # 主要产品
        return self.__product

    @property
    def excipient(self):
        # 辅助产品
        return self.__excipient

    class Product:
        def __init__(self, session):
            self.session = session
            # 默认值
            # 产品分类：自动化测试
            self.product_category_id = 985
            # 单位：坨
            self.default_unit_id = 3132

        def create(self, record, name=None):
            self.quantity = record["基本数量"]
            self.date = record["单据日期"]
            self.unit_cost = record["单价"]
            self.warehouse = self.session.warehouse(record["仓库"])
            self.total_cost = self.unit_cost * self.quantity
            # 产品编号/名称
            self.number = Random().return_sample(17)
            self.name = name if name else self.number

            logging.info("创建产品：%s" % self.number)
            self.session._set_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.JSON)
            self.session.set_authorization(token=self.session.token, uid=self.session.uid)
            url = "%s/api/v1/products.json" % self.session._server.domain
            body = {
                "product": {
                    "number": self.number,
                    "name": self.name,
                    "product_category_id": self.product_category_id,
                    "spec": "",
                    "note": "",
                    "barcode": "",
                    "default_unit_id": self.default_unit_id,
                    "default_in_unit_id": self.default_unit_id,
                    "current_warning_policy": "no_warning",
                    "split_warning_status": "split_closed",
                    "total_warning_status": "total_closed",
                    "attr_warning_status": "attr_warning_closed",
                    "unit_setting": "single_unit",
                    "batch_status": "batch_closed",
                    "serial_code_status": "serial_closed",
                    "attr_status": "attr_closed",
                    "purchase_price_setting": "purchase_simple_price",
                    "sale_price_setting": "sale_simple_price",
                    "product_units_attributes": [
                        {
                            "unit_id": self.default_unit_id,
                            "unit_name": "坨",
                            "conversion": 1
                        }
                    ],
                    "product_attr_groups_attributes": [
                        {
                            "category": "default_attr",
                            "product_attr_names": "",
                            "product_attr_ids": "",
                            "number": "",
                            "simple_prices_attributes": [],
                            "default_inventory_policies_attributes": []
                        }
                    ]
                }
            }
            if self.quantity:
                body["product"]["product_attr_groups_attributes"][0]["default_inventory_policies_attributes"].append(
                    {"warehouse_id": self.warehouse.id,
                     "warehouse_name": self.warehouse.name,
                     "default_quantity": self.quantity,
                     "default_unit_cost": self.unit_cost,
                     "default_cost": self.total_cost})
            # 发送请求，并从响应中获取id
            self.id = self.session.post(url, body=body).as_json("data", "product", "id").get()
            return self.get_detail()

        def get_detail(self):
            logging.info("查询产品：%s" % self.number)
            self.session.set_authorization(token=self.session.token, uid=self.session.uid)
            url = "%s/api/v1/products/%s" % (self.session._server.domain, self.id)
            # 发送请求，并从响应中获取id
            self.detail = self.session.get(url).as_json("data", "product").get()
            return self

        def delete(self):
            logging.info("删除产品：%s" % self.number)
            self.session._set_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM, HeaderFactory.XCsrfToken.dynamic(self.session.csrf))
            url = "%s/products.json" % self.session._server.domain
            # 发送请求，并从响应中获取id
            self.session.delete(url, body={"id": self.id})

    @property
    def purchase(self):
        return self.__purchase

    class Purchase:
        # 采购相关方法类
        def __init__(self, session):
            self.session = session
            # 默认值

            # 采购单编号
            self.contact_id = 4165

        def apply(self, record, **kwargs):
            # 提交采购单
            # 产品编号/名称
            self.number = Random().return_sample(17)
            self.quantity = record["基本数量"]
            self.date = record["单据日期"]
            self.unit_cost = record["单价"]
            self.warehouse = self.session.warehouse(record["仓库"])
            self.total_cost = self.unit_cost * self.quantity
            self.category = self.Category(kwargs["category"])
            self.session.product.get_detail()
            logging.info("创建%s：%s" % (self.category.name, self.number))
            self.session._set_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM, HeaderFactory.XRequestedWith.XML, HeaderFactory.XCsrfToken.dynamic(self.session.csrf))
            url = "%s/api/purchases.json" % self.session._server.domain
            body = {
                # 供应商：淘宝
                "supplier_id": 384,
                "purchaser_id": EnumSeller.施亮赜.value,
                "contact_id": self.contact_id,
                "category": self.category.category,
                "number": self.number,
                "io_at": self.date,
                "discount": 0.00,
                "deduction": 0.00,
                "amount": self.total_cost,
                "contact_name": "一头烧鸭",
                "contact_mobile": "13681876857",
                "contact_address": "长白山云顶天宫大铜门",
                "supplier_address": "塔克拉玛干精绝古城九层妖塔",
                "total_quantity": self.quantity,
                "total_deduction": 0.00,
                "total_amount": self.total_cost,
                "total_tax_amount": 0.00,
                "total_amount_with_tax": self.total_cost,
                "status": "approving",
                "product_items_attributes[0][product_attr_group_id]": self.session.product.detail["product_attr_groups"][0]["id"],
                "product_items_attributes[0][product_id]": self.session.product.id,
                "product_items_attributes[0][warehouse_id]": self.warehouse.id,
                "product_items_attributes[0][product_unit_id]": self.session.product.detail["product_units"][0]["id"],
                "product_items_attributes[0][name]": self.session.product.name,
                "product_items_attributes[0][product_number]": self.session.product.number,
                "product_items_attributes[0][unit]": "坨",
                "product_items_attributes[0][quantity]": self.quantity,
                "product_items_attributes[0][price]": self.unit_cost,
                "product_items_attributes[0][price_with_tax]": self.unit_cost,
                "product_items_attributes[0][discount]": 0.00,
                "product_items_attributes[0][deduction]": 0.00,
                "product_items_attributes[0][amount]": self.total_cost,
                "product_items_attributes[0][tax_rate]": 0.00,
                "product_items_attributes[0][tax_amount]": 0.00,
                "product_items_attributes[0][amount_with_tax]": self.total_cost,
                "product_items_attributes[0][modified]": self.category.modified,
                "product_items_attributes[0][position]": 0,
                # 允许库存不足
                "allow_negative_inventory": "true"

            }

            self.id = self.session.post(url, body=body).as_json("purchase", "id").get()

            return self

        def approve(self):
            # 审批采购单
            logging.info("审批%s：%s" % (self.category.name, self.number))
            self.session._set_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM, HeaderFactory.XCsrfToken.dynamic(self.session.csrf))
            url = "%s/api/purchases/%s.json" % (self.session._server.domain, self.id)
            body = {
                "status": "approving",
                "approved_level": 1,
                "reason": Random().return_sample(99),
                "resume_executing": "false",
                "allow_negative_inventory": "true",
                "gt_order_quantity": "false"}
            self.session.put(url, body=body)
            return self

        class Category(IBuilder):
            categories = {
                "采购入库": {"category": "in", "modified": "price"}, "采购退货": {"category": "out", "modified": "quantity"}
            }

            def __init__(self, name):
                self.name = name
                self.builder(**self.categories[self.name])

    @property
    def sale(self):
        return self.__sale

    class Sale:
        # 销售相关方法类
        def __init__(self, session):
            self.session = session
            # 默认值
            # 销售单编号
            self.contact_id = 4166

        def apply(self, record, **kwargs):
            # 提交销售单
            # 产品编号/名称
            self.number = Random().return_sample(17)
            self.quantity = record["基本数量"]
            self.date = record["单据日期"]
            self.unit_cost = record["单价"]
            self.warehouse = self.session.warehouse(record["仓库"])
            self.total_cost = self.unit_cost * self.quantity

            self.category = self.Category(kwargs["category"])
            self.session.product.get_detail()
            logging.info("创建%s：%s" % (self.category.name, self.number))
            self.session._set_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM, HeaderFactory.XCsrfToken.dynamic(self.session.csrf))
            url = "%s/api/sales.json" % self.session._server.domain
            body = {
                "customer_id": EnumCustomer.张海艳.value,
                "seller_id": EnumSeller.施亮赜.value,
                "contact_id": self.contact_id,
                "category": self.category.category,
                "number": self.number,
                "io_at": self.date,
                "discount": 0.00,
                "deduction": 0.00,
                "amount": self.total_cost,
                "contact_name": "一头烧鸭",
                "contact_mobile": "13681876857",
                "contact_address": "长白山云顶天宫大铜门",
                "supplier_address": "塔克拉玛干精绝古城九层妖塔",
                "total_quantity": self.quantity,
                "total_deduction": 0.00,
                "total_amount": self.total_cost,
                "total_tax_amount": 0.00,
                "total_amount_with_tax": self.total_cost,
                "status": "approving",
                "product_items_attributes[0][product_attr_group_id]": self.session.product.detail["product_attr_groups"][0]["id"],
                "product_items_attributes[0][product_id]": self.session.product.id,
                "product_items_attributes[0][warehouse_id]": self.warehouse.id,
                "product_items_attributes[0][product_unit_id]": self.session.product.detail["product_units"][0]["id"],
                "product_items_attributes[0][name]": self.session.product.name,
                "product_items_attributes[0][product_number]": self.session.product.number,
                "product_items_attributes[0][unit]": "坨",
                "product_items_attributes[0][quantity]": self.quantity,
                "product_items_attributes[0][price]": self.unit_cost,
                "product_items_attributes[0][price_with_tax]": self.unit_cost,
                "product_items_attributes[0][discount]": 0.00,
                "product_items_attributes[0][deduction]": 0.00,
                "product_items_attributes[0][amount]": self.total_cost,
                "product_items_attributes[0][tax_rate]": 0.00,
                "product_items_attributes[0][tax_amount]": 0.00,
                "product_items_attributes[0][amount_with_tax]": self.total_cost,
                "product_items_attributes[0][modified]": self.category.modified,
                "product_items_attributes[0][position]": 0,
                # 允许库存不足
                "allow_negative_inventory": "true"
            }

            self.id = self.session.post(url, body=body).as_json("sale", "id").get()

            return self

        def approve(self):
            # 审批采购单
            logging.info("审批%s：%s" % (self.category.name, self.number))
            self.session._set_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM, HeaderFactory.XCsrfToken.dynamic(self.session.csrf))
            url = "%s/api/sales/%s.json" % (self.session._server.domain, self.id)
            body = {
                "status": "approving",
                "approved_level": 1,
                "reason": Random().return_sample(99),
                "resume_executing": "false",
                "allow_negative_inventory": "true",
                "gt_order_quantity": "false"}

            self.session.put(url, body=body)
            return self

        class Category(IBuilder):
            categories = {
                "销售退货": {"category": "in", "modified": "quantity"}, "销售出库": {"category": "out", "modified": "price"}
            }

            def __init__(self, name):
                self.name = name
                self.builder(**self.categories[self.name])

    @property
    def storage(self):
        return self.__storage

    class Storage:
        # 库存相关方法类
        def __init__(self, session):
            self.session = session
            # 默认值
            # 产品编号/名称

        def transfer(self, record, **kwargs):
            # 调拨
            self.number = Random().return_sample(17)
            self.quantity = record["基本数量"]
            self.date = record["单据日期"]
            self.from_warehouse, self.to_warehouse = [self.session.warehouse(wh) for wh in record["仓库"].split("=>")]
            self.category = self.Category(kwargs["category"])
            self.session.product.get_detail()
            logging.info("创建%s：%s" % (self.category.name, self.number))
            self.session._set_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM, HeaderFactory.XCsrfToken.dynamic(self.session.csrf))
            url = "%s/api/%s.json" % (self.session._server.domain, self.category.apis)
            body = {
                "from_warehouse_id": self.from_warehouse.id,
                "to_warehouse_id": self.to_warehouse.id,
                "transferred_at": self.date,
                "total_quantity": self.quantity,
                "number": self.number,
                # 允许库存不足
                "allow_negative_inventory": "true",
                "status": "approving",
                "product_items_attributes[0][product_attr_group_id]": self.session.product.detail["product_attr_groups"][0]["id"],
                "product_items_attributes[0][product_id]": self.session.product.id,
                "product_items_attributes[0][product_unit_id]": self.session.product.detail["product_units"][0]["id"],
                "product_items_attributes[0][name]": self.session.product.name,
                "product_items_attributes[0][product_number]": self.session.product.number,
                "product_items_attributes[0][unit]": "坨",
                "product_items_attributes[0][quantity]": self.quantity,
                "product_items_attributes[0][modified]": "quantity"
            }

            self.id = self.session.post(url, body=body).as_json("storage_transfer", "id").get()

            return self

        def storageio(self, record, **kwargs):
            # 调拨
            self.number = Random().return_sample(17)
            self.quantity = record["基本数量"]
            self.date = record["单据日期"]
            self.unit_cost = record["单价"]
            self.warehouse = self.session.warehouse(record["仓库"])
            self.total_cost = self.unit_cost * self.quantity

            self.category = self.Category(kwargs["category"])
            self.session.product.get_detail()
            logging.info("创建%s：%s" % (self.category.name, self.number))
            self.session._set_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM, HeaderFactory.XCsrfToken.dynamic(self.session.csrf))
            url = "%s/api/%s.json" % (self.session._server.domain, self.category.apis)
            body = {
                "number": self.number,
                "total_quantity": self.quantity,
                "total_base_quantity": "",
                "total_amount": self.total_cost,
                "storaged_at": self.date,
                "storageio_category_id": self.category.id,
                "check_id": "",
                "status": "approving",

                "product_items_attributes[0][product_attr_group_id]": self.session.product.detail["product_attr_groups"][0]["id"],
                "product_items_attributes[0][product_id]": self.session.product.id,
                "product_items_attributes[0][product_unit_id]": self.session.product.detail["product_units"][0]["id"],
                "product_items_attributes[0][warehouse_id]": self.warehouse.id,
                "product_items_attributes[0][name]": self.session.product.name,
                "product_items_attributes[0][product_number]": self.session.product.number,
                "product_items_attributes[0][attr_names]": "",
                "product_items_attributes[0][spec]": "",
                "product_items_attributes[0][unit]": "坨",
                "product_items_attributes[0][quantity]": self.quantity,
                "product_items_attributes[0][price]": self.unit_cost,
                "product_items_attributes[0][amount]": self.total_cost,
                "product_items_attributes[0][note]": "",
                "product_items_attributes[0][batch_number]": "",
                "product_items_attributes[0][produced_at]": "",
                "product_items_attributes[0][expired_at]": "",
                "product_items_attributes[0][modified]": "quantity",
                "product_items_attributes[0][position]": 0,
                # 允许库存不足
                "allow_negative_inventory": "true"
            }

            self.id = self.session.post(url, body=body).as_json("storageio", "id").get()

            return self

        def package(self, record, **kwargs):
            self.number = Random().return_sample(17)
            self.quantity = record["基本数量"]
            self.date = record["单据日期"]
            # category.status:
            # 0：组装入库：product：成品；excipient：配件
            # 1：组装出库：product：配件；excipient：成品
            # 2：拆装入库：product：配件；excipient：成品
            # 3：拆装出库：product：成品；excipient：配件
            self.category = self.Category(kwargs["category"])
            # 组装入库/拆装出库
            if self.category.status in [0, 3]:
                self.finished_item = self.session.product
                self.part_items = self.session.excipient
            else:
                self.finished_item = self.session.excipient
                self.part_items = self.session.product

            # 如果输入单价==0，则为出库单
            # 出库单以主产品的当前统计价格为准
            self.unit_cost = record["单价"] or self.session.product.get_detail().detail["product_attr_groups"][0]["unit_cost"]
            self.warehouse = self.session.warehouse(record["仓库"])
            self.total_cost = self.unit_cost * self.quantity
            self.session.product.get_detail()
            logging.info("创建%s：%s" % (self.category.name, self.number))
            self.session._set_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM, HeaderFactory.XCsrfToken.dynamic(self.session.csrf))
            url = "%s/%s.json" % (self.session._server.domain, self.category.apis)
            body = {
                "%s[number]" % self.category.api: self.number,
                "%s[date]" % self.category.api: self.date,
                "%s[cost]" % self.category.api: 0.00,
                "%s[total_quantity]" % self.category.api: self.quantity,
                "%s[total_cost]" % self.category.api: self.total_cost,
                "%s[status]" % self.category.api: "approving",
                # 允许库存不足
                "%s[allow_negative_inventory]" % self.category.api: "true",
                "%s[fifo_total_cost]" % self.category.api: self.total_cost,
            }

            body.update(self.__package_attributes(True))
            body.update(self.__package_attributes(False))

            self.id = self.session.post(url, body=body).as_json(self.category.api, "id").get()

            return self

        def __package_attributes(self, is_finished):
            # is_finished：生成成品/零件
            product = self.finished_item if is_finished else self.part_items
            title = "[finished_item_attributes]" if is_finished else "[part_items_attributes][0]"
            # product用Excel指定仓库，excipient用属性仓库
            warehouse = self.warehouse if product == self.session.product else product.warehouse

            body = {"product_id": product.id,
                    "product_attr_group_id": product.detail["product_attr_groups"][0]["id"],
                    "product_unit_id": product.detail["product_units"][0]["id"],
                    "warehouse_id": warehouse.id, "name": product.name, "number": product.number,
                    "attr": "", "spec": "", "warehouse_name": warehouse.name, "unit_name": "坨",
                    "quantity": self.quantity, "unit_cost": self.unit_cost, "cost": self.total_cost,
                    "batch_number": "", "produced_at": "", "expired_at": "", "conversion": 1, "note": "",
                    "modified": "quantity", "position": 0, "fifo_unit_cost": self.unit_cost,
                    "fifo_cost": self.total_cost}
            return {"%s%s[%s]" % (self.category.api, title, k): v for k, v in body.items()}

        def approve(self):
            # 审批出入库单
            logging.info("审批%s：%s" % (self.category.name, self.number))
            self.session._set_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM, HeaderFactory.XCsrfToken.dynamic(self.session.csrf))
            url = "%s/api/%s/%s.json" % (self.session._server.domain, self.category.apis, self.id)
            body = {
                "status": "approving",
                "approved_level": 1,
                "reason": Random().return_sample(99),
                "allow_negative_inventory": "true"}

            self.session.put(url, body=body)
            return self

        class Category(IBuilder):
            categories = {"调拨": {"apis": "storage_transfers"},
                          "其他入库": {"id": 2558, "apis": "storageios"},
                          "其他出库": {"id": 2559, "apis": "storageios"},
                          "组装入库": {"status": 0, "api": "package", "apis": "packages"},
                          "组装出库": {"status": 1, "api": "package", "apis": "packages"},
                          "拆装入库": {"status": 2, "api": "unpackage", "apis": "unpackages"},
                          "拆装出库": {"status": 3, "api": "unpackage", "apis": "unpackages"}
                          }

            def __init__(self, name):
                self.name = name
                self.builder(**self.categories[self.name])


class LxDeploy(Session):
    def login(self):
        # self.user = user
        self.token = self.user.token
        self.uid = self.user.uid
        self.get(self._server.domain + "/dingtalk/sessions/new", body={"token": self.user.token, "uid": self.user.uid})
        self.cookie = self.get_cookies()
        self.csrf = self.get_csrf()
        return self


# class Statistic:
#     def __init__(self, workbook, worksheet):
#         # # 转换成二位数组
#         # self.lis_provider = Arrays(list_provider).dual_vector_foil()
#         # # 数据格式标准化
#         # self.lis_provider = [serialize(prov).get() for prov in self.lis_provider]
#         # # 数组-字典转换成字典-数组
#         # self.dict_provider = self.__list_to_dict(self.lis_provider)
#         # # 字典-数组转换成pandas.DataFrame
#         # self.data_frame = self.__data_frame = pandas.DataFrame(self.dict_provider)
#         # logging.info(path.dirname(__file__))
#         # workbook = pandas.ExcelFile("进销存.xlsx")
#         self.__data_frame = pandas.read_excel(path.join(path.dirname(__file__), workbook), sheet_name=worksheet)
#         self.__data_frame["日期"] = pandas.to_datetime(self.__data_frame["日期"])
#         self.data_frame = self.__data_frame
#
#         # df2 = df1.merge(df_abbrev, on='state')  # 类似数据库的 inner join，不匹配数据不会显示
#
#     def to_datetime(self, *args):
#         for column in args:
#             self.__data_frame[column] = pandas.to_datetime(self.__data_frame[column])
#         return self
#
#     #  恢复出厂设置
#     #  重置group/resample/切片/set_index等，但不会重置to_datetime等数据类型变换操作
#     def restore(self):
#         self.data_frame = self.__data_frame
#         return self
#
#     def set_index(self, index):
#         self.data_frame = self.data_frame.set_index(index)
#         return self
#
#     def day(self, delta=0):
#         # years,months,weeks,days,hours，seconds，microseconds
#         date_time = arrow.now().shift(days=delta).format("YYYY-MM-DD")
#         self.data_frame = self.data_frame[date_time:date_time]
#         return self
#
#     def month(self, delta=0):
#         date_time = arrow.now().shift(months=delta).format("YYYY-MM")
#         self.data_frame = self.data_frame[date_time]
#         return self
#
#     def resample(self, resample, aggregate="sum"):
#         self.data_frame = self.data_frame.resample(resample).aggregate(aggregate)
#         return self
#
#     def group(self, group, aggregate="sum"):
#         self.data_frame = self.data_frame.groupby(self.data_frame[group]).aggregate(aggregate)
#         return self
#
#     def log(self):
#         logging.info("\n" + self.data_frame.__str__())
#
#         # logging.info("\n" + self.data_frame[self.data_frame.时间==datetime.strptime("").month].__str__())
#
#     def providers(self):
#         list_provider = list()
#         list_keys = self.data_frame.keys()
#         for record in self.data_frame.values:
#             dict_record = dict(zip(list_keys, record))
#             list_provider.append([dict_record])
#         return list_provider
#
#         # return [self.__business_factory(dict(zip(, x))) for x in self.data_frame.values]
#
#     def __business_factory(self, dict_provider):
#         return dict_provider["business"].value(dict_provider)
#
#     # logging.info("\n" + data_frame_by_time.resample("w").agg({"amount": numpy.sum, "outbound": "sum", "return_form": "sum"}).__str__())
#
#     # for name, group in data_frame.groupby("io_at_week"):
#     #     logging.info(name)
#     #     # logging.info(group["product"].sum())
#     #     logging.info(group["amount"].sum())
#
#     # group.apply(lambda row: 'Dear Mr. %s' % row.last_name if row.gender == 'Male' else 'Dear Ms. %s' % row.last_name, axis=1)
#
#     def __list_to_dict(self, list_provider):
#         dict_provider = {k: list() for k in list_provider[0].keys()}
#         for provider in list_provider:
#             for k, v in provider.items():
#                 dict_provider[k].append(v)
#         return dict_provider


@unique
class EnumOauth(Enum):
    Oauth = Session
    LxDeploy = LxDeploy
