package com.example.chatai.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.chatai.data.model.ConnectionState
import com.example.chatai.data.model.Message
import com.example.chatai.data.repository.ChatRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 聊天页ViewModel
 * 管理消息列表和WebSocket连接
 */
class ChatViewModel : ViewModel() {

    private val repository = ChatRepository(viewModelScope)

    // 消息列表
    private val _messages = MutableStateFlow<List<Message>>(emptyList())
    val messages: StateFlow<List<Message>> = _messages.asStateFlow()

    // 连接状态
    private val _connectionState = MutableStateFlow<ConnectionState>(
        ConnectionState.disconnected()
    )
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    // 加载状态
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    // 错误信息
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    // 当前会话ID
    private var currentSessionId: String? = null

    /**
     * 连接WebSocket
     */
    fun connect(sessionId: String) {
        currentSessionId = sessionId

        // 监听连接状态
        viewModelScope.launch {
            repository.getConnectionState().collect { state ->
                _connectionState.value = state
            }
        }

        // 监听消息
        viewModelScope.launch {
            repository.messages.collect { messages ->
                _messages.value = messages
            }
        }

        // 连接WebSocket
        repository.connect(sessionId)

        // 加载历史消息
        loadMessages(sessionId)
    }

    /**
     * 断开连接
     */
    fun disconnect() {
        repository.disconnect()
        repository.clearMessages()
    }

    /**
     * 加载历史消息
     */
    fun loadMessages(sessionId: String) {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null

            try {
                repository.loadMessages(sessionId)
                _messages.value = repository.messages.value
            } catch (e: Exception) {
                _error.value = "加载失败: ${e.message}"
            } finally {
                _isLoading.value = false
            }
        }
    }

    /**
     * 发送消息
     */
    fun sendMessage(text: String): Boolean {
        if (text.isBlank()) return false

        val success = repository.sendMessage(text)
        if (!success) {
            _error.value = "发送失败，请检查连接"
        }
        return success
    }

    /**
     * 获取当前客户端ID
     */
    fun getCurrentClientId(): String {
        return repository.getCurrentClientId()
    }

    /**
     * 是否已连接
     */
    fun isConnected(): Boolean {
        return repository.isConnected()
    }

    /**
     * 清除错误
     */
    fun clearError() {
        _error.value = null
    }
}
