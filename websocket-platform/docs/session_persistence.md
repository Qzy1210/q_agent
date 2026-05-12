# 会话持久化文档

## 概述

WebSocket平台已实现完整的会话持久化到MySQL功能，支持会话管理、客户端连接跟踪和消息历史记录。

## 数据库表结构

### 1. sessions 表 - 会话信息

```sql
CREATE TABLE `sessions` (
  `id` varchar(64) NOT NULL COMMENT '会话ID',
  `user_id` varchar(64) NOT NULL COMMENT '用户ID',
  `status` varchar(20) DEFAULT 'active' COMMENT '会话状态(active/inactive/closed)',
  `created_at` datetime(3) DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime(3) DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_sessions_user_id` (`user_id`),
  KEY `idx_sessions_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话表';
```

**字段说明：**
- `id`: 会话唯一标识
- `user_id`: 用户ID，支持多用户
- `status`: 会话状态（active/inactive/closed）
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 2. session_clients 表 - 客户端连接

```sql
CREATE TABLE `session_clients` (
  `id` varchar(64) NOT NULL COMMENT '记录ID',
  `session_id` varchar(64) NOT NULL COMMENT '会话ID',
  `client_id` varchar(64) NOT NULL COMMENT '客户端ID',
  `client_type` varchar(20) NOT NULL COMMENT '客户端类型(app/agent)',
  `user_id` varchar(64) NOT NULL COMMENT '用户ID',
  `status` varchar(20) DEFAULT 'online' COMMENT '连接状态(online/offline)',
  `connected_at` datetime(3) DEFAULT NULL COMMENT '连接时间',
  `disconnected_at` datetime(3) DEFAULT NULL COMMENT '断开时间',
  PRIMARY KEY (`id`),
  KEY `idx_session_clients_session_id` (`session_id`),
  KEY `idx_session_clients_client_id` (`client_id`),
  KEY `idx_session_clients_user_id` (`user_id`),
  KEY `idx_session_clients_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话客户端关联表';
```

**字段说明：**
- `session_id`: 关联的会话ID
- `client_id`: 客户端唯一标识
- `client_type`: 客户端类型（app/agent）
- `user_id`: 用户ID
- `status`: 连接状态（online/offline）
- `connected_at`: 连接时间
- `disconnected_at`: 断开时间

### 3. messages 表 - 消息记录

```sql
CREATE TABLE `messages` (
  `id` varchar(64) NOT NULL COMMENT '消息ID',
  `session_id` varchar(64) NOT NULL COMMENT '会话ID',
  `type` varchar(20) NOT NULL COMMENT '消息类型',
  `from` varchar(64) NOT NULL COMMENT '发送者ID',
  `to` varchar(64) DEFAULT NULL COMMENT '接收者ID',
  `content` text COMMENT '消息内容(JSON)',
  `timestamp` bigint NOT NULL COMMENT '时间戳',
  `created_at` datetime(3) DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_messages_session_id` (`session_id`),
  KEY `idx_messages_from` (`from`),
  KEY `idx_messages_timestamp` (`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息记录表';
```

**字段说明：**
- `session_id`: 关联的会话ID
- `type`: 消息类型（text/file/tool_call/tool_result等）
- `from`: 发送者客户端ID
- `to`: 接收者客户端ID（可选）
- `content`: 消息内容（JSON格式）
- `timestamp`: 消息时间戳

## 核心功能

### 1. 会话管理

```go
// 创建会话
err := sessionManager.CreateSession("session1", "user1")

// 获取会话
session, err := sessionManager.GetSession("session1")

// 更新会话状态
err := sessionManager.UpdateSessionStatus("session1", "closed")

// 删除会话（软删除）
err := sessionManager.DeleteSession("session1")

// 获取用户所有会话
sessions, err := sessionManager.GetUserSessions("user1")
```

### 2. 客户端管理

```go
// 注册客户端到会话
err := sessionManager.RegisterClient("session1", "app1", "app", "user1")

// 注销客户端
err := sessionManager.UnregisterClient("app1")

// 获取会话的所有在线客户端
clients, err := sessionManager.GetSessionClients("session1")
```

### 3. 消息管理

```go
// 保存消息
err := sessionManager.SaveMessage(
    "msg1",           // 消息ID
    "session1",       // 会话ID
    "text",           // 消息类型
    "app1",           // 发送者
    "agent1",         // 接收者
    `{"text":"Hello"}`, // 消息内容
    1234567890,       // 时间戳
)

// 获取会话消息历史
messages, err := sessionManager.GetSessionMessages("session1", 10, 0)
```

## 使用方式

### 1. 自动迁移（推荐）

应用启动时会自动创建表结构：

```go
sessionManager := logic.NewSessionManager()
err := sessionManager.InitTables()
```

### 2. 手动执行SQL

也可以手动执行迁移SQL：

```bash
mysql -u root -p websocket_platform < docs/migrations/001_init_session_tables.sql
```

## 数据查询示例

### 查询用户活跃会话

```sql
SELECT * FROM sessions 
WHERE user_id = 'user1' AND status = 'active' 
ORDER BY updated_at DESC;
```

### 查询会话在线客户端

```sql
SELECT * FROM session_clients 
WHERE session_id = 'session1' AND status = 'online';
```

### 查询会话消息历史

```sql
SELECT * FROM messages 
WHERE session_id = 'session1' 
ORDER BY timestamp DESC 
LIMIT 100;
```

### 统计用户消息数量

```sql
SELECT session_id, COUNT(*) as message_count 
FROM messages 
WHERE session_id IN (
  SELECT id FROM sessions WHERE user_id = 'user1'
)
GROUP BY session_id;
```

## 性能优化建议

1. **索引优化**
   - 所有查询字段已建立索引
   - 复合查询考虑添加复合索引

2. **分区表**
   - 消息表按时间分区，提升查询性能
   - 历史消息归档到冷存储

3. **缓存策略**
   - 活跃会话缓存到Redis
   - 客户端连接状态缓存
   - 消息历史分页缓存

4. **数据清理**
   - 定期清理过期会话
   - 归档历史消息
   - 优化表空间

## 监控指标

建议监控以下指标：

- 会话总数
- 活跃会话数
- 在线客户端数
- 消息发送速率
- 数据库查询延迟
- 表空间使用率

## 备份策略

1. **全量备份**
   - 每天凌晨全量备份
   - 保留最近7天备份

2. **增量备份**
   - 每小时增量备份binlog
   - 实时同步到从库

3. **数据恢复**
   - 支持指定时间点恢复
   - 支持单表恢复

## 注意事项

1. **数据一致性**
   - 使用事务保证关联数据一致性
   - 会话删除时同步更新客户端状态

2. **并发控制**
   - 使用行锁防止并发冲突
   - 乐观锁处理并发更新

3. **错误处理**
   - 数据库错误记录日志
   - 关键操作失败重试

4. **安全性**
   - 敏感数据加密存储
   - SQL注入防护
   - 访问权限控制

## 后续优化

- [ ] 添加Redis缓存层
- [ ] 实现消息分页查询优化
- [ ] 添加数据归档功能
- [ ] 实现多租户支持
- [ ] 添加数据统计报表
