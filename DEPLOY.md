# 部署指南

本项目提供一键部署脚本，支持将 `websocket-platform` 和 `q_agent` 部署到远程服务器。

## 快速开始

### 1. 配置部署参数

```bash
# 复制配置模板
cp deploy.env.example deploy.env

# 编辑配置文件
vim deploy.env
```

必须配置的参数：
- `SERVER_HOST` - 服务器IP地址
- `MYSQL_PASSWORD` - MySQL密码
- `LLM_API_KEY` - LLM API密钥（如使用OpenAI/Anthropic）

### 2. 配置SSH密钥（推荐）

```bash
# 生成SSH密钥（如果没有）
ssh-keygen -t rsa -b 4096

# 复制公钥到服务器
ssh-copy-id root@your_server_ip

# 测试连接
ssh root@your_server_ip "echo '连接成功'"
```

### 3. 执行部署

```bash
# 完整部署
./deploy.sh deploy

# 或者分步部署
./deploy.sh websocket  # 仅部署 websocket-platform
./deploy.sh qagent     # 仅部署 q_agent
```

## 命令说明

| 命令 | 说明 |
|------|------|
| `deploy` 或 `d` | 执行完整部署（推荐首次使用） |
| `websocket` 或 `w` | 仅部署 websocket-platform |
| `qagent` 或 `q` | 仅部署 q_agent |
| `start` | 启动所有服务 |
| `stop` | 停止所有服务 |
| `restart` 或 `r` | 重启所有服务 |
| `status` 或 `s` | 查看服务状态 |
| `logs [service]` | 查看日志 (websocket/qagent/all) |
| `backup` 或 `b` | 备份当前版本 |
| `rollback` | 回滚到上一版本 |

## 选项

| 选项 | 说明 |
|------|------|
| `--skip-env` | 跳过服务器环境准备（已安装Go/Python时使用） |

## 使用示例

```bash
# 首次部署（会自动安装Go、Python等依赖）
./deploy.sh deploy

# 服务器已有Go和Python，跳过环境准备
./deploy.sh deploy --skip-env

# 仅更新 websocket-platform
./deploy.sh websocket

# 查看服务状态
./deploy.sh status

# 查看 websocket-platform 日志
./deploy.sh logs websocket

# 查看所有服务日志
./deploy.sh logs all

# 回滚到上一版本
./deploy.sh rollback
```

## 部署结构

部署后服务器目录结构：

```
/opt/aipro/
├── websocket-platform/     # WebSocket服务
│   ├── bin/
│   │   └── websocket-platform  # 可执行文件
│   ├── conf/               # 配置文件
│   ├── logs/               # 日志目录
│   └── ...
├── q_agent/                # Q-Agent服务
│   ├── venv/               # Python虚拟环境
│   ├── config.json         # 配置文件
│   ├── logs/               # 日志目录
│   └── ...
├── backup/                 # 备份目录
│   ├── websocket-platform_YYYYMMDD_HHMMSS/
│   └── q_agent_YYYYMMDD_HHMMSS/
└── logs/                   # 公共日志
```

## 服务管理

部署后服务通过 systemd 管理：

```bash
# 在服务器上执行
systemctl status websocket-platform  # 查看状态
systemctl restart websocket-platform # 重启服务
systemctl stop websocket-platform    # 停止服务
journalctl -u websocket-platform -f  # 查看日志

systemctl status q-agent   # 查看状态
systemctl restart q-agent  # 重启服务
```

## 访问地址

部署完成后：

- **WebSocket Platform**: `http://<服务器IP>:8088`
- **Q-Agent API**: `http://<服务器IP>:8089`

WebSocket 连接端点：
- App客户端: `ws://<服务器IP>:8088/ws/app?client_id=xxx&user_id=xxx`
- Agent客户端: `ws://<服务器IP>:8088/ws/agent?client_id=xxx&user_id=xxx`

## 常见问题

### 1. SSH连接失败

```bash
# 检查SSH服务
ssh root@server_ip "echo ok"

# 或使用密码方式（不推荐）
sshpass -p 'password' ssh root@server_ip
```

### 2. Go安装失败

如果Go下载慢，可以手动安装：

```bash
# 在服务器上执行
wget https://go.dev/dl/go1.21.6.linux-amd64.tar.gz
tar -C /usr/local -xzf go1.21.6.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> /etc/profile
source /etc/profile
```

### 3. 端口被占用

```bash
# 查看端口占用
netstat -tlnp | grep -E '8088|8089'

# 修改端口
# websocket-platform: 编辑 conf/dev.yml
# q_agent: 编辑 config.json
```

### 4. 数据库连接失败

确保MySQL服务运行且允许远程连接：

```sql
-- 创建数据库
CREATE DATABASE websocket_platform CHARACTER SET utf8mb4;
CREATE DATABASE q_agent CHARACTER SET utf8mb4;

-- 授权（如需远程连接）
GRANT ALL ON *.* TO 'root'@'%' IDENTIFIED BY 'password';
FLUSH PRIVILEGES;
```

## 安全建议

1. **不要在代码仓库中提交 `deploy.env`**（已加入 .gitignore）
2. 使用SSH密钥认证，避免密码传输
3. 生产环境建议配置防火墙，仅开放必要端口
4. 定期更新API密钥和数据库密码
