package com.example.chatai

import android.app.Application
import com.example.chatai.data.repository.ChatRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

/**
 * Application类
 */
class ChatApplication : Application() {

    // Application级别的协程作用域
    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    // 全局Repository实例（确保user_id持久化）
    val repository: ChatRepository by lazy {
        ChatRepository(applicationScope, applicationContext)
    }

    override fun onCreate() {
        super.onCreate()
        // 应用初始化
        instance = this
    }

    companion object {
        lateinit var instance: ChatApplication
            private set
    }
}
