package com.example.chatai.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.chatai.data.model.Session
import com.example.chatai.data.repository.ChatRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 主页ViewModel
 * 管理会话列表
 */
class MainViewModel : ViewModel() {

    private val repository = ChatRepository(viewModelScope)

    // 会话列表
    private val _sessions = MutableStateFlow<List<Session>>(emptyList())
    val sessions: StateFlow<List<Session>> = _sessions.asStateFlow()

    // 加载状态
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    // 错误信息
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    init {
        loadSessions()
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
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null

            try {
                val sessionId = repository.createSession()
                if (sessionId != null) {
                    _sessions.value = repository.sessions.value
                    onCreated(sessionId)
                } else {
                    _error.value = "创建会话失败"
                }
            } catch (e: Exception) {
                _error.value = "创建失败: ${e.message}"
            } finally {
                _isLoading.value = false
            }
        }
    }

    /**
     * 清除错误
     */
    fun clearError() {
        _error.value = null
    }
}
