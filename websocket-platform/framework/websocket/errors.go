package websocket

import "errors"

var (
	// ErrMaxConnectionsReached 达到最大连接数
	ErrMaxConnectionsReached = errors.New("maximum connections reached")
	
	// ErrSendChannelFull 发送通道已满
	ErrSendChannelFull = errors.New("send channel is full")
	
	// ErrClientNotFound 客户端不存在
	ErrClientNotFound = errors.New("client not found")
	
	// ErrInvalidMessageType 无效的消息类型
	ErrInvalidMessageType = errors.New("invalid message type")
	
	// ErrInvalidClientType 无效的客户端类型
	ErrInvalidClientType = errors.New("invalid client type")
)
