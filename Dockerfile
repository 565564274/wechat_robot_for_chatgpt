FROM python:3.10.4-slim-buster
MAINTAINER 565564274@qq.com
# update the apt mirror
RUN sed -i s@/archive.ubuntu.com/@/mirrors.aliyun.com/@g /etc/apt/sources.list && apt-get clean
# update apt
RUN apt update
# install the required software
RUN DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends \
                 git-lfs \
                 tzdata
# update pip mirror
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/
# update timezone
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone
RUN rm -f /etc/localtime && dpkg-reconfigure -f noninteractive tzdata
# install python packages
COPY ./requirements.txt /requirements.txt
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
# clean apt packages
RUN rm -rf /var/lib/apt/lists/*

COPY ./ /wechat_robot
# set the environment for python path
# RUN 'export PYTHONPATH=$PYTHONPATH:/IA-Data', replace with docker run -e
ENV PYTHONPATH=$PYTHONPATH:/wechat_robot
WORKDIR /wechat_robot

# 暴露端口
EXPOSE 9981

# 设置代理
#ENV http_proxy=http://127.0.0.1:7890
#ENV https_proxy=http://127.0.0.1:7890

# 启动命令
CMD ["python", "run.py"]

