package com.example.chatai.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.chatai.ChatApplication
import com.example.chatai.data.model.ConnectionState
import com.example.chatai.data.model.Message
import com.example.chatai.data.repository.ChatRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.delay

/**
 * 聊天页ViewModel
 * 管理消息列表和WebSocket连接
 */
class ChatViewModel : ViewModel() {

    // 使用Application级别的共享Repository实例
    private val repository: ChatRepository = ChatApplication.instance.repository

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
     * 连接WebSocket并加载历史消息
     * 复用全局连接，如果已连接到相同session则不重新连接
     */
    fun connect(sessionId: String) {
        currentSessionId = sessionId

        // 监听连接状态
        viewModelScope.launch {
            repository.getConnectionState().collect { state ->
                _connectionState.value = state
            }
        }

        // 监听消息（合并策略，WebSocket消息会自动添加）
        viewModelScope.launch {
            repository.messages.collect { messages ->
                _messages.value = messages
            }
        }

        // 设置会话ID
        repository.setSessionId(sessionId)

        // 如果未连接或连接到不同的session，则建立连接
        if (!repository.isConnected()) {
            repository.connect(sessionId)
        }

        // 延迟加载历史消息（等待WebSocket历史消息先到达）
        // WebSocket连接后会自动发送历史消息，我们延迟500ms后再加载REST API消息
        // 这样可以避免重复，并确保消息合并正确
        viewModelScope.launch {
            delay(500)
            loadMessages(sessionId)
        }
    }

    /**
     * 断开连接
     * 注意：退出聊天页面时不断开全局连接，只在需要时才断开
     */
    fun disconnect() {
        // 不再调用 repository.disconnect()
        // 全局连接由 Application 级别管理
        // 只清空当前页面的消息列表
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