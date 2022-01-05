import logging, requests
from functools import reduce

from bs4 import BeautifulSoup
from requests import HTTPError

from component.interface import DynamicEnum, IBuilder, IWrapper, IStringify
from component.utils import Contains, Equals


class HeaderFactory:
    class Accept(DynamicEnum):
        _key = "Accept"
        ALL = {_key: "*/*"}
        HTML = {_key: "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"}
        JSON = {_key: "application/json, text/javascript, */*; q=0.01"}

    class ContentType(DynamicEnum):
        _key = "Content-Type"
        HTML = {_key: "text/html; charset=utf-8"}
        JSON = {_key: "application/json; charset=UTF-8"}
        FORM = {_key: "application/x-www-form-urlencoded; charset=UTF-8"}

    # TODO 与系统强相关，应该做到配置文件中
    class AppToken(DynamicEnum):
        _key = "appToken"
        CRM = {"appToken": "f6620ff6729345c8b6101174e695d0ab"}
        SKB = {"app_token": "766fcf9a46064513ac5bb7ae4af620f1"}

    class UserToken(DynamicEnum):
        _key = "userToken"

    class XCsrfToken(DynamicEnum):
        _key = "X-CSRF-Token"

    class Platform(DynamicEnum):
        _key = "platform"
        IK = {_key: "IK"}

    class XRequestedWith(DynamicEnum):
        _key = "X-Requested-With"
        XML = {_key: "XMLHttpRequest"}


# http_session基类
class BaseSession(IBuilder):
    def __init__(self, user):
        self.user = user
        self._server = self.user.factory.server
        self._uc = self.user.factory.uc
        self._http_session = requests.session()
        self.cookie = None
        self.csrf = None

    def _clear_head(self, *args):
        self._http_session.headers.clear()
        self._set_head(*args)

    # 设置消息头
    def _set_head(self, *args):
        [self._http_session.headers.update(header.value) for header in args]
        self._http_session.headers.update({"Cookie": self.cookie})

    def set_authorization(self, **kwargs):
        token_value = "Token " + ",".join(["%s=\"%s\"" % (k, v) for k, v in kwargs.items()])
        self._http_session.headers.update({"Authorization": token_value})

    def url(self, url, **kwargs):
        # 特殊处理get方法，将所有参数强行转换成url
        url += "?"
        url += "&".join(["%s=%s" % (k, v) for k, v in kwargs.items()])
        self.http_response = self.Response(self._http_session.get(url))
        return self.http_response

    def get(self, url, body=None):
        # get请求
        self.http_response = self.Response(self._http_session.get(url, params=body))
        return self.http_response

    # post请求
    def post(self, url, body=None, verify=False):
        kwargs = {"json" if self._http_session.headers.get("Content-Type") == HeaderFactory.ContentType.JSON.value["Content-Type"] else "data": body, "verify": verify}
        self.http_response = self.Response(self._http_session.post(url, **kwargs))
        return self.http_response

    def put(self, url, body):
        self.http_response = self.Response(self._http_session.put(url=url, data=body))
        return self.http_response

    def delete(self, url, body=None):
        self.http_response = self.Response(self._http_session.delete(url=url, data=body))
        return self.http_response

    # uc登录前半部分
    def login(self):
        # TODO apptoken写死，应该参数化
        self._set_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.JSON, HeaderFactory.AppToken.CRM, HeaderFactory.Platform.IK)
        url = self._uc.domain + "/api/sso/login"
        body = {
            "noticeType": "other",
            "password": self.user.password,
            "phone": self.user.phone,
            "type": "login"
        }
        return self.post(url=url, body=body)

    # 获取cookie
    def get_cookies(self):
        return self.http_response.headers["set-cookie"]

    # 获取csrf
    def get_csrf(self):
        return BeautifulSoup(self.http_response.text, "html5lib").select("head>meta[name=\"csrf-token\"]").pop().attrs["content"]

    class Response(IWrapper):
        def __init__(self, delegate):
            # IWrapper实现委托设计模式
            # 输入delegate为requests.response，代理其所有方法
            super().__init__(delegate)
            # 请求失败则抛出异常，中断程序执行
            if self.status_code not in [200, 204]:
                logging.warning("请求失败！url：%s；status_code：%s；reason：%s；text：%s" % (self.url, self.status_code, self.reason, self.text))
            else:
                logging.info("请求url：%s成功" % self.url)
                logging.info("请求body：%s" % self.request.body)
                logging.info("响应body：%s" % self.text if "application/json" in self.headers["content-type"] else 0)

        def as_json(self, *paths):
            # 通过paths逐级查找 response子节点
            actual = reduce(lambda x, y: x[y], [self.json(), *paths])
            # 用子节点创建json对象
            return self.Json(actual)

        class Json:
            # response对象的json模式
            def __init__(self, actual):
                self.actual = actual

            def contains(self, expected):
                return Contains(self.actual).scalar(expected)

            def equals(self, expected):
                return Equals(self.actual).scalar(expected)

            def get(self):
                return self.actual


class BaseUserPo(IStringify):
    def __init__(self, dict_user, organization, factory):
        # 登录密码统一默认值
        self.password = "Ik123456"
        self.dict_user = dict_user
        [self.__setattr__(k, v) for k, v in dict_user.items()]
        self.factory = factory
        self.db_session = self.factory.server.db.session
        # 子类钩子方法：动态注入organization名称过滤条件
        self.dto = self._get_user_dto(organization)
        self.stringify = ["uid","phone"]

        if not hasattr(self, "oauth_klass"):
            # 如果本身包含oauth，则使用oauth
            # 否则使用server提供的oauth
            # 用于处理pc的情况
            self.oauth_klass = self.factory.oauth_klass

    def login(self):
        logging.info(self.__str__())
        self.session = self.oauth_klass(self).login()
        return self

    # 判断属性列表是否与本user对象匹配
    def match(self, dict_attr):
        return all([self.dict_user.get(key) == value for key, value in dict_attr.items()])

    # 判断权限是否匹配与本user对象匹配
    def match_authority(self, authority):
        return hasattr(self, "authority") and authority in self.authority

    @property
    def list_superiors(self):
        logging.info("查询用户：%s上级主管" % self.dto.phone)
        return [user for user in self.factory.users if user.dto.id == self.dto.superior_id]

    # 打印用户相信信息
    @property
    def detail(self):
        return ";".join(["%s:%s" % (key, value) for key, value in self.dict_user.items()])

    # 打印名称和登录名
    def __str__(self):
        return "用户数据持久化封装对象UserPO：" + super().__str__()
