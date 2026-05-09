.PHONY: build run clean test

# 项目名称
PROJECT_NAME=websocket-platform
# 输出目录
BUILD_DIR=bin
# 主程序入口
MAIN_FILE=cmd/server/main.go

# 构建
build:
	@echo "Building $(PROJECT_NAME)..."
	@mkdir -p $(BUILD_DIR)
	@go build -o $(BUILD_DIR)/$(PROJECT_NAME) $(MAIN_FILE)
	@echo "Build complete: $(BUILD_DIR)/$(PROJECT_NAME)"

# 运行
run:
	@echo "Running $(PROJECT_NAME)..."
	@go run $(MAIN_FILE)

# 清理
clean:
	@echo "Cleaning..."
	@rm -rf $(BUILD_DIR)
	@echo "Clean complete"

# 测试
test:
	@echo "Running tests..."
	@go test -v ./...

# 安装依赖
deps:
	@echo "Installing dependencies..."
	@go mod download
	@go mod tidy
	@echo "Dependencies installed"

# 格式化代码
fmt:
	@echo "Formatting code..."
	@go fmt ./...
	@echo "Code formatted"

# 代码检查
lint:
	@echo "Running linter..."
	@golangci-lint run
	@echo "Lint complete"

# 帮助
help:
	@echo "Available targets:"
	@echo "  make build  - Build the project"
	@echo "  make run    - Run the project"
	@echo "  make clean  - Clean build files"
	@echo "  make test   - Run tests"
	@echo "  make deps   - Install dependencies"
	@echo "  make fmt    - Format code"
	@echo "  make lint   - Run linter"
