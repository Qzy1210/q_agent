package bootstrap

import (
	"websocket-platform/framework/config"
	"websocket-platform/framework/log"
	"websocket-platform/framework/provider"
)

// LoggerProvider 日志服务提供者
type LoggerProvider struct{}

// NewLoggerProvider 创建日志提供者
func NewLoggerProvider() provider.Provider {
	return &LoggerProvider{}
}

// Name 返回提供者名称
func (p *LoggerProvider) Name() string {
	return "logger"
}

// Init 初始化日志（轻量级操作：创建日志实例）
func (p *LoggerProvider) Init() error {
	loggerConfig := config.LoggerInstance()
	return log.InitLogger(
		loggerConfig.Level,
		loggerConfig.Encoding,
		loggerConfig.OutputPaths,
		loggerConfig.ErrorOutputPaths,
	)
}

// Boot 启动日志服务（日志不需要启动操作）
func (p *LoggerProvider) Boot() error {
	return nil
}

// Close 关闭日志服务（刷新日志缓冲）
func (p *LoggerProvider) Close() error {
	return log.Sync()
}
