package com.example.chatai.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.ProgressBar
import android.widget.TextView
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.chatai.R
import com.example.chatai.ui.adapter.SessionAdapter
import com.example.chatai.ui.viewmodel.MainViewModel
import com.example.chatai.util.Constants
import com.google.android.material.button.MaterialButton
import com.google.android.material.snackbar.Snackbar

/**
 * 主Activity - 会话列表页面
 */
class MainActivity : AppCompatActivity() {

    private val viewModel: MainViewModel by viewModels()

    // UI组件
    private lateinit var toolbar: Toolbar
    private lateinit var btnNewSession: MaterialButton
    private lateinit var recyclerView: RecyclerView
    private lateinit var tvEmpty: TextView
    private lateinit var progressBar: ProgressBar

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
        btnNewSession = findViewById(R.id.btnNewSession)
        recyclerView = findViewById(R.id.recyclerViewSessions)
        tvEmpty = findViewById(R.id.tvEmpty)
        progressBar = findViewById(R.id.progressBar)

        // 设置Toolbar
        setSupportActionBar(toolbar)

        // 创建新会话按钮
        btnNewSession.setOnClickListener {
            viewModel.createSession { sessionId ->
                // 跳转到聊天页面
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
        viewModel.sessions.observe(this) { sessions ->
            adapter.submitList(sessions)
            tvEmpty.visibility = if (sessions.isEmpty()) View.VISIBLE else View.GONE
        }

        // 加载状态
        viewModel.isLoading.observe(this) { isLoading ->
            progressBar.visibility = if (isLoading) View.VISIBLE else View.GONE
        }

        // 错误信息
        viewModel.error.observe(this) { error ->
            error?.let {
                Snackbar.make(recyclerView, it, Snackbar.LENGTH_LONG).show()
                viewModel.clearError()
            }
        }
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
