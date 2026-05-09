package bootstrap

import (
	"websocket-platform/framework/config"
	"websocket-platform/framework/drivers"
	"websocket-platform/framework/provider"
)

// MysqlProvider 数据库服务提供者
type MysqlProvider struct{}

// NewMysqlProvider 创建数据库提供者
func NewMysqlProvider() provider.Provider {
	return &MysqlProvider{}
}

// Name 返回提供者名称
func (p *MysqlProvider) Name() string {
	return "mysql"
}

// Init 初始化数据库（轻量级操作：加载配置）
func (p *MysqlProvider) Init() error {
	return nil
}

// Boot 启动数据库服务（重量级操作：建立数据库连接）
func (p *MysqlProvider) Boot() error {
	mysqlConfig := config.MysqlInstance()
	return drivers.InitMySQL(
		mysqlConfig.Host,
		mysqlConfig.Port,
		mysqlConfig.Database,
		mysqlConfig.Username,
		mysqlConfig.Password,
		mysqlConfig.Charset,
		mysqlConfig.MaxOpenConns,
		mysqlConfig.MaxIdleConns,
		mysqlConfig.ConnMaxLifetime,
	)
}

// Close 关闭数据库连接
func (p *MysqlProvider) Close() error {
	return drivers.Close()
}
