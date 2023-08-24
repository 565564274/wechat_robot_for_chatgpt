# wechat_robot
- 企业微信客服
- 通过API回调处理并发送对应消息

## 加解密
- [企业微信提供的示例代码](https://github.com/sbzhu/weworkapi_python)
- 需要安装pycrypto`pip install pycryptodemo`
- 使用 https://pypi.tuna.tsinghua.edu.cn/simple/

## docker
```
docker run --net=host -p 9981:9981 -d \
    -v wechat_robot:/wechat_robot/message \
    -v /home/config/resource_setting.yaml:/config/resource_setting.yaml \
    registry.cn-chengdu.aliyuncs.com/ez4leon/qywx:2.1
```
- --net=host 为了网络使用本地代理
- 保证本地/home/config/resource_setting.yaml配置文件存在

