import logging
import math

import arrow
from enum import Enum, unique

import pandas
# 通用功能模块
# 审批人类型
from sqlalchemy import func, extract

from component.oauth import BaseSession, HeaderFactory
from component.utils import Strings
from service.skb.pojo import UserCluesDto, EnumCycle, EnumShowDomain
from service.uc.pojo import UserDto, UserDepDto


class Session(BaseSession):
    # 部门结构
    # def get_department_tree(self):
    #     logging.info("获得部门结构")
    #     self._set_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.FORM, HeaderFactory.XRequestedWith.XML)
    #     self.set_authorization(token=self.token)
    #     url = "%s/api/%s.json" % (self._server.domain, self._business.plural)
    #     self.http_response = self._http_session.post(url, data=self._business.apply(self.user))
    #     self._business.id = self.get_json_property("sale", "id")
    #     return self._assert_response()

    # 流量额度消耗统计表
    def quota(self, kwargs):
        self.kwargs = kwargs
        show_domain = EnumShowDomain[self.kwargs["show_domain"]]
        date_type = EnumCycle[self.kwargs["date_type"]]
        start_date = self.kwargs["start_date"]
        end_date = self.kwargs["end_date"]
        did = Strings(self.kwargs["did"]).set_default("")
        uid = Strings(self.kwargs["uid"]).set_default("")

        logging.info("流量额度消耗统计表")
        self._set_head(HeaderFactory.Accept.ALL, HeaderFactory.ContentType.FORM, HeaderFactory.AppToken.SKB)
        self.set_authorization(token=self.token)
        self._http_session.headers.pop("Content-Type")
        url = "%s/api_skb/v1/org/quota/statistics" % self._server.domain
        self.get(url=url,
                 body={"oid": self.user.dto.organization_oid, "showDomain": show_domain.value, "dateType": date_type.name, "startDate": start_date, "endDate": end_date, "did": did, "uid": uid})
        # self.url(url=url, oid=self.user.dto.organization_oid, showDomain=show_domain.value, dateType=date_type.name, startDate=start_date, endDate=end_date, did=did, uid=uid)
        logging.info(self.http_response.as_json("data", "result"))
        # arrow.get("2019-06-01 00:00:00", tzinfo="local").to("utc").format('YYYY-MM-DD HH:mm:ss')

        self.query = self._server.db.session.query(UserCluesDto.uid.label("uid"), func.date_format(
            UserCluesDto.unfold_date, date_type.value).label("cycle"), func.count(UserCluesDto.pid))
        # 过滤企业oid
        self.query = self.query.filter(UserCluesDto.oid == self.user.dto.organization_oid)
        # 过滤无效流量
        self.query = self.query.filter(UserCluesDto.contact != "", UserCluesDto.contact != None)
        #  过滤所属子用户
        self.query = self.query.filter(UserCluesDto.uid.in_([user.uid for user in self.user.list_children()]))
        # 过滤日期
        self.query = self.query.filter(UserCluesDto.unfold_date.between(start_date, end_date))
        # 过滤部门
        if did:
            self.query = self.query.filter(UserCluesDto.uid.in_([user.uid for user in self._uc.db.session.query(UserDto).join(UserDepDto).filter(UserDepDto.department_did == did).all()]))
        # 过滤用户
        if uid:
            self.query = self.query.filter(UserCluesDto.uid == uid)

        if EnumShowDomain.按时间 == show_domain:
            # 按照name（日期）聚合
            self.list_db_results = self.query.group_by("cycle").all()

            return self.http_response.as_json("data", "result").equals([{"name": cycle, "value": count_pid} for uid, cycle, count_pid in self.list_db_results])
        elif EnumShowDomain.按用户 == show_domain:
            self.list_db_results = self.query.group_by("uid").all()
            return self.http_response.as_json("data", "result").equals(
                [{"name": self._uc.db.session.query(UserDto).filter(UserDto.uid == uid).first().name, "value": count_pid} for uid, cycle, count_pid in self.list_db_results])


# class PcDeploy(Oauth):
#     def login(self):
#         super().login()
#
#         self.cookie = self.get_cookies()
#         self._set_head(HeaderFactory.Accept.JSON, HeaderFactory.ContentType.FORM, HeaderFactory.AppToken.CRM)
#         url = self._server.domain + "/api/sso/checkLoginState"
#         self.get(url)
#         self._assert_response()
#         self.token = self.get_json_property("data","userToken")
#         return self


class PcDeploy(Session):

    def login(self):
        # self.user = user
        self.token = self.user.token
        self.uid = self.user.uid
        return self


@unique
class EnumOauth(Enum):
    Oauth = Session
    PcDeploy = PcDeploy
