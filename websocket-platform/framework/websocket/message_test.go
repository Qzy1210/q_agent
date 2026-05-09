package websocket

import (
	"testing"
	
	"github.com/stretchr/testify/assert"
)

func TestNewMessage(t *testing.T) {
	content := &TextContent{Text: "Hello, World!"}
	message := NewMessage(MessageTypeText, "client1", "session1", content)
	
	assert.NotNil(t, message)
	assert.NotEmpty(t, message.ID)
	assert.Equal(t, MessageTypeText, message.Type)
	assert.Equal(t, "client1", message.From)
	assert.Equal(t, "session1", message.SessionID)
	assert.NotZero(t, message.Timestamp)
	assert.NotNil(t, message.Content)
}

func TestMessageToJSON(t *testing.T) {
	content := &TextContent{Text: "Hello, World!"}
	message := NewMessage(MessageTypeText, "client1", "session1", content)
	
	data, err := message.ToJSON()
	assert.NoError(t, err)
	assert.NotEmpty(t, data)
}

func TestMessageFromJSON(t *testing.T) {
	jsonData := `{"id":"msg1","type":"text","from":"client1","session_id":"session1","timestamp":1234567890,"content":{"text":"Hello, World!"}}`
	
	var message Message
	err := message.FromJSON([]byte(jsonData))
	
	assert.NoError(t, err)
	assert.Equal(t, "msg1", message.ID)
	assert.Equal(t, MessageTypeText, message.Type)
	assert.Equal(t, "client1", message.From)
	assert.Equal(t, "session1", message.SessionID)
	assert.Equal(t, int64(1234567890), message.Timestamp)
}

func TestTextContent(t *testing.T) {
	content := &TextContent{Text: "Test message"}
	message := NewMessage(MessageTypeText, "client1", "session1", content)
	
	data, err := message.ToJSON()
	assert.NoError(t, err)
	
	var parsed Message
	err = parsed.FromJSON(data)
	assert.NoError(t, err)
}

func TestFileContent(t *testing.T) {
	content := &FileContent{
		Name:    "test.txt",
		Type:    "text/plain",
		Size:    1024,
		Content: "dGVzdCBjb250ZW50",
	}
	
	message := NewMessage(MessageTypeFile, "client1", "session1", content)
	
	data, err := message.ToJSON()
	assert.NoError(t, err)
	
	var parsed Message
	err = parsed.FromJSON(data)
	assert.NoError(t, err)
}

func TestToolCallContent(t *testing.T) {
	content := &ToolCallContent{
		ToolName: "calculator",
		Parameters: map[string]interface{}{
			"expression": "2+2",
		},
	}
	
	message := NewMessage(MessageTypeToolCall, "client1", "session1", content)
	
	data, err := message.ToJSON()
	assert.NoError(t, err)
	
	var parsed Message
	err = parsed.FromJSON(data)
	assert.NoError(t, err)
}

func TestToolResultContent(t *testing.T) {
	content := &ToolResultContent{
		ToolName: "calculator",
		Result:   4,
	}
	
	message := NewMessage(MessageTypeToolResult, "client1", "session1", content)
	
	data, err := message.ToJSON()
	assert.NoError(t, err)
	
	var parsed Message
	err = parsed.FromJSON(data)
	assert.NoError(t, err)
}

func TestStatusContent(t *testing.T) {
	content := &StatusContent{
		Status:  "connected",
		Message: "Welcome!",
	}
	
	message := NewMessage(MessageTypeStatus, "system", "session1", content)
	
	data, err := message.ToJSON()
	assert.NoError(t, err)
	
	var parsed Message
	err = parsed.FromJSON(data)
	assert.NoError(t, err)
}

func TestHeartbeatContent(t *testing.T) {
	content := &HeartbeatContent{
		Timestamp: 1234567890,
	}
	
	message := NewMessage(MessageTypeHeartbeat, "system", "session1", content)
	
	data, err := message.ToJSON()
	assert.NoError(t, err)
	
	var parsed Message
	err = parsed.FromJSON(data)
	assert.NoError(t, err)
}
