package com.example.chatai.ui.adapter

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.chatai.R
import com.example.chatai.data.model.Session
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * 会话列表适配器
 */
class SessionAdapter(
    private val onItemClick: (Session) -> Unit
) : ListAdapter<Session, SessionAdapter.ViewHolder>(DiffCallback()) {

    private val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault())

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_session, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val session = getItem(position)
        holder.bind(session)
    }

    inner class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val tvSessionId: TextView = itemView.findViewById(R.id.tvSessionId)
        private val tvStatus: TextView = itemView.findViewById(R.id.tvStatus)
        private val tvTime: TextView = itemView.findViewById(R.id.tvTime)

        init {
            itemView.setOnClickListener {
                val position = bindingAdapterPosition
                if (position != RecyclerView.NO_POSITION) {
                    onItemClick(getItem(position))
                }
            }
        }

        fun bind(session: Session) {
            tvSessionId.text = "会话ID: ${session.id.take(8)}..."
            tvStatus.text = when (session.status) {
                Session.STATUS_ACTIVE -> "活跃"
                Session.STATUS_INACTIVE -> "不活跃"
                Session.STATUS_CLOSED -> "已关闭"
                else -> session.status
            }

            // 设置状态颜色
            val statusColor = when (session.status) {
                Session.STATUS_ACTIVE -> itemView.context.getColor(R.color.status_online)
                else -> itemView.context.getColor(R.color.status_offline)
            }
            tvStatus.setTextColor(statusColor)

            // 显示时间
            session.updatedAt?.let {
                tvTime.text = dateFormat.format(it)
            } ?: run {
                session.createdAt?.let {
                    tvTime.text = dateFormat.format(it)
                }
            }
        }
    }

    class DiffCallback : DiffUtil.ItemCallback<Session>() {
        override fun areItemsTheSame(oldItem: Session, newItem: Session): Boolean {
            return oldItem.id == newItem.id
        }

        override fun areContentsTheSame(oldItem: Session, newItem: Session): Boolean {
            return oldItem == newItem
        }
    }
}
