package bootstrap

import (
	"websocket-platform/framework/config"
	"websocket-platform/framework/provider"
)

// ConfigProvider 配置服务提供者
type ConfigProvider struct {
	configPath string
}

// NewConfigProvider 创建配置提供者
func NewConfigProvider(configPath string) provider.Provider {
	return &ConfigProvider{
		configPath: configPath,
	}
}

// Name 返回提供者名称
func (p *ConfigProvider) Name() string {
	return "config"
}

// Init 初始化配置（轻量级操作）
func (p *ConfigProvider) Init() error {
	return config.InitConfig(p.configPath)
}

// Boot 启动配置服务（配置不需要启动操作）
func (p *ConfigProvider) Boot() error {
	return nil
}

// Close 关闭配置服务（配置不需要清理操作）
func (p *ConfigProvider) Close() error {
	return nil
}
