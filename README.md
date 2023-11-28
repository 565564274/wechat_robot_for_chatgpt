# wechat_robot
- 企业微信客服
- 通过API回调处理并发送对应消息

## changelog
- 多线程处理用户消息
- 聊天/图片记录自动同步保存本地
- Openai的APIkey自动切换，可在配置文件的api_key_option中加入多个key
- 更新OpenAI版本，使用最新的ChatGPT:gpt-3.5-turbo-1106/DALL-E 3
- 关联公众号判断用户是否关注，关注后才可使用（功能默认关闭，需要的话联系我）
- ...

## 加解密
- [企业微信提供的示例代码](https://github.com/sbzhu/weworkapi_python)
- 需要安装pycrypto`pip install pycryptodemo`
- 使用 https://pypi.tuna.tsinghua.edu.cn/simple/

## docker
```
docker run --net=host -p 9981:9981 -d \
    -v wechat_robot:/wechat_robot/message \
    -v /home/config/wechat_robot/resource_setting.yaml:/wechat_robot/config/resource_setting.yaml \
    -v /home/log/wechat_robot/robot.log:/wechat_robot/robot.log \
    -v /home/log/wechat_robot/media:/wechat_robot/media \
    registry.cn-chengdu.aliyuncs.com/ez4leon/qywx
```
- --net=host 为了网络使用本地代理
- 保证本地/home/config/resource_setting.yaml配置文件存在

- [镜像构建缓慢—从海外下载基础镜像上传至aliyun](https://help.aliyun.com/document_detail/202437.html?spm=5176.smartservice_service_robot_chat_new.0.0.59d3709a3Qh6uB)
