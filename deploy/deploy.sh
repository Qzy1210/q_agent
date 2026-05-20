#!/bin/bash

#############################################
# 一键部署脚本 v3 - websocket-platform & q_agent
# 支持 Ubuntu/Debian 系统，使用 systemd 管理服务
# 支持从配置文件读取配置
#############################################

set -e

# 获取脚本所在目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ==================== 默认配置 ====================
SERVER_HOST="49.233.105.26"
SERVER_USER="root"
SERVER_PORT="22"
DEPLOY_BASE="/home/ai_agent"
WEBSOCKET_PORT=8088
QAGENT_PORT=8089
GO_VERSION="1.21.6"
DEPLOY_ENV="test"  # 部署环境: test, prod

# ==================== 加载配置文件 ====================
load_config() {
    local config_file="${SCRIPT_DIR}/deploy.env"

    if [ -f "$config_file" ]; then
        echo -e "${BLUE}[INFO]${NC} 加载配置文件: $config_file"
        # 读取配置文件，忽略注释和空行
        while IFS= read -r line || [ -n "$line" ]; do
            # 跳过注释和空行
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            [[ -z "${line// }" ]] && continue

            # 解析 KEY=VALUE 格式
            if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
                local key="${BASH_REMATCH[1]}"
                local value="${BASH_REMATCH[2]}"
                # 移除可能的引号
                value="${value#\"}"
                value="${value%\"}"
                value="${value#\'}"
                value="${value%\'}"
                # 导出变量
                export "$key"="$value"
            fi
        done < "$config_file"
    else
        echo -e "${YELLOW}[WARNING]${NC} 未找到配置文件 deploy.env"
        echo -e "${YELLOW}[WARNING]${NC} 请复制 deploy.env.example 为 deploy.env 并填写配置"
    fi
}

# ==================== 颜色定义 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ==================== 工具函数 ====================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 未安装，请先安装"
        exit 1
    fi
}

# SSH到服务器执行命令
ssh_exec() {
    ssh -o StrictHostKeyChecking=no -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_HOST} "$1"
}

# SSH到服务器执行命令（强制分配终端，用于 journalctl -f 等）
ssh_exec_tty() {
    ssh -tt -o StrictHostKeyChecking=no -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_HOST} "$1"
}

# 同步文件到服务器
rsync_to_server() {
    local src=$1
    local dst=$2
    rsync -avz --delete --exclude '.git' --exclude '.idea' --exclude '__pycache__' --exclude 'venv' --exclude '*.log' --exclude 'logs/*' --progress -e "ssh -o StrictHostKeyChecking=no -p ${SERVER_PORT}" ${src} ${SERVER_USER}@${SERVER_HOST}:${dst}
}

# ==================== 验证配置 ====================

validate_config() {
    local missing=()

    [ -z "$SERVER_HOST" ] && missing+=("SERVER_HOST")

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "以下配置项未设置:"
        for item in "${missing[@]}"; do
            echo "  - $item"
        done
        echo ""
        echo "请编辑 deploy.env 文件或设置环境变量"
        exit 1
    fi

    # 验证项目目录结构
    if [ ! -d "${PROJECT_ROOT}/websocket-platform" ]; then
        log_error "未找到 websocket-platform 目录: ${PROJECT_ROOT}/websocket-platform"
        log_error "请确保脚本位于正确的位置: <project>/deploy/deploy.sh"
        exit 1
    fi

    if [ ! -d "${PROJECT_ROOT}/q_agent" ]; then
        log_error "未找到 q_agent 目录: ${PROJECT_ROOT}/q_agent"
        log_error "请确保脚本位于正确的位置: <project>/deploy/deploy.sh"
        exit 1
    fi

    # 设置部署目录
    WEBSOCKET_DIR="${DEPLOY_BASE}/websocket-platform"
    QAGENT_DIR="${DEPLOY_BASE}/q_agent"

    log_info "项目根目录: ${PROJECT_ROOT}"
    log_info "部署目标: ${DEPLOY_BASE}"
}

# ==================== 预检查 ====================

pre_check() {
    log_info "正在执行预检查..."

    # 检查本地命令
    check_command ssh
    check_command rsync

    # 检查SSH连接
    log_info "检查SSH连接到 ${SERVER_USER}@${SERVER_HOST}..."
    if ! ssh_exec "echo 'SSH连接成功'" &> /dev/null; then
        log_error "无法连接到服务器 ${SERVER_USER}@${SERVER_HOST}"
        log_error "请确保:"
        echo "  1. 服务器地址正确"
        echo "  2. SSH密钥已配置 (推荐) 或使用 ssh-add 添加密钥"
        echo "  3. 服务器SSH服务正常运行"
        exit 1
    fi

    log_success "预检查通过"
}

# ==================== 环境准备 ====================

prepare_server() {
    log_info "正在准备服务器环境..."

    ssh_exec << ENDSSH
set -e

echo ">>> 更新系统包..."
apt-get update -y

echo ">>> 安装基础工具..."
apt-get install -y curl wget git build-essential net-tools

echo ">>> 检查Go环境..."
if ! command -v go &> /dev/null; then
    echo "正在安装Go ${GO_VERSION}..."
    wget -q https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz
    rm -rf /usr/local/go
    tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz
    rm go${GO_VERSION}.linux-amd64.tar.gz

    # 配置环境变量
    grep -q '/usr/local/go/bin' /etc/profile || {
        echo 'export PATH=\$PATH:/usr/local/go/bin' >> /etc/profile
        echo 'export GOPATH=/root/go' >> /etc/profile
        echo 'export PATH=\$PATH:\$GOPATH/bin' >> /etc/profile
    }
fi

echo ">>> 验证Go版本..."
export PATH=\$PATH:/usr/local/go/bin
go version

echo ">>> 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "正在安装Python 3..."
    apt-get install -y python3 python3-pip python3-venv
fi
python3 --version

echo ">>> 创建部署目录..."
mkdir -p ${DEPLOY_BASE}/websocket-platform
mkdir -p ${DEPLOY_BASE}/q_agent
mkdir -p ${DEPLOY_BASE}/logs
mkdir -p ${DEPLOY_BASE}/backup

echo ">>> 环境准备完成"
ENDSSH

    log_success "服务器环境准备完成"
}

# ==================== 备份 ====================

backup() {
    log_info "正在备份当前版本..."

    local timestamp=$(date +%Y%m%d_%H%M%S)

    ssh_exec << ENDSSH
set -e

timestamp="${timestamp}"

# 备份 websocket-platform
if [ -d "${WEBSOCKET_DIR}" ] && [ "\$(ls -A ${WEBSOCKET_DIR} 2>/dev/null)" ]; then
    echo ">>> 备份 websocket-platform..."
    mkdir -p ${DEPLOY_BASE}/backup
    rm -rf ${DEPLOY_BASE}/backup/websocket-platform
    cp -r ${WEBSOCKET_DIR} ${DEPLOY_BASE}/backup/websocket-platform_\${timestamp}
    ln -sfn ${DEPLOY_BASE}/backup/websocket-platform_\${timestamp} ${DEPLOY_BASE}/backup/websocket-platform
fi

# 备份 q_agent
if [ -d "${QAGENT_DIR}" ] && [ "\$(ls -A ${QAGENT_DIR} 2>/dev/null)" ]; then
    echo ">>> 备份 q_agent..."
    rm -rf ${DEPLOY_BASE}/backup/q_agent
    cp -r ${QAGENT_DIR} ${DEPLOY_BASE}/backup/q_agent_\${timestamp}
    ln -sfn ${DEPLOY_BASE}/backup/q_agent_\${timestamp} ${DEPLOY_BASE}/backup/q_agent
fi

echo ">>> 备份完成"
ENDSSH

    log_success "备份完成"
}

# ==================== 部署 websocket-platform ====================

deploy_websocket() {
    log_info "正在部署 websocket-platform..."

    # 同步代码（从项目根目录的 websocket-platform 子目录）
    log_info "同步代码到服务器..."
    rsync_to_server "${PROJECT_ROOT}/websocket-platform/" "${WEBSOCKET_DIR}/"

    # 构建并安装服务
    ssh_exec << ENDSSH
set -e
export PATH=\$PATH:/usr/local/go/bin

cd ${WEBSOCKET_DIR}

echo ">>> 下载Go依赖..."
go mod download
go mod tidy

echo ">>> 构建项目..."
mkdir -p bin logs
go build -o bin/websocket-platform cmd/server/main.go

echo ">>> 创建systemd服务..."
cat > /etc/systemd/system/websocket-platform.service << 'SERVICE'
[Unit]
Description=WebSocket Platform Service
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=root
WorkingDirectory=${WEBSOCKET_DIR}
ExecStart=${WEBSOCKET_DIR}/bin/websocket-platform
Restart=always
RestartSec=5
StandardOutput=append:${WEBSOCKET_DIR}/logs/service.log
StandardError=append:${WEBSOCKET_DIR}/logs/error.log

# 资源限制
LimitNOFILE=65535
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable websocket-platform

echo ">>> websocket-platform 部署完成"
ENDSSH

    log_success "websocket-platform 部署完成"
}

# ==================== 部署 q_agent ====================

deploy_qagent() {
    log_info "正在部署 q_agent..."

    # 同步代码 - 同步项目根目录，保持 q_agent 包结构
    log_info "同步代码到服务器..."
    # 排除 websocket-platform 和其他不需要的文件
    rsync -avz --delete \
        --exclude '.git' \
        --exclude '.idea' \
        --exclude '__pycache__' \
        --exclude 'venv' \
        --exclude '*.log' \
        --exclude 'logs/*' \
        --exclude 'websocket-platform' \
        --exclude 'android-app' \
        --exclude '.claude' \
        --exclude 'deploy' \
        --exclude '*.md' \
        --progress \
        -e "ssh -o StrictHostKeyChecking=no -p ${SERVER_PORT}" \
        "${PROJECT_ROOT}/" \
        "${SERVER_USER}@${SERVER_HOST}:${QAGENT_DIR}/"

    # 安装依赖并配置服务
    ssh_exec << ENDSSH
set -e

cd ${QAGENT_DIR}

echo ">>> 创建Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

echo ">>> 安装依赖包（使用 pyproject.toml）..."
pip install --upgrade pip -q
pip install -e . -q

echo ">>> 配置 config.json (环境: ${DEPLOY_ENV})..."
if [ -f "config.${DEPLOY_ENV}.json" ]; then
    cp "config.${DEPLOY_ENV}.json" config.json
    echo "已使用 config.${DEPLOY_ENV}.json"
elif [ -f "config.json" ]; then
    echo "[WARNING] 未找到 config.${DEPLOY_ENV}.json，使用默认 config.json"
else
    echo "[ERROR] 未找到 config.json 或 config.${DEPLOY_ENV}.json"
fi

echo ">>> 创建日志目录..."
mkdir -p logs

echo ">>> 创建systemd服务..."
cat > /etc/systemd/system/q-agent.service << 'SERVICE'
[Unit]
Description=Q-Agent WebSocket Client Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${QAGENT_DIR}
Environment="PYTHONPATH=${QAGENT_DIR}"
ExecStart=${QAGENT_DIR}/venv/bin/python ${QAGENT_DIR}/q_agent/agents/agent_websocket.py
Restart=always
RestartSec=5
StandardOutput=append:${QAGENT_DIR}/logs/service.log
StandardError=append:${QAGENT_DIR}/logs/error.log

# 资源限制
LimitNOFILE=65535
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable q-agent

echo ">>> q_agent 部署完成"
ENDSSH

    log_success "q_agent 部署完成"
}

# ==================== 服务管理 ====================

start_services() {
    log_info "正在启动服务..."

    local services=${1:-"websocket-platform q-agent"}

    ssh_exec << ENDSSH
set -e

echo ">>> 启动服务..."
for svc in ${services}; do
    echo "启动 \$svc..."
    systemctl restart \$svc
done

sleep 2

echo ""
echo ">>> 服务状态:"
for svc in ${services}; do
    if systemctl is-active --quiet \$svc; then
        echo "  ✓ \$svc: 运行中"
    else
        echo "  ✗ \$svc: 未运行"
        systemctl status \$svc --no-pager -l | head -20
    fi
done
ENDSSH

    log_success "服务启动完成"
}

stop_services() {
    log_info "正在停止服务..."
    ssh_exec "systemctl stop websocket-platform q-agent 2>/dev/null || true"
    log_success "服务已停止"
}

restart_services() {
    log_info "正在重启服务..."
    stop_services
    sleep 1
    start_services
}

# ==================== 状态查看 ====================

show_status() {
    log_info "服务状态:"
    echo ""
    ssh_exec << 'ENDSSH'
echo "======================================"
echo "websocket-platform 状态:"
echo "--------------------------------------"
systemctl status websocket-platform --no-pager -l 2>/dev/null | head -15 || echo "服务未安装"
echo ""
echo "======================================"
echo "q-agent 状态:"
echo "--------------------------------------"
systemctl status q-agent --no-pager -l 2>/dev/null | head -15 || echo "服务未安装"
echo "======================================"

echo ""
echo "端口监听:"
echo "--------------------------------------"
ss -tlnp 2>/dev/null | grep -E '8088|8089' || netstat -tlnp 2>/dev/null | grep -E '8088|8089' || echo "未找到监听端口"

echo ""
echo "访问地址:"
IP=$(hostname -I | awk '{print $1}')
echo "  WebSocket Platform: http://${IP}:8088"
echo "  Q-Agent API:        http://${IP}:8089"
ENDSSH
}

# ==================== 日志查看 ====================

show_logs() {
    local service=$1
    local lines=${2:-100}

    case $service in
        websocket|websocket-platform|w)
            ssh_exec_tty "journalctl -u websocket-platform -f --no-pager -n ${lines}"
            ;;
        qagent|q-agent|q)
            ssh_exec_tty "journalctl -u q-agent -f --no-pager -n ${lines}"
            ;;
        all|*)
            ssh_exec_tty "journalctl -u websocket-platform -u q-agent -f --no-pager -n ${lines}"
            ;;
    esac
}

# ==================== 回滚 ====================

rollback() {
    log_warning "正在回滚到上一版本..."

    ssh_exec << ENDSSH
set -e

echo ">>> 停止服务..."
systemctl stop websocket-platform q-agent 2>/dev/null || true

echo ">>> 检查备份..."
if [ -L "${DEPLOY_BASE}/backup/websocket-platform" ]; then
    backup_dir=\$(readlink -f ${DEPLOY_BASE}/backup/websocket-platform)
    echo "找到备份: \$backup_dir"

    echo ">>> 恢复 websocket-platform..."
    rm -rf ${WEBSOCKET_DIR}
    cp -r "\$backup_dir" ${WEBSOCKET_DIR}
    echo "websocket-platform 已回滚"
else
    echo "未找到 websocket-platform 备份"
fi

if [ -L "${DEPLOY_BASE}/backup/q_agent" ]; then
    backup_dir=\$(readlink -f ${DEPLOY_BASE}/backup/q_agent)
    echo "找到备份: \$backup_dir"

    echo ">>> 恢复 q_agent..."
    rm -rf ${QAGENT_DIR}
    cp -r "\$backup_dir" ${QAGENT_DIR}
    echo "q_agent 已回滚"
else
    echo "未找到 q_agent 备份"
fi

echo ">>> 重启服务..."
systemctl start websocket-platform q-agent 2>/dev/null || true

echo ">>> 回滚完成"
ENDSSH

    log_success "回滚完成"
    show_status
}

# ==================== 完整部署 ====================

full_deploy() {
    local skip_env=${1:-false}

    log_info "========================================"
    log_info "开始完整部署"
    log_info "========================================"
    echo ""

    pre_check
    echo ""

    if [ "$skip_env" != "true" ]; then
        prepare_server
        echo ""
    else
        log_info "跳过环境准备"
        echo ""
    fi

    backup
    echo ""

    deploy_websocket
    echo ""

    deploy_qagent
    echo ""

    start_services
    echo ""

    log_success "========================================"
    log_success "部署完成"
    log_success "========================================"
    show_status
}

# ==================== 帮助信息 ====================

show_help() {
    echo "
${GREEN}一键部署脚本 v3 - websocket-platform & q_agent${NC}

${YELLOW}脚本位置:${NC}
  当前脚本位于 deploy/ 子目录，会自动检测项目根目录

${YELLOW}用法:${NC}
  $0 [命令] [选项]

${YELLOW}命令:${NC}
  ${GREEN}deploy, d${NC}       执行完整部署（推荐首次使用）
  ${GREEN}websocket, w${NC}     仅部署 websocket-platform
  ${GREEN}qagent, q${NC}        仅部署 q_agent
  ${GREEN}start${NC}            启动所有服务
  ${GREEN}stop${NC}             停止所有服务
  ${GREEN}restart, r${NC}       重启所有服务
  ${GREEN}status, s${NC}        查看服务状态
  ${GREEN}logs [service]${NC}   查看日志 (websocket/qagent/all)
  ${GREEN}backup${NC}           备份当前版本
  ${GREEN}rollback${NC}         回滚到上一版本
  ${GREEN}validate${NC}         验证配置和项目结构
  ${GREEN}help, h${NC}          显示帮助信息

${YELLOW}选项:${NC}
  --skip-env      跳过服务器环境准备（已安装Go/Python时使用）
  --env <name>    指定部署环境 (test/prod)，默认 test
  --dry-run       仅显示将要执行的操作，不实际执行

${YELLOW}配置:${NC}
  配置文件: deploy/deploy.env
  应用配置: config.{env}.json (如 config.test.json)
  ${BLUE}vim deploy/deploy.env${NC}

${YELLOW}示例:${NC}
  $0 validate                  # 验证配置是否正确
  $0 deploy                    # 使用 test 环境部署
  $0 deploy --env prod         # 使用 prod 环境部署
  $0 deploy --skip-env         # 跳过环境检查直接部署
  $0 websocket                 # 仅部署 websocket-platform
  $0 logs websocket            # 查看 websocket-platform 日志
  $0 status                    # 查看服务状态
  $0 rollback                  # 回滚到上一版本

${YELLOW}首次使用:${NC}
  1. 编辑配置文件:
     ${BLUE}vim deploy/deploy.env${NC}

  2. 确保SSH密钥已配置 (推荐):
     ${BLUE}ssh-copy-id user@server${NC}

  3. 验证配置:
     ${BLUE}$0 validate${NC}

  4. 执行部署:
     ${BLUE}$0 deploy${NC}
"
}

# ==================== 主函数 ====================

main() {
    local command=${1:-help}
    shift 2>/dev/null || true

    # 解析选项
    local skip_env=false
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-env)
                skip_env=true
                shift
                ;;
            --env)
                DEPLOY_ENV="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    # 加载配置
    load_config

    case $command in
        deploy|d)
            validate_config
            full_deploy $skip_env
            ;;
        websocket|w)
            validate_config
            pre_check
            backup
            deploy_websocket
            start_services "websocket-platform"
            ;;
        qagent|q)
            validate_config
            pre_check
            backup
            deploy_qagent
            start_services "q-agent"
            ;;
        validate|v)
            validate_config
            log_success "配置验证通过"
            echo ""
            echo "项目结构:"
            echo "  - websocket-platform: ${PROJECT_ROOT}/websocket-platform"
            echo "  - q_agent:            ${PROJECT_ROOT}/q_agent"
            echo ""
            echo "部署目标:"
            echo "  - 服务器: ${SERVER_USER}@${SERVER_HOST}:${SERVER_PORT}"
            echo "  - 目录:   ${DEPLOY_BASE}"
            echo "  - 环境:   ${DEPLOY_ENV}"
            echo ""
            echo "应用配置:"
            echo "  - 配置文件: config.${DEPLOY_ENV}.json → config.json"
            ;;
        start)
            validate_config
            start_services
            ;;
        stop)
            validate_config
            stop_services
            ;;
        restart|r)
            validate_config
            restart_services
            ;;
        status|s)
            validate_config
            show_status
            ;;
        logs|l)
            validate_config
            show_logs ${1:-all} ${2:-100}
            ;;
        backup|b)
            validate_config
            backup
            ;;
        rollback)
            validate_config
            rollback
            ;;
        help|h|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
