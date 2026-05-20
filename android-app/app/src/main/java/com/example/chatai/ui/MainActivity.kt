package com.example.chatai.ui

import android.content.Intent
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.ImageButton
import android.widget.ProgressBar
import android.widget.TextView
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.chatai.R
import com.example.chatai.data.model.ConnectionState
import com.example.chatai.data.model.WebSocketState
import com.example.chatai.ui.adapter.SessionAdapter
import com.example.chatai.ui.viewmodel.MainViewModel
import com.example.chatai.util.Constants
import com.google.android.material.button.MaterialButton
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch

/**
 * 主Activity - 会话列表页面
 * 参考 web/index.html 的连接设置面板
 */
class MainActivity : AppCompatActivity() {

    private val viewModel: MainViewModel by viewModels()

    // UI组件
    private lateinit var toolbar: Toolbar
    private lateinit var btnSettings: ImageButton
    private lateinit var statusDot: View
    private lateinit var tvConnectionStatus: TextView
    private lateinit var btnConnect: Button
    private lateinit var tvConfigInfo: TextView
    private lateinit var recyclerView: RecyclerView
    private lateinit var tvEmpty: TextView
    private lateinit var progressBar: ProgressBar

    // 手动设置会话相关组件
    private lateinit var manualSessionContainer: View
    private lateinit var btnEnterSession: MaterialButton

    // 适配器
    private lateinit var adapter: SessionAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        initViews()
        setupRecyclerView()
        observeData()
    }

    /**
     * 初始化视图
     */
    private fun initViews() {
        toolbar = findViewById(R.id.toolbar)
        btnSettings = findViewById(R.id.btnSettings)
        statusDot = findViewById(R.id.statusDot)
        tvConnectionStatus = findViewById(R.id.tvConnectionStatus)
        btnConnect = findViewById(R.id.btnConnect)
        tvConfigInfo = findViewById(R.id.tvConfigInfo)
        recyclerView = findViewById(R.id.recyclerViewSessions)
        tvEmpty = findViewById(R.id.tvEmpty)
        progressBar = findViewById(R.id.progressBar)
        manualSessionContainer = findViewById(R.id.manualSessionContainer)
        btnEnterSession = findViewById(R.id.btnEnterSession)

        // 设置Toolbar
        setSupportActionBar(toolbar)

        // 设置按钮
        btnSettings.setOnClickListener {
            startActivity(Intent(this, SettingsActivity::class.java))
        }

        // 连接/断开按钮
        btnConnect.setOnClickListener {
            if (viewModel.isConnected()) {
                viewModel.disconnect()
            } else {
                viewModel.connect()
            }
        }

        // 进入手动设置的会话
        btnEnterSession.setOnClickListener {
            viewModel.getSessionId()?.let { sessionId ->
                // 先建立连接（如果未连接）
                if (!viewModel.isConnected()) {
                    viewModel.connect()
                }
                startChatActivity(sessionId)
            }
        }
    }

    /**
     * 设置RecyclerView
     */
    private fun setupRecyclerView() {
        adapter = SessionAdapter { session ->
            // 点击会话，跳转到聊天页面
            startChatActivity(session.id)
        }
        recyclerView.layoutManager = LinearLayoutManager(this)
        recyclerView.adapter = adapter
    }

    /**
     * 观察数据变化
     */
    private fun observeData() {
        // 会话列表
        lifecycleScope.launch {
            viewModel.sessions.collect { sessions ->
                adapter.submitList(sessions)
                tvEmpty.visibility = if (sessions.isEmpty()) View.VISIBLE else View.GONE
            }
        }

        // 加载状态
        lifecycleScope.launch {
            viewModel.isLoading.collect { isLoading ->
                progressBar.visibility = if (isLoading) View.VISIBLE else View.GONE
            }
        }

        // 错误信息
        lifecycleScope.launch {
            viewModel.error.collect { error ->
                error?.let {
                    Snackbar.make(recyclerView, it, Snackbar.LENGTH_LONG).show()
                    viewModel.clearError()
                }
            }
        }

        // 连接状态
        lifecycleScope.launch {
            viewModel.connectionState.collect { state ->
                updateConnectionStatus(state)
            }
        }

        // 配置信息
        updateConfigInfo()
    }

    /**
     * 更新连接状态显示
     */
    private fun updateConnectionStatus(state: ConnectionState) {
        val (text, color, dotColor) = when (state.state) {
            WebSocketState.CONNECTING -> {
                Triple("连接中...", R.color.status_connecting, R.color.status_connecting)
            }
            WebSocketState.CONNECTED -> {
                Triple("已连接", R.color.status_online, R.color.status_online)
            }
            WebSocketState.DISCONNECTED -> {
                Triple("已断开", R.color.status_offline, R.color.status_offline)
            }
            WebSocketState.ERROR -> {
                Triple("连接错误", R.color.status_offline, R.color.status_offline)
            }
            WebSocketState.RECONNECTING -> {
                Triple("重连中...", R.color.status_connecting, R.color.status_connecting)
            }
        }

        tvConnectionStatus.text = text
        tvConnectionStatus.setTextColor(ContextCompat.getColor(this, color))

        // 更新状态点颜色
        val drawable = GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(ContextCompat.getColor(this@MainActivity, dotColor))
        }
        statusDot.background = drawable

        // 更新按钮文字
        btnConnect.text = if (state.isConnected()) getString(R.string.disconnect) else getString(R.string.connect)
    }

    /**
     * 更新配置信息显示
     */
    private fun updateConfigInfo() {
        val serverUrl = viewModel.getServerUrl()
        val clientId = viewModel.getClientId()
        val userId = viewModel.getUserId()
        val sessionId = viewModel.getSessionId()

        val info = buildString {
            append("服务器: $serverUrl\n")
            append("Client: ${clientId.take(12)}... | User: $userId\n")
            if (sessionId != null) {
                append("Session: $sessionId")
            }
        }
        tvConfigInfo.text = info

        // 根据是否手动设置了会话ID来显示/隐藏手动会话入口
        // 如果有手动设置的会话ID，显示进入会话按钮，隐藏会话列表
        if (sessionId != null) {
            manualSessionContainer.visibility = View.VISIBLE
            // 隐藏会话列表和空状态提示
            recyclerView.visibility = View.GONE
            tvEmpty.visibility = View.GONE
        } else {
            manualSessionContainer.visibility = View.GONE
            // 显示会话列表
            recyclerView.visibility = View.VISIBLE
        }
    }

    override fun onResume() {
        super.onResume()
        // 返回时更新配置信息
        updateConfigInfo()
    }

    /**
     * 跳转到聊天页面
     */
    private fun startChatActivity(sessionId: String) {
        val intent = Intent(this, ChatActivity::class.java).apply {
            putExtra(Constants.EXTRA_SESSION_ID, sessionId)
        }
        startActivity(intent)
    }
}
