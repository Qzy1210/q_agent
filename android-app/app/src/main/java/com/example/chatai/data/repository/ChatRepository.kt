package com.example.chatai.data.repository

import com.example.chatai.data.api.ApiClient
import com.example.chatai.data.api.ApiService
import com.example.chatai.data.api.WebSocketManager
import com.example.chatai.data.model.*
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.util.UUID

/**
 * 聊天数据仓库
 * 统一管理WebSocket和API数据
 */
class ChatRepository(
    private val scope: CoroutineScope
) {

    private val apiService: ApiService = ApiClient.getApiService()
    private val webSocketManager = WebSocketManager()

    // 当前用户ID（模拟登录）
    private var currentUserId: String = "user_${System.currentTimeMillis()}"

    // 当前客户端ID
    private var currentClientId: String = UUID.randomUUID().toString()

    // 当前会话ID
    private var currentSessionId: String? = null

    // 消息列表
    private val _messages = MutableStateFlow<List<Message>>(emptyList())
    val messages: StateFlow<List<Message>> = _messages

    // 会话列表
    private val _sessions = MutableStateFlow<List<Session>>(emptyList())
    val sessions: StateFlow<List<Session>> = _sessions

    // 加载状态
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    // 错误信息
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error

    init {
        // 初始化WebSocket
        webSocketManager.init(scope)

        // 监听WebSocket消息
        scope.launch {
            webSocketManager.messageFlow.collect { message ->
                message?.let {
                    addMessage(it)
                }
            }
        }
    }

    /**
     * 获取连接状态
     */
    fun getConnectionState(): StateFlow<ConnectionState> {
        return webSocketManager.connectionState
    }

    /**
     * 连接WebSocket
     */
    fun connect(sessionId: String) {
        currentSessionId = sessionId
        webSocketManager.connect(currentClientId, currentUserId, sessionId)
    }

    /**
     * 断开WebSocket
     */
    fun disconnect() {
        webSocketManager.disconnect()
    }

    /**
     * 发送消息
     */
    fun sendMessage(text: String): Boolean {
        if (text.isBlank()) return false

        val success = webSocketManager.sendMessage(text)
        if (success) {
            // 添加到本地消息列表（乐观更新）
            val message = Message(
                id = UUID.randomUUID().toString(),
                type = MessageType.TEXT,
                from = currentClientId,
                sessionId = currentSessionId ?: "",
                timestamp = System.currentTimeMillis(),
                content = MessageContent(text = text)
            )
            addMessage(message)
        }
        return success
    }

    /**
     * 添加消息到列表
     */
    private fun addMessage(message: Message) {
        val currentList = _messages.value.toMutableList()
        // 检查是否已存在（避免重复）
        if (currentList.none { it.id == message.id }) {
            currentList.add(message)
            _messages.value = currentList
        }
    }

    /**
     * 获取会话列表
     */
    suspend fun loadSessions() {
        _isLoading.value = true
        _error.value = null

        try {
            val response = apiService.getSessions(currentUserId)
            _sessions.value = response.sessions
        } catch (e: Exception) {
            _error.value = "获取会话列表失败: ${e.message}"
        } finally {
            _isLoading.value = false
        }
    }

    /**
     * 创建新会话
     */
    suspend fun createSession(): String? {
        _isLoading.value = true
        _error.value = null

        try {
            val response = apiService.createSession(
                CreateSessionRequest(currentUserId)
            )
            // 刷新会话列表
            loadSessions()
            return response.sessionId
        } catch (e: Exception) {
            _error.value = "创建会话失败: ${e.message}"
            return null
        } finally {
            _isLoading.value = false
        }
    }

    /**
     * 加载会话消息历史
     */
    suspend fun loadMessages(sessionId: String, limit: Int = 50, offset: Int = 0) {
        _isLoading.value = true
        _error.value = null

        try {
            val response = apiService.getSessionMessages(sessionId, limit, offset)
            // 转换MessageData为Message
            val messages = response.messages.map { data ->
                Message(
                    id = data.id,
                    type = data.type,
                    from = data.from,
                    to = data.to,
                    sessionId = data.sessionId,
                    timestamp = data.timestamp,
                    content = MessageContent(text = data.content)
                )
            }
            _messages.value = messages
        } catch (e: Exception) {
            _error.value = "获取消息历史失败: ${e.message}"
        } finally {
            _isLoading.value = false
        }
    }

    /**
     * 清空消息
     */
    fun clearMessages() {
        _messages.value = emptyList()
    }

    /**
     * 获取当前用户ID
     */
    fun getCurrentUserId(): String = currentUserId

    /**
     * 获取当前客户端ID
     */
    fun getCurrentClientId(): String = currentClientId

    /**
     * 是否已连接
     */
    fun isConnected(): Boolean = webSocketManager.isConnected()
}
