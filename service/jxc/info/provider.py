from service.jxc.utils import LxDeploy
from component.confiuration import EnvironmentEnum, PlatformEnum

# 该文件为所有审批功能的数据提供者（approval）
# PC/Android/IOS大部分用户及配置信息为公用
# 所有公用配置信息存储在IOS下
# PC专用用户存储在PC下

# data = [
#     # 产品汇总表
#     []
# ]

# data = {EnumBusiness.产品:
#             [[{"authority": "super", "number": "zhy001", "name": "普通单单位产品001", "spec": "100ml", "unit_name": "瓶", "current_warning_policy": "no_warning", "split_warning_status": "split_closed",
#                "total_warning_status": "total_closed", "attr_warning_status": "attr_warning_closed", "attr_status": "attr_opened", "price_policy_setting": "multi_unit_policy",
#                "unit_setting": "multi_unit", "batch_status": "batch_opened", "serial_code_status": "serial_closed"}],
#              [{"authority": "super", "number": "zhy001", "name": "普通单单位产品001", "spec": "100ml", "unit_name": "瓶", "current_warning_policy": "no_warning", "split_warning_status": "split_closed",
#                "total_warning_status": "total_closed", "attr_warning_status": "attr_warning_closed", "attr_status": "attr_opened", "price_policy_setting": "multi_unit_policy",
#                "unit_setting": "multi_unit", "batch_status": "batch_opened", "serial_code_status": "serial_closed"}]]
#         }
