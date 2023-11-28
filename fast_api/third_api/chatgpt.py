import openai
import httpx

from openai import OpenAI
from utils import resource_pool
from utils.log import logger_manager


logger = logger_manager.logger


class ChatgptApi:

    def __init__(self, key=None):
        self.http_client = httpx.Client(
            proxies=resource_pool["chatgpt"]["proxy"],
            timeout=30
        )
        self.client = OpenAI(
            api_key=key if key else resource_pool["chatgpt"]["api_key"],
            max_retries=1,
            http_client=self.http_client,
            timeout=30
        )
        self.model_name = resource_pool["chatgpt"]["model_name"]

    def model(self):
        return self.client.models.list()

    def get_key(self):
        return self.client.api_key

    def update_key_self(self):
        logger.info("********************************" * 6)
        used = self.get_key()
        if used not in resource_pool["chatgpt"]["api_key_option"]:
            logger.info(f"开始自更新OpenAI的api_key【{used}】,替换为api_key_option")
            new = resource_pool["chatgpt"]["api_key_option"][0]
        else:
            logger.info(f"开始自更新OpenAI的api_key【{used}】,更换api_key_option")
            index = resource_pool["chatgpt"]["api_key_option"].index(used)
            if index < len(resource_pool["chatgpt"]["api_key_option"]) - 1:
                index += 1
            else:
                index = len(resource_pool["chatgpt"]["api_key_option"]) - 1
            new = resource_pool["chatgpt"]["api_key_option"][index]

        self.client = OpenAI(
            api_key=new,
            http_client=self.http_client
        )
        logger.info("自更新完成: " + str(self.get_key()))
        logger.info("********************************" * 6)

    def chat(self, messages, first=True, role=None):
        result = []
        for message in messages:
            result.append(
                {
                    "role": message[0],
                    "content": message[1]
                }
            )
        if role:
            result[0] = {"role": "system", "content": role}
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=result,
                timeout=30
            )
        except Exception as e:
            logger.error(e)
            if "This model's maximum context length" in str(e):
                return {"role": "assistant", "content": "已达到该Model最大对话长度，请重新回复【开始聊天】，重新开始与chatgpt对话"}
            elif "check your plan and billing details" in str(e):
                # Error code: 429 - {'error': {'message': 'You exceeded your current quota, please check your plan and billing details.', 'type': 'insufficient_quota', 'param': None, 'code': 'insufficient_quota'}}
                self.update_key_self()
                if first:
                    return self.chat(messages, first=False)
                return {"role": "assistant", "content": "这个ChatGPT账号没钱不能玩了，快去提醒他充值"}
            elif "Connection" in str(e) or "Error communicating with OpenAI" in str(e):
                # Error communicating with OpenAI:
                # ('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))
                return {"role": "assistant", "content": "服务器科学上网有点问题，快去提醒他看看\nTips:可能是节点网络波动，一会再试试"}
            elif "Incorrect API key provided" in str(e):
                self.update_key_self()
                if first:
                    return self.chat(messages, first=False)
                # Incorrect API key provided: sk-Tp6UB***************************************h4q7.
                # You can find your API key at https://platform.openai.com/account/api-keys.
                return {"role": "assistant", "content": "这个ChatGPT账号的API key不对，快去提醒他看看"}
            elif "Rate limit reached" in str(e):
                # Rate limit reached for default-gpt-3.5-turbo-16k in organization org-vwVh2d6OFgt2xjsjnSEQJp8Z on requests per min. Limit: 3 / min.
                # Please try again in 20s. Contact us through our help center at help.openai.com if you continue to have issues.
                # Please add a payment method to your account to increase your rate limit. Visit https://platform.openai.com/account/billing to add a payment method.
                return {"role": "assistant", "content": "请求频率太高了，稍后再试"}
            else:
                return {"role": "assistant", "content": "未知错误，请重新回复【开始聊天】，重新开始与chatgpt对话"}
        return {"role": "assistant", "content": response.choices[0].message.content}

    def image(self, messages, first=True):
        try:
            response = self.client.images.generate(
                prompt=messages,
                model="dall-e-3",
                size="1024x1024",
                quality="hd",
                style="vivid",
                n=1,
                timeout=30
            )
            image_url = response.data[0].url
        except openai.APIError as e:
            logger.error(e)
            if e.code == "content_policy_violation":
                return [False, "你的描述被OpenAI的安全系统拒绝，生成失败\n请重新输入描述，开始由OpenAI生成图片"]
            elif e.code == "rate_limit_exceeded":
                return [False, "超过接口访问频率限制1/1min，生成失败\n请稍后重新输入描述，开始由OpenAI生成图片\n"
                               "Tips:由于所有人使用同一个账号，最新的Model[DALL·E 3]接口又有访问频率限制，"
                               "也就是说这1分钟刚好有其他人用了，你只能等下一分钟，所以等等再试试吧。\n"
                               "或者你可以赞助我，多接入几个账号或者直接接入Midjourney[旺柴]"]
            elif e.code == "invalid_api_key":
                self.update_key_self()
                if first:
                    return self.image(messages, first=False)
                return [False, "这个ChatGPT账号的API key不对，快去提醒他看看，生成失败\n请重新输入描述，开始由OpenAI生成图片"]
            elif "billing" in str(e):
                # Error code: 400 - {'error': {'code': 'billing_hard_limit_reached', 'message': 'Billing hard limit has been reached', 'param': None, 'type': 'invalid_request_error'}}
                self.update_key_self()
                if first:
                    return self.image(messages, first=False)
                return [False, "这个ChatGPT账号没钱不能玩了，快去提醒他充值"]
            else:
                return [False, "未知问题，生成失败\n请重新输入描述，开始由OpenAI生成图片"]
        except Exception as e:
            logger.error(e)
            return [False, "未知问题，生成失败\n请重新输入描述，开始由OpenAI生成图片"]
        return [True, image_url]


if __name__ == '__main__':
    a = ChatgptApi()
    # res = a.chat(
    #     [["user", "你好"], ["user", "你好"]]
    # )
    res = a.image(
        "比萨斜塔"
    )
    print(res)
