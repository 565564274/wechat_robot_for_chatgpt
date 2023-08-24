import os
import json

from utils.log import logger_manager
from utils.singleton import singleton
from utils.root_path import DEFAULT_MESSAGE_PATH


logger = logger_manager.logger


@singleton
class MessageHistory:

    def __init__(self):
        logger.info("initialize MessageHistory")
        self.dir_path = DEFAULT_MESSAGE_PATH
        self.history_files = []
        if not os.path.exists(self.dir_path):
            os.makedirs(self.dir_path)
            logger.info("can't find MessageHistory folder, creat done")
        for file in self.dir_path.glob("*"):
            if file.suffix == ".json":
                self.history_files.append(file.name)

    def sync(self, msg_dict):
        logger.info("start sync messages")

        # dict 到 文件
        for external_userid in msg_dict.keys():
            file_name = external_userid + ".json"
            file_path = self.dir_path / file_name
            messages = msg_dict[external_userid]
            try:
                if file_name not in self.history_files:
                    logger.info(f"create json file for 【{external_userid}】")
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump({external_userid: msg_dict[external_userid]}, f)
                    self.history_files.append(external_userid)
                else:
                    # reset data
                    find = False
                    same = False
                    data = None
                    update_data = []
                    is_write = False
                    with open(file_path, 'r', encoding="utf-8") as f:
                        data = json.load(f)
                    lasted_msgid = data[external_userid][-1]["msgid"]
                    for i in range(len(messages)):
                        if messages[-(i + 1)]["msgid"] == lasted_msgid:
                            find = True
                            if i == 0:
                                same = True
                            else:
                                update_data = messages[-(i + 1) + 1:]
                            break
                    if find:
                        if not same:
                            is_write = True
                            data[external_userid].extend(update_data)
                    else:
                        is_write = True
                        data[external_userid].extend(messages)
                    if is_write:
                        logger.info(f"update json file for 【{external_userid}】")
                        msg_dict[external_userid] = data[external_userid]
                        with open(file_path, "w", encoding="utf-8") as f:
                            json.dump(data, f)
            except Exception as e:
                logger.error(e)
                continue
        # 文件 到 dict
        for file in self.history_files:
            file_path = self.dir_path / file
            uid = file.replace(".json", "")
            if uid not in list(msg_dict.keys()):
                logger.info(f"update json data by 【{file}】")
                with open(file_path, 'r', encoding="utf-8") as f:
                    data = json.load(f)
                msg_dict[uid] = data[uid]

        logger.info("complete sync messages")
        return msg_dict



