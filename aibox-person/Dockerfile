FROM python:3.8.6

# opencv 相关安装so文件
RUN apt-get update && apt-get install -y libgl1
ENV TZ=Asia/Shanghai

WORKDIR /workspace

RUN pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip3 config set global.timeout 300 && \
    pip3 config set install.trusted-host pypi.tuna.tsinghua.edu.cn

RUN python3 -m pip install -U pip setuptools wheel && \
    pip3 install poetry==1.8.2 && \
    poetry config virtualenvs.create false

COPY poetry.lock pyproject.toml /workspace
RUN poetry install --only main && \
    rm -rf /root/.cache && \
    rm -rf /root/.local
RUN cp aarch64/usr/bin/* /usr/bin && cp aarch64/usr/lib/* /usr/lib && restart_rknn.sh

COPY . .

CMD cd aibox-person && python3 node.py