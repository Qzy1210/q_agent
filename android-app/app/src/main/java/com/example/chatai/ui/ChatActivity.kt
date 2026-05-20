package com.example.chatai.ui

import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.chatai.R
import com.example.chatai.data.model.ConnectionState
import com.example.chatai.data.model.WebSocketState
import com.example.chatai.ui.adapter.MessageAdapter
import com.example.chatai.ui.viewmodel.ChatViewModel
import com.example.chatai.util.Constants
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch

/**
 * 聊天Activity - 消息列表页面
 */
class ChatActivity : AppCompatActivity() {

    private val viewModel: ChatViewModel by viewModels()

    // UI组件
    private lateinit var toolbar: Toolbar
    private lateinit var tvConnectionStatus: TextView
    private lateinit var recyclerView: RecyclerView
    private lateinit var tvEmpty: TextView
    private lateinit var inputContainer: LinearLayout
    private lateinit var etInput: EditText
    private lateinit var btnSend: Button
    private lateinit var progressBar: ProgressBar

    // 适配器
    private lateinit var adapter: MessageAdapter

    // 会话ID
    private var sessionId: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_chat)

        // 获取会话ID
        sessionId = intent.getStringExtra(Constants.EXTRA_SESSION_ID)

        initViews()
        setupRecyclerView()
        observeData()

        // 连接WebSocket（复用全局连接）
        sessionId?.let {
            viewModel.connect(it)
        }
    }

    /**
     * 初始化视图
     */
    private fun initViews() {
        toolbar = findViewById(R.id.toolbar)
        tvConnectionStatus = findViewById(R.id.tvConnectionStatus)
        recyclerView = findViewById(R.id.recyclerViewMessages)
        tvEmpty = findViewById(R.id.tvEmpty)
        inputContainer = findViewById(R.id.inputContainer)
        etInput = findViewById(R.id.etInput)
        btnSend = findViewById(R.id.btnSend)
        progressBar = findViewById(R.id.progressBar)

        // 设置Toolbar
        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        toolbar.setNavigationOnClickListener {
            finish()
        }

        // 发送按钮
        btnSend.setOnClickListener {
            sendMessage()
        }
    }

    /**
     * 设置RecyclerView
     */
    private fun setupRecyclerView() {
        adapter = MessageAdapter(viewModel.getCurrentClientId())
        val layoutManager = LinearLayoutManager(this)
        layoutManager.stackFromEnd = true  // 消息从底部开始
        recyclerView.layoutManager = layoutManager
        recyclerView.adapter = adapter
    }

    /**
     * 观察数据变化
     */
    private fun observeData() {
        // 消息列表
        lifecycleScope.launch {
            viewModel.messages.collect { messages ->
                adapter.submitList(messages) {
                    // 滚动到底部
                    if (messages.isNotEmpty()) {
                        recyclerView.smoothScrollToPosition(messages.size - 1)
                    }
                }
                tvEmpty.visibility = if (messages.isEmpty()) View.VISIBLE else View.GONE
            }
        }

        // 连接状态
        lifecycleScope.launch {
            viewModel.connectionState.collect { state ->
                updateConnectionStatus(state)
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
    }

    /**
     * 更新连接状态显示
     */
    private fun updateConnectionStatus(state: ConnectionState) {
        val (text, color) = when (state.state) {
            WebSocketState.CONNECTING -> {
                Pair("连接中...", R.color.status_connecting)
            }
            WebSocketState.CONNECTED -> {
                Pair("已连接", R.color.status_online)
            }
            WebSocketState.DISCONNECTED -> {
                Pair("已断开", R.color.status_offline)
            }
            WebSocketState.ERROR -> {
                Pair("连接错误", R.color.status_offline)
            }
            WebSocketState.RECONNECTING -> {
                Pair("重连中...", R.color.status_connecting)
            }
        }

        tvConnectionStatus.text = text
        tvConnectionStatus.setTextColor(getColor(color))

        // 根据连接状态启用/禁用发送按钮
        btnSend.isEnabled = state.isConnected()
    }

    /**
     * 发送消息
     */
    private fun sendMessage() {
        val text = etInput.text.toString().trim()
        if (text.isEmpty()) return

        if (viewModel.sendMessage(text)) {
            etInput.text.clear()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        viewModel.disconnect()
    }
}
