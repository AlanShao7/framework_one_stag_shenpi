import unittest2, HtmlTestRunner

from service.skb.report.driver import ReportDriver


def executor():
    # 创建测试加载器
    loader = unittest2.TestLoader()
    # 创建测试包
    suite = unittest2.TestSuite()
    # 遍历所有测试类
    for test_class in [ReportDriver]:
        # 从测试类中加载测试用例
        tests = loader.loadTestsFromTestCase(test_class)
        # 将测试用例添加到测试包中
        suite.addTests(tests)
    return suite


if __name__ == '__main__':
    HtmlTestRunner.HTMLTestRunner(descriptions=True, failfast=False, buffer=False, report_title="report_title",
                                  report_name="report_name", template=None, resultclass=None, add_timestamp=True,
                                  open_in_browser=False, combine_reports=True, template_args=None).run(executor())
