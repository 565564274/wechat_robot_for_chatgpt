import requests
import os

from datetime import datetime
from utils.log import logger_manager
from utils.root_path import DEFAULT_FILE_PATH


logger = logger_manager.logger


def save_file_by_url(url, dir_name, file_type="image"):
    dir_path = DEFAULT_FILE_PATH / dir_name
    file_name = None
    file_path = None
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    try:
        if file_type == "image":
            image_data = requests.get(url).content
            # 获得图片后缀
            # file_suffix = url[url.find("image/") + 6:]
            # todo: 后缀需要适配
            file_suffix = "png"
            # 拼接图片名（包含路径）
            file_name = datetime.strftime(datetime.now(), '%Y-%m-%d_%H-%M-%S')
            file_path = '{}{}{}.{}'.format(dir_path, os.sep, file_name, file_suffix)
            # 下载图片，并保存到文件夹中
            with open(file_path, "wb") as f:
                f.write(image_data)
        else:
            assert False, "不支持的格式"
    except Exception as e:
        logger.error(e)
    return [file_name, file_path]


if __name__ == '__main__':
    a = 'https://oaidalleapiprodscus.blob.core.windows.net/private/org-b9DTP8sCyHe4puuvc3VsDj4M/user-0ZgVoBvoO0jFg92rmpDR7yOm/img-tAkLkvIDl26yRIjxEM8z8Ihj.png?st=2023-04-26T12%3A21%3A32Z&se=2023-04-26T14%3A21%3A32Z&sp=r&sv=2021-08-06&sr=b&rscd=inline&rsct=image/png'
    a = 'https://img-blog.csdnimg.cn/20210601190357805.png'
    save_file_by_url(a, ".\\")


