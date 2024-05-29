FROM ubuntu:20.04

ENV TZ="Asia/Shanghai"
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# 设置环境变量 DEBIAN_FRONTEND 为 noninteractive，避免交互式询问
ENV DEBIAN_FRONTEND=noninteractive

# 设置时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo 'Asia/Shanghai' >/etc/timezone
# opencv 相关安装so文件
RUN apt-get update && apt-get install -y build-essential cmake git wget unzip ffmpeg ca-certificates
# 安装 Python 和相关依赖
RUN apt-get install -y python3 python3-pip
RUN apt-get update && apt-get install -y libopencv-dev python3-opencv

# 设置 SSL_CERT_FILE 环境变量
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
# 设置 REQUESTS_CA_BUNDLE 环境变量
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

WORKDIR /workspace


RUN python3 -m pip install -U pip setuptools wheel requests && \
    pip3 install poetry==1.8.2 


COPY poetry.lock pyproject.toml /workspace/
# 使用全局安装，主要为了使用apt安装的opencv，pip安装的opencv不支持avc1的编码
RUN poetry config virtualenvs.create false && \
    python3 -m poetry install --only main
    # rm -rf /root/.cache && \
    # rm -rf /root/.local

# 将poetry安装的site-packages添加到PYTHONPATH
ENV PYTHONPATH=${PYTHONPATH}:/usr/lib/python3.8/site-packages

# 卸载opencv, 使用系统的opencv
RUN pip3 uninstall -y opencv-python

COPY . .

CMD cd aibox-record && sleep 5 && python3 node.py