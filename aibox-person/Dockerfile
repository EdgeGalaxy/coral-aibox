FROM python:3.8.6

ENV TZ="Asia/Shanghai"
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# 设置时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo 'Asia/Shanghai' >/etc/timezone
# opencv 相关安装so文件
RUN apt-get update && apt-get install -y libgl1

WORKDIR /workspace



RUN python3 -m pip install -U pip setuptools wheel && \
    pip3 install poetry==1.8.2


COPY poetry.lock pyproject.toml /workspace/
RUN poetry install --without rt,rknn && \
    rm -rf /root/.local

COPY . .

CMD cd aibox-person && sleep 10 && poetry run python3 node.py