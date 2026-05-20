package com.example.chatai.ui.viewmodel

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.chatai.ChatApplication
import com.example.chatai.data.model.ConnectionState
import com.example.chatai.data.model.Session
import com.example.chatai.data.repository.ChatRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 主页ViewModel
 * 管理会话列表和连接状态
 */
class MainViewModel : ViewModel() {

    companion object {
        private const val TAG = "MainViewModel"
    }

    // 使用Application级别的共享Repository实例
    private val repository: ChatRepository = ChatApplication.instance.repository

    // 会话列表
    private val _sessions = MutableStateFlow<List<Session>>(emptyList())
    val sessions: StateFlow<List<Session>> = _sessions.asStateFlow()

    // 加载状态
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    // 错误信息
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    // 连接状态
    private val _connectionState = MutableStateFlow<ConnectionState>(
        ConnectionState.disconnected()
    )
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    init {
        loadSessions()
        observeConnectionState()
    }

    /**
     * 监听连接状态
     */
    private fun observeConnectionState() {
        viewModelScope.launch {
            repository.getConnectionState().collect { state ->
                _connectionState.value = state
            }
        }
    }

    /**
     * 加载会话列表
     */
    fun loadSessions() {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null

            try {
                repository.loadSessions()
                _sessions.value = repository.sessions.value
            } catch (e: Exception) {
                _error.value = "加载失败: ${e.message}"
            } finally {
                _isLoading.value = false
            }
        }
    }

    /**
     * 创建新会话
     */
    fun createSession(onCreated: (String) -> Unit) {
        Log.d(TAG, "createSession called")
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null

            try {
                Log.d(TAG, "Calling repository.createSession()")
                val sessionId = repository.createSession()
                Log.d(TAG, "createSession result: $sessionId")
                if (sessionId != null) {
                    _sessions.value = repository.sessions.value
                    onCreated(sessionId)
                } else {
                    _error.value = "创建会话失败"
                }
            } catch (e: Exception) {
                Log.e(TAG, "createSession error: ${e.message}", e)
                _error.value = "创建失败: ${e.message}"
            } finally {
                _isLoading.value = false
            }
        }
    }

    /**
     * 连接 WebSocket
     */
    fun connect() {
        repository.connect()
    }

    /**
     * 断开连接
     */
    fun disconnect() {
        repository.disconnect()
    }

    /**
     * 是否已连接
     */
    fun isConnected(): Boolean = repository.isConnected()

    /**
     * 获取服务器地址
     */
    fun getServerUrl(): String = repository.getServerUrl()

    /**
     * 获取客户端ID
     */
    fun getClientId(): String = repository.getCurrentClientId()

    /**
     * 获取用户ID
     */
    fun getUserId(): String = repository.getCurrentUserId()

    /**
     * 获取会话ID
     */
    fun getSessionId(): String? = repository.getSessionId()

    /**
     * 清除错误
     */
    fun clearError() {
        _error.value = null
    }
}
