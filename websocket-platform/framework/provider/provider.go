package provider

// Provider 定义服务提供者接口
// 所有服务组件（配置、日志、数据库、HTTP、WebSocket等）都必须实现此接口
type Provider interface {
	// Name 返回 Provider 名称
	Name() string
	
	// Init 初始化资源（轻量级操作：加载配置、创建实例）
	Init() error
	
	// Boot 启动服务（重量级操作：建立连接、启动服务）
	Boot() error
	
	// Close 清理资源（优雅关闭、释放资源）
	Close() error
}
