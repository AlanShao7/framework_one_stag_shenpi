from string import Template

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker


class DbConfig:
    template = "${driver}://${name}:${pwd}@${url}:${port}/${schema}?charset=${charset}"

    def __init__(self, **kwargs):
        self.driver = "mysql+pymysql"
        self.charset = "utf8"
        self.port = "3306"
        [self.__setattr__(k, v) for k, v in kwargs.items()]

    # 初始化数据库连接
    def builder(self):
        self.engine = create_engine(self.__str__(), echo=True)
        self.session = sessionmaker(bind=self.engine)()
        self.metadata = MetaData(self.engine)
        return self

    def __str__(self):
        return Template(self.template).substitute(self.__dict__)
