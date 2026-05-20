# 部署指南

本项目提供一键部署脚本，支持将 `websocket-platform` 和 `q_agent` 部署到远程服务器。

## 使用示例

```bash
# 首次部署（会自动安装Go、Python等依赖）
./deploy.sh deploy

# 服务器已有Go和Python，跳过环境准备
./deploy.sh deploy --skip-env

# 验证配置是否正确
./deploy.sh validate

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

## 目录结构

```
deploy/
├── deploy.sh      # 一键部署主脚本
├── deploy.env     # 部署配置文件
└── DEPLOY.md      # 本文档
```

## 部署架构

```
┌─────────────────────────────────────────────────────────┐
│                    远程服务器                             │
├─────────────────────────────────────────────────────────┤
│  /home/ai_agent/                                        │
│  ├── websocket-platform/    ← Go WebSocket服务 (:8088)  │
│  │   ├── bin/websocket-platform                        │
│  │   └── logs/                                         │
│  ├── q_agent/               ← Python Agent服务 (:8089)  │
│  │   ├── venv/              ← Python虚拟环境            │
│  │   ├── config.json        ← 自动生成配置              │
│  │   └── logs/                                         │
│  └── backup/                ← 版本备份                   │
└─────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 配置部署参数

```bash
cd deploy

# 编辑配置文件
vim deploy.env
```

必须配置的参数：
- `SERVER_HOST` - 服务器IP地址
- 数据库和LLM配置请直接修改项目根目录的 `config.json`

### 2. 配置SSH密钥（推荐）

```bash
# 生成SSH密钥（如果没有）
ssh-keygen -t rsa -b 4096

# 复制公钥到服务器
ssh-copy-id root@your_server_ip

# 测试连接
ssh root@your_server_ip "echo '连接成功'"
```

### 3. 验证配置（推荐）

```bash
# 验证配置和项目结构
./deploy.sh validate
```

输出示例：
```
✅ 配置验证通过

项目结构:
  - websocket-platform: /path/to/q_agent/websocket-platform
  - q_agent:            /path/to/q_agent/q_agent

部署目标:
  - 服务器: root@49.233.105.26:22
  - 目录:   /home/ai_agent

应用配置:
  - 数据库和LLM配置请检查: config.json
```

### 4. 执行部署

```bash
# 完整部署
./deploy.sh deploy

# 或者分步部署
./deploy.sh websocket  # 仅部署 websocket-platform
./deploy.sh qagent     # 仅部署 q_agent
```

## 命令说明

| 命令 | 简写 | 说明 |
|------|------|------|
| `deploy` | `d` | 执行完整部署（推荐首次使用） |
| `websocket` | `w` | 仅部署 websocket-platform |
| `qagent` | `q` | 仅部署 q_agent |
| `validate` | `v` | 验证配置和项目结构 |
| `start` | - | 启动所有服务 |
| `stop` | - | 停止所有服务 |
| `restart` | `r` | 重启所有服务 |
| `status` | `s` | 查看服务状态 |
| `logs [service]` | `l` | 查看日志 (websocket/qagent/all) |
| `backup` | `b` | 备份当前版本 |
| `rollback` | - | 回滚到上一版本 |
| `help` | `h` | 显示帮助信息 |

## 选项

| 选项 | 说明 |
|------|------|
| `--skip-env` | 跳过服务器环境准备（已安装Go/Python时使用） |
| `--dry-run` | 仅显示将要执行的操作，不实际执行（待实现） |

## 部署流程详解

执行 `./deploy.sh deploy` 时，脚本会按以下顺序执行：

```
1. 预检查
   ├── 检查本地 ssh/rsync 命令
   └── 测试 SSH 连接

2. 环境准备 (--skip-env 跳过)
   ├── 更新系统包
   ├── 安装 Go 1.21.6
   ├── 安装 Python 3
   └── 创建部署目录

3. 备份
   ├── 备份 websocket-platform/
   └── 备份 q_agent/

4. 部署 websocket-platform
   ├── rsync 同步代码
   ├── go mod download
   ├── go build
   └── 创建 systemd 服务

5. 部署 q_agent
   ├── rsync 同步代码（包含 config.json）
   ├── 创建 Python venv
   ├── pip install -e .（通过 pyproject.toml 安装依赖）
   └── 创建 systemd 服务

6. 启动服务
   └── systemctl start
```

## 使用示例

```bash
# 首次部署（会自动安装Go、Python等依赖）
./deploy.sh deploy

# 服务器已有Go和Python，跳过环境准备
./deploy.sh deploy --skip-env

# 验证配置是否正确
./deploy.sh validate

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

### 5. 脚本路径错误

确保脚本位于正确的位置：
```
<project-root>/
├── deploy/
│   ├── deploy.sh      ← 脚本位置
│   └── deploy.env
├── websocket-platform/
└── q_agent/
```

## 安全建议

1. **不要在代码仓库中提交 `deploy.env`**（已加入 .gitignore）
2. 使用SSH密钥认证，避免密码传输
3. 生产环境建议配置防火墙，仅开放必要端口
4. 定期更新API密钥和数据库密码
