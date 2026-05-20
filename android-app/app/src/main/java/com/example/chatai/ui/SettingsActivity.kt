package com.example.chatai.ui

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import com.example.chatai.ChatApplication
import com.example.chatai.R
import com.example.chatai.data.api.WebSocketManager
import com.example.chatai.data.repository.ChatRepository
import com.google.android.material.snackbar.Snackbar
import java.util.UUID

/**
 * 设置页面
 * 支持配置服务器地址、Client ID、User ID、Session ID 等连接参数
 * 参考 web/index.html 的连接设置面板
 */
class SettingsActivity : AppCompatActivity() {

    private lateinit var toolbar: Toolbar
    private lateinit var etServerUrl: EditText
    private lateinit var etClientId: EditText
    private lateinit var etUserId: EditText
    private lateinit var etSessionId: EditText
    private lateinit var btnRegenerateClientId: Button
    private lateinit var btnRegenerateUserId: Button
    private lateinit var btnSave: Button

    private val repository: ChatRepository by lazy { ChatApplication.instance.repository }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        initViews()
        loadSettings()
    }

    private fun initViews() {
        toolbar = findViewById(R.id.toolbar)
        etServerUrl = findViewById(R.id.etServerUrl)
        etClientId = findViewById(R.id.etClientId)
        etUserId = findViewById(R.id.etUserId)
        etSessionId = findViewById(R.id.etSessionId)
        btnRegenerateClientId = findViewById(R.id.btnRegenerateClientId)
        btnRegenerateUserId = findViewById(R.id.btnRegenerateUserId)
        btnSave = findViewById(R.id.btnSave)

        // 返回按钮
        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        toolbar.setNavigationOnClickListener { finish() }

        // 重新生成 Client ID
        btnRegenerateClientId.setOnClickListener {
            etClientId.setText("client_${UUID.randomUUID().toString().replace("-", "").take(9)}")
        }

        // 重新生成 User ID
        btnRegenerateUserId.setOnClickListener {
            etUserId.setText("user_${UUID.randomUUID().toString().replace("-", "").take(9)}")
        }

        // 保存设置
        btnSave.setOnClickListener {
            saveSettings()
        }
    }

    /**
     * 加载当前设置
     */
    private fun loadSettings() {
        etServerUrl.setText(repository.getServerUrl())
        etClientId.setText(repository.getCurrentClientId())
        etUserId.setText(repository.getCurrentUserId())
        repository.getSessionId()?.let { etSessionId.setText(it) }
    }

    /**
     * 保存设置
     */
    private fun saveSettings() {
        val serverUrl = etServerUrl.text.toString().trim()
        val clientId = etClientId.text.toString().trim()
        val userId = etUserId.text.toString().trim()
        val sessionId = etSessionId.text.toString().trim()

        // 验证服务器地址
        if (serverUrl.isEmpty()) {
            etServerUrl.error = "请输入服务器地址"
            return
        }

        if (!serverUrl.startsWith("ws://") && !serverUrl.startsWith("wss://")) {
            etServerUrl.error = "地址必须以 ws:// 或 wss:// 开头"
            return
        }

        // 验证必填项
        if (clientId.isEmpty()) {
            etClientId.error = "请输入客户端 ID"
            return
        }

        if (userId.isEmpty()) {
            etUserId.error = "请输入用户 ID"
            return
        }

        if (sessionId.isEmpty()) {
            etSessionId.error = "请输入会话 ID"
            return
        }

        // 断开当前连接（如果已连接），保存设置后会自动重连
        val wasConnected = repository.isConnected()
        if (wasConnected) {
            repository.disconnect()
        }

        // 保存设置到 Repository
        repository.setServerUrl(serverUrl)
        repository.setClientId(clientId)
        repository.setUserId(userId)
        repository.setSessionId(sessionId)

        // 如果之前已连接，使用新配置重新连接
        if (wasConnected) {
            repository.connect()
        }

        Snackbar.make(btnSave, R.string.settings_saved, Snackbar.LENGTH_SHORT).show()

        // 延迟返回
        btnSave.postDelayed({ finish() }, 500)
    }
}
