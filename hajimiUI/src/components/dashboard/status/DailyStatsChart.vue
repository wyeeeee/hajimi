<template>
  <div class="daily-stats-section" :class="{ 'animate-in': isVisible }">
    <div class="section-header" @click="toggleCollapse">
      <h3 class="section-title">
        <span class="toggle-icon">{{ isCollapsed ? '▶' : '▼' }}</span>
        每日调用统计
      </h3>
      <div class="section-actions">
        <button class="action-btn export-btn" @click.stop="exportData" title="导出数据">
          <span class="btn-icon">↓</span> 导出
        </button>
        <button class="action-btn import-btn" @click.stop="triggerImport" title="导入数据">
          <span class="btn-icon">↑</span> 导入
        </button>
        <input
          type="file"
          ref="fileInput"
          @change="handleFileImport"
          accept=".csv,.json"
          style="display: none"
        />
      </div>
    </div>
    
    <div v-show="!isCollapsed" class="daily-stats-content">
      <!-- 统计表格 -->
      <div class="daily-stats-table-container">
        <div class="stats-summary">
          <span class="stats-summary-item">
            <span class="summary-label">统计天数:</span>
            <span class="summary-value">{{ dailyStats.length }}天</span>
          </span>
        </div>
        <table class="daily-stats-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>调用次数</th>
              <th>Token使用量</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="stat in dailyStats" :key="stat.date">
              <td>{{ stat.date }}</td>
              <td>
                <span class="stat-value">{{ stat.calls }}</span>
              </td>
              <td>
                <span class="stat-value">{{ stat.tokens }}</span>
              </td>
            </tr>
            <tr v-if="dailyStats.length === 0">
              <td colspan="3" class="empty-data">暂无统计数据</td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td><strong>总计</strong></td>
              <td>
                <span class="stat-value total">{{ totalCalls }}</span>
              </td>
              <td>
                <span class="stat-value total">{{ totalTokens }}</span>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, nextTick, watch } from 'vue'

export default {
  name: 'DailyStatsChart',
  
  setup() {
    const dailyStats = ref([])
    const isVisible = ref(false)
    const isCollapsed = ref(false)
    const fileInput = ref(null)
    
    const totalCalls = computed(() => {
      return dailyStats.value.reduce((sum, stat) => sum + (parseInt(stat.calls) || 0), 0)
    })
    
    const totalTokens = computed(() => {
      return dailyStats.value.reduce((sum, stat) => sum + (parseInt(stat.tokens) || 0), 0)
    })
    
    const toggleCollapse = () => {
      isCollapsed.value = !isCollapsed.value
    }
    
    const fetchDailyStats = async () => {
      try {
        // 添加时间戳和随机数避免缓存
        const timestamp = new Date().getTime()
        const random = Math.floor(Math.random() * 10000)
        
        const response = await fetch(`/api/daily-stats?_t=${timestamp}&_r=${random}`, {
          headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache'
          }
        })
        
        if (!response.ok) {
          throw new Error(`HTTP error ${response.status}`)
        }
        
        const data = await response.json()
        
        if (data && data.daily_stats && Array.isArray(data.daily_stats)) {
          // 按日期排序（最新的在前面）
          dailyStats.value = [...data.daily_stats].sort((a, b) => {
            return new Date(b.date) - new Date(a.date)
          })
        } else {
          console.warn('获取的每日统计数据格式不正确')
        }
      } catch (error) {
        console.error('获取每日统计数据失败:', error)
      }
    }
    
    // 导出数据功能
    const exportData = (event) => {
      event.stopPropagation() // 阻止冒泡，避免触发折叠面板
      
      if (dailyStats.value.length === 0) {
        alert('没有可导出的数据')
        return
      }
      
      try {
        // 准备CSV数据
        const headers = ['日期', '调用次数', 'Token使用量']
        const csvContent = [
          headers.join(','),
          ...dailyStats.value.map(stat => 
            `${stat.date},${stat.calls},${stat.tokens}`
          )
        ].join('\n')
        
        // 创建Blob对象
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
        const url = URL.createObjectURL(blob)
        
        // 创建下载链接
        const link = document.createElement('a')
        const date = new Date().toISOString().split('T')[0]
        link.href = url
        link.setAttribute('download', `hajimi_daily_stats_${date}.csv`)
        document.body.appendChild(link)
        
        // 模拟点击下载
        link.click()
        
        // 清理
        setTimeout(() => {
          document.body.removeChild(link)
          URL.revokeObjectURL(url)
        }, 100)
      } catch (error) {
        console.error('导出数据失败:', error)
        alert('导出数据失败，请查看控制台获取详细信息')
      }
    }
    
    // 触发导入文件选择器
    const triggerImport = (event) => {
      event.stopPropagation() // 阻止冒泡，避免触发折叠面板
      fileInput.value.click()
    }
    
    // 处理文件导入
    const handleFileImport = async (event) => {
      const file = event.target.files[0]
      if (!file) return
      
      try {
        const reader = new FileReader()
        
        reader.onload = async (e) => {
          try {
            const content = e.target.result
            let importedData = []
            
            // 根据文件类型处理数据
            if (file.name.endsWith('.csv')) {
              // 处理CSV文件
              const lines = content.split('\n')
              const headers = lines[0].split(',')
              
              importedData = lines.slice(1).filter(line => line.trim()).map(line => {
                const values = line.split(',')
                return {
                  date: values[0],
                  calls: parseInt(values[1]) || 0,
                  tokens: parseInt(values[2]) || 0
                }
              })
            } else if (file.name.endsWith('.json')) {
              // 处理JSON文件
              const jsonData = JSON.parse(content)
              if (Array.isArray(jsonData)) {
                importedData = jsonData.map(item => ({
                  date: item.date,
                  calls: parseInt(item.calls) || 0,
                  tokens: parseInt(item.tokens) || 0
                }))
              }
            }
            
            if (importedData.length === 0) {
              alert('导入的文件不包含有效数据')
              return
            }
            
            // 确认导入
            if (confirm(`确定要导入${importedData.length}条数据记录吗？`)) {
              try {
                // 发送数据到后端API
                const response = await fetch('/api/daily-stats/import', {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json'
                  },
                  body: JSON.stringify(importedData)
                })
                
                if (!response.ok) {
                  const errorData = await response.json()
                  throw new Error(errorData.detail || `HTTP错误: ${response.status}`)
                }
                
                const result = await response.json()
                
                // 导入成功后更新显示
                alert(`导入成功: ${result.message}`)
                
                // 重新获取最新数据
                await fetchDailyStats()
              } catch (apiError) {
                console.error('API调用失败:', apiError)
                alert(`导入失败: ${apiError.message}`)
              }
            }
          } catch (error) {
            console.error('处理导入文件失败:', error)
            alert('处理导入文件失败，请确保文件格式正确')
          }
        }
        
        if (file.name.endsWith('.csv')) {
          reader.readAsText(file)
        } else if (file.name.endsWith('.json')) {
          reader.readAsText(file)
        } else {
          alert('不支持的文件格式，请上传CSV或JSON文件')
        }
      } catch (error) {
        console.error('文件导入失败:', error)
        alert('文件导入失败，请查看控制台获取详细信息')
      } finally {
        // 重置文件输入，允许重新选择同一文件
        event.target.value = null
      }
    }
    
    // 组件挂载后自动执行一次获取
    onMounted(() => {
      fetchDailyStats()
      
      // 组件可见性动画
      setTimeout(() => {
        isVisible.value = true
      }, 100)
      
      // 定时刷新数据
      const refreshInterval = setInterval(() => {
        fetchDailyStats()
      }, 30000) // 从60000毫秒(60秒)改为30000毫秒(30秒)
      
      // 组件卸载时清除定时器
      return () => clearInterval(refreshInterval)
    })
    
    return {
      dailyStats,
      isVisible,
      isCollapsed,
      totalCalls,
      totalTokens,
      toggleCollapse,
      fetchDailyStats,
      exportData,
      triggerImport,
      handleFileImport,
      fileInput
    }
  }
}
</script>

<style scoped>
.daily-stats-section {
  opacity: 0;
  transform: translateY(10px);
  transition: opacity 0.5s ease, transform 0.5s ease;
  background-color: var(--color-bg-panel);
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.animate-in {
  opacity: 1;
  transform: translateY(0);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  cursor: pointer;
  background-color: var(--color-bg-subtle);
  border-bottom: 1px solid var(--color-border);
}

.section-title {
  margin: 0;
  font-size: 1rem;
  color: var(--color-heading);
  display: flex;
  align-items: center;
}

.toggle-icon {
  margin-right: 8px;
  font-size: 0.8rem;
  transition: transform 0.3s ease;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg-panel);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 3px 8px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background-color: var(--color-bg-hover);
  border-color: var(--color-primary-50);
}

.export-btn {
  color: var(--color-success);
}

.import-btn {
  color: var(--color-primary);
}

.btn-icon {
  margin-right: 4px;
  font-weight: bold;
}

.daily-stats-content {
  padding: 15px;
}

.daily-stats-table-container {
  margin-bottom: 20px;
  overflow-x: auto;
}

.stats-summary {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  padding: 8px 10px;
  background-color: var(--color-bg-subtle);
  border-radius: 6px;
}

.stats-summary-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-label {
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.summary-value {
  font-weight: 600;
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: 0.95rem;
}

.daily-stats-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.daily-stats-table th,
.daily-stats-table td {
  padding: 10px;
  border-bottom: 1px solid var(--color-border-light);
}

.daily-stats-table th {
  background-color: var(--color-bg-subtle);
  font-weight: 600;
  color: var(--color-heading);
}

.daily-stats-table tbody tr:hover {
  background-color: var(--color-bg-hover);
}

.daily-stats-table tfoot {
  font-weight: 600;
}

.daily-stats-table tfoot td {
  border-top: 2px solid var(--color-border);
}

.stat-value {
  font-family: var(--font-mono);
  font-size: 0.9rem;
}

.stat-value.total {
  color: var(--color-primary);
  font-weight: 600;
}

.empty-data {
  text-align: center;
  color: var(--color-text-muted);
  padding: 20px;
}

@media (max-width: 640px) {
  .daily-stats-table th,
  .daily-stats-table td {
    padding: 8px 5px;
    font-size: 0.85rem;
  }
  
  .action-btn {
    padding: 2px 5px;
    font-size: 0.75rem;
  }
  
  .btn-icon {
    margin-right: 2px;
  }
}
</style> 