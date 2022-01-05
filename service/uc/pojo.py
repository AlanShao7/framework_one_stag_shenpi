from sqlalchemy import Column, String, Integer, DATETIME, ForeignKey
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, backref

from component.confiuration import Context
from component.oauth import BaseUserPo

Base = declarative_base()
db_config = Context.config.uc.environment.platform.db


class UserDto(Base):
    @declared_attr
    def __tablename__(self):
        return db_config.table_name[self.__name__]

    uid = Column(Integer, primary_key=True)
    superior_uid = Column(Integer)
    name = Column(String)
    phone = Column(String)

    @declared_attr
    def organization_oid(self):
        return Column(Integer, ForeignKey("%s.oid" % db_config.table_name["OrganizationDto"]))

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

    did = Column(Integer, primary_key=True)
    name = Column(String)
    organization_oid = Column(Integer)
    parent_did = Column(Integer)
    path_did = Column(String)

    @declared_attr
    def users(self):
        return relationship("UserDepDto", back_populates="department")


class UserDepDto(Base):
    @declared_attr
    def __tablename__(self):
        return db_config.table_name[self.__name__]

    user_uid = Column(Integer, ForeignKey("uc_users.uid"), primary_key=True)
    department_did = Column(Integer, ForeignKey("uc_departments.did"), primary_key=True)

    user = relationship("service.uc.pojo.UserDto", back_populates="departments")
    department = relationship("service.uc.pojo.DepartmentDto", back_populates="users")


class OrganizationDto(Base):
    @declared_attr
    def __tablename__(self):
        return db_config.table_name[self.__name__]

    oid = Column(Integer, primary_key=True)
    name = Column(String)


class UcUserPo(BaseUserPo):

    def _get_user_dto(self, organization):
        # uc中的user保存在uc库中
        self.db_session = self.factory.uc.db.session
        Base.metadata = db_config.metadata
        return self.db_session.query(UserDto).join(OrganizationDto).filter(UserDto.uid == self.uid).filter(OrganizationDto.name == organization["name"]).first()

    # 查找子部门用户
    def list_children(self):
        return self.db_session.query(UserDto).join(UserDepDto).join(DepartmentDto).filter(
            DepartmentDto.path_did.like("%%%s%%" % self.dto.departments[0].department_did)).all()
#
# class DepartmentTreeVO:
#     #  部门树结构
#     def __init__(self, dict_department_tree, parent=0):
#         self.department_tree = dict_department_tree
#         [self.__setattr__(k, v) for k, v in self.department_tree.items()]
#         self.departmentTreeVOList = [DepartmentTreeVO(department, self) for department in self.departmentTreeVOList]
