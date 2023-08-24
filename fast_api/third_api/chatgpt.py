import openai

from utils import resource_pool
from utils.log import logger_manager


logger = logger_manager.logger


class ChatgptApi:

    def __init__(self, key=None):
        proxy = resource_pool["chatgpt"]["proxy"]
        api_key = resource_pool["chatgpt"]["api_key"]
        self.model_name = resource_pool["chatgpt"]["model_name"]
        # 需要根据url地址的协议来选择相应的代理
        openai.proxy = {
            "http": proxy,
            "https": proxy
        }
        openai.api_key = key if key else api_key

    def model(self):
        return openai.Model.list()

    def get_key(self):
        return openai.api_key

    def chat(self, messages):
        result = []
        for message in messages:
            result.append(
                {
                    "role": message[0],
                    "content": message[1]
                }
            )
        try:
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=result
            )
        except Exception as e:
            logger.error(e)
            if "This model's maximum context length is 4097 tokens" in str(e):
                return {"role": "assistant", "content": "已达到该Model最大对话长度，请重新回复【开始聊天】，重新开始与chatgpt对话"}
            elif "check your plan and billing details" in str(e):
                return {"role": "assistant", "content": "这个ChatGPT账号没钱不能玩了，快去提醒他充值"}
            elif "Connection" in str(e):
                # Error communicating with OpenAI:
                # ('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))
                return {"role": "assistant", "content": "服务器科学上网有点问题，快去提醒他看看"}
            else:
                return {"role": "assistant", "content": "未知错误，请重新回复【开始聊天】，重新开始与chatgpt对话"}
        return {"role": "assistant", "content": response.choices[0].message.content}

    def image(self, messages):
        try:
            response = openai.Image.create(
                prompt=messages,
                n=1,
                size="1024x1024"
            )
            image_url = response['data'][0]['url']
        except Exception as e:
            logger.error(e)
            return [False, "你的描述正常吗？\n请重新回复【生成图片】，重新开始由OpenAI生成图片"]
        return [True, image_url]


if __name__ == '__main__':
    a = ChatgptApi()
    a.chat(
        [["user", "你好"], ]
    )
    print(a.model())
