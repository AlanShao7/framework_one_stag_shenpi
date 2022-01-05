from service.jxc.utils import LxDeploy
from component.confiuration import EnvironmentEnum, PlatformEnum

# 该文件为所有审批功能的数据提供者（approval）
# PC/Android/IOS大部分用户及配置信息为公用
# 所有公用配置信息存储在IOS下
# PC专用用户存储在PC下
users = {
    EnvironmentEnum.TEST: {PlatformEnum.IOS: [{"uid": "45516652d2e0487a626e", "token": "4e57bf7928f8d042d2183573032f06", "authority": "super"}]}}
oauth_klasses = {
    EnvironmentEnum.TEST: {
        PlatformEnum.钉钉: LxDeploy
    }
}

# data = {EnumBusiness.销售管理:
#             [[{"business": EnumSale.出库单, "io_at": "2019-01-08", "customer": "张海艳", "seller": "张海艳", "product": {"name": "报表测试专用产品001", "quantity": 21, "price": 39}, "warehouse": EnumWarehouse.上海仓}],
#              [{"business": EnumSale.退货单, "io_at": "2019-05-14", "customer": "张海艳", "seller": "张海艳", "product": {"name": "报表测试专用产品001", "quantity": 17, "price": 13}, "warehouse": EnumWarehouse.上海仓}]]
#         }
