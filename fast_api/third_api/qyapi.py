import requests
import json
import random
import string
import time

from utils import resource_pool
from pprint import pprint
from datetime import datetime
from utils.log import logger_manager


logger = logger_manager.logger


class QiyeApi:

    def __init__(self):
        self.base_url = resource_pool["qyapi"]["base_url"]
        self.ID = resource_pool["qyapi"]["qiye_id"]
        self.SECRET = resource_pool["qyapi"]["kefu_Secret"]

        # 获取ACCESS_TOKEN
        self.ACCESS_TOKEN_time = datetime.now()
        self.ACCESS_TOKEN = self.get_access_token(first=True)
        self.cursor = None

    def get_access_token(self, first=False):
        used_time = (datetime.now() - self.ACCESS_TOKEN_time).total_seconds()
        if used_time > 7200 or first:
            path = f"cgi-bin/gettoken?corpid={self.ID}&corpsecret={self.SECRET}"
            url = self.base_url + path
            resp = requests.request(url=url, method="get")
            resp = json.loads(resp.text)
            self.ACCESS_TOKEN_time = datetime.now()
            self.ACCESS_TOKEN = resp["access_token"]
        return self.ACCESS_TOKEN

    def get_kefu(self):
        path = f"cgi-bin/kf/account/list?access_token={self.get_access_token()}"
        url = self.base_url + path
        params = {
            "offset": 0,
            "limit": 100
        }
        resp = requests.request(url=url, method="post", json=params)
        resp = json.loads(resp.text)
        return resp["access_token"]

    def sync_msg(self, token, open_kfid):
        path = f"cgi-bin/kf/sync_msg?access_token={self.get_access_token()}"
        url = self.base_url + path
        params = {
            "token": token,
            "limit": 1000,
            "voice_format": 0,
            "open_kfid": open_kfid}
        if self.cursor:
            # 上一次调用时返回的next_cursor，第一次拉取可以不填。若不填，从3天内最早的消息开始返回。
            params.update({"cursor": self.cursor})
        resp = requests.request(url=url, method="post", json=params)
        resp = json.loads(resp.text)
        if resp["errcode"] != 0:
            logger.error(resp)
            assert False, "sync_msg failed"
        if "next_cursor" in resp:
            if resp["next_cursor"]:
                self.cursor = resp["next_cursor"]
        # 转换时间戳
        for msg in resp["msg_list"]:
            msg["send_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(msg["send_time"])))
        return resp["msg_list"]

    def send_msg(self, external_userid, open_kfid, content="已收到"):
        path = f"cgi-bin/kf/send_msg?access_token={self.get_access_token()}"
        url = self.base_url + path
        params = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgid": ''.join(random.sample(string.ascii_letters + string.digits, 32)),
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        resp = requests.request(url=url, method="post", json=params)
        resp = json.loads(resp.text)
        if resp["errcode"] != 0:
            logger.error(resp)
            assert False, "send_msg failed"
        return resp

    def send_media(self, external_userid, open_kfid, media_id, media_type="image"):
        path = f"cgi-bin/kf/send_msg?access_token={self.get_access_token()}"
        url = self.base_url + path
        params = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgid": ''.join(random.sample(string.ascii_letters + string.digits, 32)),
            "msgtype": media_type,
            media_type: {
                "media_id": media_id
            }
        }
        resp = requests.request(url=url, method="post", json=params)
        resp = json.loads(resp.text)
        if resp["errcode"] != 0:
            logger.error(resp)
            assert False, "send_media failed"
        return resp

    def get_service_state(self, external_userid, open_kfid):
        path = f"cgi-bin/kf/service_state/get?access_token={self.get_access_token()}"
        url = self.base_url + path
        params = {
            "external_userid": external_userid,
            "open_kfid": open_kfid,
        }
        resp = requests.request(url=url, method="post", json=params)
        resp = json.loads(resp.text)
        # https://developer.work.weixin.qq.com/document/path/94669
        '''
        0	未处理	新会话接入（客户发消息咨询）。可选择：1.直接用API自动回复消息。2.放进待接入池等待接待人员接待。3.指定接待人员（接待人员须处于“正在接待”中，下同）进行接待
        1	由智能助手接待	可使用API回复消息。可选择转入待接入池或者指定接待人员处理。
        2	待接入池排队中	在待接入池中排队等待接待人员接入。可选择转为指定人员接待
        3	由人工接待	人工接待中。可选择转接给其他接待人员处理或者结束会话。
        4	已结束/未开始	会话已经结束或未开始（客户进入会话，还没上行消息）。不允许通过API变更会话状态，客户发消息咨询后会话状态变为“未处理”。接待人员通过客户端在已结束会话中成功发送消息后，会话状态变为“由人工接待”，此时会产生会话状态变更回调事件（4-重新接入已结束/已转接会话）。
        {'errcode': 0, 'errmsg': 'ok', 'service_state': 3, 'servicer_userid': 'GongSongTao'}
        接待人员的userid。第三方应用为密文userid，即open_userid。仅当state=3时有效
        '''
        if resp["errcode"] != 0:
            logger.error(resp)
            assert False, "get_service_state failed"
        else:
            return resp

    def transfer_service_state(self, external_userid, open_kfid, service_state, servicer_userid=None):
        path = f"cgi-bin/kf/service_state/trans?access_token={self.get_access_token()}"
        url = self.base_url + path
        params = {
            "external_userid": external_userid,
            "open_kfid": open_kfid,
            "service_state": service_state
        }
        if service_state == 3:
            assert servicer_userid, "未指派接待人员"
            params["servicer_userid"] = servicer_userid
        resp = requests.request(url=url, method="post", json=params)
        resp = json.loads(resp.text)
        # https://developer.work.weixin.qq.com/document/path/94669
        '''
        0	未处理	新会话接入（客户发消息咨询）。可选择：1.直接用API自动回复消息。2.放进待接入池等待接待人员接待。3.指定接待人员（接待人员须处于“正在接待”中，下同）进行接待
        1	由智能助手接待	可使用API回复消息。可选择转入待接入池或者指定接待人员处理。
        2	待接入池排队中	在待接入池中排队等待接待人员接入。可选择转为指定人员接待
        3	由人工接待	人工接待中。可选择转接给其他接待人员处理或者结束会话。
        4	已结束/未开始	会话已经结束或未开始（客户进入会话，还没上行消息）。不允许通过API变更会话状态，客户发消息咨询后会话状态变为“未处理”。接待人员通过客户端在已结束会话中成功发送消息后，会话状态变为“由人工接待”，此时会产生会话状态变更回调事件（4-重新接入已结束/已转接会话）。
        {'errcode': 0, 'errmsg': 'ok', 'service_state': 3, 'servicer_userid': 'GongSongTao'}
        接待人员的userid。第三方应用为密文userid，即open_userid。仅当state=3时有效
        '''
        if resp["errcode"] != 0:
            logger.error(resp)
            assert False, "transfer_service_state failed"
        else:
            return resp

    def upload_media(self, media_name, media_path, media_type="image"):
        path = f"cgi-bin/media/upload?access_token={self.get_access_token()}&type={media_type}"
        url = self.base_url + path
        files = {
            'media': (media_name, open(media_path, 'rb')),
        }
        resp = requests.request(url=url, method="post", files=files)
        resp = json.loads(resp.text)
        if resp["errcode"] != 0:
            logger.error(resp)
            assert False, "send_msg failed"
        return resp["media_id"]

    def get_user_info_by_external_userid(self, external_userid, need_enter_session_context=1):
        path = f"cgi-bin/kf/customer/batchget?access_token={self.get_access_token()}"
        url = self.base_url + path
        params = {
            "external_userid_list": [external_userid],
            "need_enter_session_context": need_enter_session_context
        }
        resp = requests.request(url=url, method="post", json=params)
        resp = json.loads(resp.text)
        if resp["errcode"] != 0:
            logger.error(resp)
            assert False, "get_user_info_by_external_userid failed"
        return resp


if __name__ == '__main__':
    a = QiyeApi()
    # a.get_access_token()
    # a.sync_msg("ENC6YBsoDwLX6Axn8yNVFXhBUKFV8PNU5Kiz6SCsPTkSwMz", "wkLmpmJwAAZ2YdbsRoYGVl1449uVLjiA")
    # a.send_msg("wmLmpmJwAAg4rw6Um6uTRCcPJiHJQ-jA", "wkLmpmJwAAZ2YdbsRoYGVl1449uVLjiA", 1)
    # a.upload_media(r"C:\Users\songtao.gong\Desktop\cc.jpeg", )
    # a.send_media("wmLmpmJwAAg4rw6Um6uTRCcPJiHJQ-jA", "wkLmpmJwAAZ2YdbsRoYGVl1449uVLjiA", "3TJ5DPlGA7gLTbnVfrqRpynFvmhMtLSdmDlAX6FRJjt4TKi23O5nM4c3CUb9pizrm")
    a.get_user_info_by_external_userid("wmLmpmJwAA4S9yUP9GLx8LR6u6gUcE4Q",)

