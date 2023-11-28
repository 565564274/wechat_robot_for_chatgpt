import requests

from utils import resource_pool
from utils.log import logger_manager


logger = logger_manager.logger


class WxOfficialApi:

    def __init__(self):
        self.verify_check = resource_pool["wx_official_check"]
        self.verify_userid = resource_pool["secret"]["verify_userid"]
        self.base_url = "http://172.17.0.1:9982/"

    def bind(self, code: str, external_userid_by_qywx: str):
        if not self.verify_check:
            return True
        path = f"bind?userid={self.verify_userid}&code={code}&external_userid_by_qywx={external_userid_by_qywx}"
        url = self.base_url + path
        resp = requests.request(url=url, method="get")
        return True if resp.text == "true" else False

    def bind_check(self, external_userid_by_qywx: str):
        if not self.verify_check:
            return True
        path = f"bind_check?userid={self.verify_userid}&external_userid_by_qywx={external_userid_by_qywx}"
        url = self.base_url + path
        resp = requests.request(url=url, method="get")
        return True if resp.text == "true" else False

