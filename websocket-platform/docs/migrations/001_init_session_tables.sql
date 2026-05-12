-- WebSocket平台会话持久化表结构
-- 创建时间: 2024-05-09
-- 说明: 会话、客户端和消息记录表

-- 会话表
CREATE TABLE IF NOT EXISTS `sessions` (
  `id` varchar(64) NOT NULL COMMENT '会话ID',
  `user_id` varchar(64) NOT NULL COMMENT '用户ID',
  `status` varchar(20) DEFAULT 'active' COMMENT '会话状态(active/inactive/closed)',
  `created_at` datetime(3) DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime(3) DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_sessions_user_id` (`user_id`),
  KEY `idx_sessions_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话表';

-- 会话客户端关联表
CREATE TABLE IF NOT EXISTS `session_clients` (
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

-- 消息记录表
CREATE TABLE IF NOT EXISTS `messages` (
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
