from enum import Enum, IntEnum

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

from component.confiuration import Context

Base = declarative_base()
db_config = Context.config.server.environment.platform.db


class EnumCycle(Enum):
    day = "%Y-%m-%d"
    month = "%Y-%m"
    year = "%Y"
    week = "%u"


class EnumShowDomain(IntEnum):
    按时间 = 1
    按用户 = 2


# ———————————————————数据持久化对象———————————————————
class UserCluesDto(Base):
    __tablename__ = "user_clues"

    id = Column(Integer, primary_key=True)
    oid = Column(Integer)
    uid = Column(Integer)
    pid = Column(String)
    unfold_date = Column(DateTime(timezone=False))
    contact = Column(String)
