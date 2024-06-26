#!/bin/bash

# 打印使用方法
usage() {
    echo "Usage: $0 --mqtt MQTT_URL [--docker-mirror DOCKER_MIRROR]"
    exit 1
}

# 初始化参数
MQTT_URL=""
DOCKER_MIRROR=""

# 打印错误信息并退出
error_exit() {
    echo "Error: $1"
    exit 1
}

# 解析传入的参数
parse_arguments() {
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            --mqtt) MQTT_URL="$2"; shift ;;
            --docker-mirror) DOCKER_MIRROR="$2"; shift ;;
            *) echo "未知参数: $1"; usage ;;
        esac
        shift
    done

    if [ -z "$MQTT_URL" ]; then
        error_exit "缺少必填参数: --mqtt."
    fi

    if ! [[ "$MQTT_URL" =~ mqtt://([^:]+):([^@]+)@([^:]+):(.+) ]]; then
        error_exit "错误的MQTT URL, 形如: mqtt://username:password@host:port"
    fi

    MQTT_USERNAME="${BASH_REMATCH[1]}"
    MQTT_PASSWORD="${BASH_REMATCH[2]}"
    MQTT_BROKER="${BASH_REMATCH[3]}"
    MQTT_PORT="${BASH_REMATCH[4]}"
}

check_system() {
    if [[ "$(uname)" != "Linux" ]]; then
        error_exit "仅支持Linux系统."
    fi
}

# 设置环境变量
set_env_vars() {
    export MQTT_USERNAME
    export MQTT_PASSWORD
    export MQTT_BROKER
    export MQTT_PORT
    export DOCKER_MIRROR

    echo "MQTT User: $MQTT_USERNAME"
    echo "MQTT Password: $MQTT_PASSWORD"
    echo "MQTT IP: $MQTT_BROKER"
    echo "MQTT Port: $MQTT_PORT"
    echo "Docker Mirror: ${DOCKER_MIRROR:-not provided}"
}

# 检查必备工具
check_requirements() {
    command -v docker &> /dev/null || error_exit "docker 未安装."
    command -v docker compose &> /dev/null || error_exit "docker compose 未安装."
    command -v rock &> /dev/null || error_exit "rock 未安装."
}

# 下载配置文件
download_configs() {
    mkdir -p aibox-deploy
    wget -qO aibox-deploy/aibox-nginx.conf https://nbstore.oss-cn-shanghai.aliyuncs.com/coral-aibox/deploy/config/aibox-nginx.conf
}

# 检测设备型号并下载对应的docker-compose文件
detect_device_and_download_compose() {
    local MODEL=$(cat /proc/device-tree/model)

    case "$MODEL" in 
        *"NEARDI"*)
            echo "检测到NEARDI设备"
            wget -qO aibox-deploy/docker-compose.yml https://nbstore.oss-cn-shanghai.aliyuncs.com/coral-aibox/deploy/config/docker-compose-rknn.yml
            ;;
        *"Jetson"*)
            echo "检测到Jetson设备"
            wget -qO aibox-deploy/docker-compose.yml https://nbstore.oss-cn-shanghai.aliyuncs.com/coral-aibox/deploy/config/docker-compose-rt.yml
            ;;
        *)
            error_exit "未检测到已知设备型号"
            ;;
    esac
}

# 主程序执行流程
main() {
    check_system
    parse_arguments "$@"
    set_env_vars
    check_requirements
    download_configs
    detect_device_and_download_compose

    # 进入文件夹运行docker compose命令
    cd aibox-deploy
    docker-compose up -d

    echo "操作完成."
}

# 执行主程序
main "$@"