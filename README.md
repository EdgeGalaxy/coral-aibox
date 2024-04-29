
# AIBox Coral版本

## 本地启动(后端)

### 安装

1. 安装包管理工具`poetry`

```shell
pip3 install poetry
```

2. 安装依赖并激活虚拟环境

- 通用模块安装: `aibox-camera`、`aibox-record`、`aibox-report`
```shell
# 进入对应的模块
cd aibox-<module>
poetry shell
poetry install --only main
```

- 推理模块安装: `aibox-person`、`aibox-face`
> 减少包的安装数量

```shell
# 进入对应的模块
cd aibox-<module>
poetry shell
poetry install --without rt,rknn
```

### 配置更改

> `aibox-camera`默认读取 `0` 号摄像头节点，正常Mac本地运行无需更改任何配置

> 若需要更改摄像头配置，可在`aibox-camera`的`config.json`文件中更改

**注：配置文件`config.json`中除`params`字段外其他均为框架内置定义字段，详见：[coral文档](https://zhaokefei.github.io)**


### 模型文件
> - 模型文件会优先在`$HOME/.cora/aibox/weights`目录下检查，不存在则从远端下载，默认本地下载`onnx`模型
> - 通过环境变量`MODEL_TYPE`和`CORAL_NODE_CONFIG_PATH`来选择不同的模型下载

### 运行代码

```shell
# 在各自的虚拟环境中运行, 进入到程序所在目录
cd aibox-<module>
python3 node.py
```

## 本地启动（前端）
> 本地访问: `http://127.0.0.1:3000`

```shell
cd aibox-web
yarn install
yarn run dev
```


## Docker Compose运行(有网环境，需要本地构建镜像)

### 本地
> 本地若为mac电脑，则无法在容器中根据 camera的`0`编号读到视频流，需要手动改`aibox-camera`的`config.json`文件

```
docker compose -f docker-compose-local.yml up -d --build
```


### 盒子上运行

> - 盒子上运行的yml文件中指定了配置文件具体路径，若启动时未设置配置文件，则会将默认的配置文件复制到指定的具体路径中
> - 默认配置文件地址: `$HOME/.coral/aibox/configs/`
> - 默认模型文件地址: `$HOME/.coral/aibox/weights/`
> - 默认前端访问地址: `http://<内网ip>:3000`

### Rknn盒子

```
docker compose -f docker-compose-rknn.yml up -d --build
```

### Jetson盒子
```
docker compose -f docker-compose-rt.yml up -d --build
```


## Docker Compose运行（无网环境，无需本地构建镜像）

- TODO


## 错误记录

- 需要安装 `apt-get install python3-dev`，否则 `sharedarray`包报错