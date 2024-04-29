FROM node:20-alpine AS node-build
# 前端
WORKDIR /app/aibox-web
COPY aibox-web/yarn.lock aibox-web/package*.json ./
RUN yarn install --frozen-lockfile
COPY aibox-web /app/aibox-web
RUN yarn run build

FROM python:3.8.6

ENV TZ="Asia/Shanghai"
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# 设置时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo 'Asia/Shanghai' >/etc/timezone
# opencv 相关安装so文件
RUN apt-get update && apt-get install -y libgl1 supervisor curl
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash
RUN apt-get install -y nodejs
RUN npm install -g yarn next
RUN mkdir -p /var/log/supervisor

WORKDIR /workspace



RUN python3 -m pip install -U pip setuptools wheel && \
    pip3 install poetry==1.8.2

# 后端
COPY poetry.lock pyproject.toml /workspace/
RUN poetry install --without rt,rknn && \
    rm -rf /root/.local

COPY . .

COPY --from=node-build /app/aibox-web/.next /workspace/aibox-web/.next

CMD ["/usr/bin/supervisord", "-c", "supervisord.conf"]