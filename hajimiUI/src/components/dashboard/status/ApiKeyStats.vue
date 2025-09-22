<script setup>
import { useDashboardStore } from '../../../stores/dashboard'
import { computed, ref } from 'vue'
import ApiCallsChart from './ApiCallsChart.vue'

const dashboardStore = useDashboardStore()
const apiKeyStatsVisible = ref(false)
// 存储每个API密钥的模型折叠状态
const modelFoldState = ref({})

// 新增API密钥输入相关变量
const showApiKeyInput = ref(false)
const newApiKeys = ref('')
const apiKeyPassword = ref('')
const apiKeyError = ref('')
const apiKeySuccess = ref('')
const isSubmitting = ref(false)

// 检测API密钥相关状态
const showApiKeyTestDialog = ref(false)
const apiKeyTestPassword = ref('')
const apiKeyTestError = ref('')
const apiKeyTestSuccess = ref('')
const isTestingKeys = ref(false)
const testingProgress = ref(0)
const testingTotal = ref(0)

// 清除失效API密钥相关状态
const showClearInvalidKeysDialog = ref(false)
const clearInvalidKeysPassword = ref('')
const clearInvalidKeysError = ref('')
const clearInvalidKeysSuccess = ref('')
const isClearingKeys = ref(false)

// 输出有效API密钥相关状态
const showExportValidKeysDialog = ref(false)
const exportValidKeysPassword = ref('')
const exportValidKeysError = ref('')
const exportValidKeysSuccess = ref('')
const isExportingKeys = ref(false)
const exportedKeys = ref([])

// 分页相关
const currentPage = ref(1)
const itemsPerPage = 20

// 切换API密钥统计显示/隐藏
function toggleApiKeyStats() {
  apiKeyStatsVisible.value = !apiKeyStatsVisible.value
}

// 切换API密钥测试对话框显示/隐藏
function toggleApiKeyTestDialog() {
  showApiKeyTestDialog.value = !showApiKeyTestDialog.value
  if (!showApiKeyTestDialog.value) {
    // 重置表单
    apiKeyTestPassword.value = ''
    apiKeyTestError.value = ''
    apiKeyTestSuccess.value = ''
  }
}

// 切换API密钥输入表单显示/隐藏
function toggleApiKeyInput() {
  showApiKeyInput.value = !showApiKeyInput.value
  if (!showApiKeyInput.value) {
    // 重置表单
    newApiKeys.value = ''
    apiKeyPassword.value = ''
    apiKeyError.value = ''
    apiKeySuccess.value = ''
  }
}

// 提交新的API密钥
async function submitApiKeys() {
  // 重置消息
  apiKeyError.value = ''
  apiKeySuccess.value = ''
  
  // 表单验证
  if (!newApiKeys.value.trim()) {
    apiKeyError.value = '请输入API密钥'
    return
  }
  
  if (!apiKeyPassword.value.trim()) {
    apiKeyError.value = '请输入密码'
    return
  }
  
  // 验证API密钥格式 - 支持换行和逗号分隔
  const keys = newApiKeys.value.split(/[,\n\r]+/).map(key => key.trim()).filter(key => key)
  if (keys.length === 0) {
    apiKeyError.value = '请输入至少一个有效的API密钥'
    return
  }
  
  // 验证是否有无效的密钥格式
  for (const key of keys) {
    if (key.length < 10) { // 简单验证，实际可能需要更复杂的验证
      apiKeyError.value = `API密钥格式不正确: ${key}`
      return
    }
  }
  
  isSubmitting.value = true
  try {
    // 调用API添加密钥
    await dashboardStore.updateConfig(
      'geminiApiKeys',
      newApiKeys.value,
      apiKeyPassword.value
    )
    
    // 成功提示
    apiKeySuccess.value = `成功添加 ${keys.length} 个API密钥`
    
    // 清空输入框
    newApiKeys.value = ''
    apiKeyPassword.value = ''
    
    // 刷新数据
    await dashboardStore.fetchDashboardData()
  } catch (error) {
    apiKeyError.value = error.message || '添加API密钥失败'
  } finally {
    isSubmitting.value = false
  }
}

// 提交API密钥检测
async function submitApiKeyTest() {
  // 重置消息
  apiKeyTestError.value = ''
  apiKeyTestSuccess.value = ''
  
  // 表单验证
  if (!apiKeyTestPassword.value.trim()) {
    apiKeyTestError.value = '请输入密码'
    return
  }
  
  isTestingKeys.value = true
  testingProgress.value = 0
  
  try {
    // 调用API进行密钥检测
    const response = await fetch('/api/test-api-keys', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        password: apiKeyTestPassword.value
      })
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || '测试API密钥失败')
    }
    
    // 开始轮询检测进度
    const pollInterval = setInterval(async () => {
      try {
        const progressResponse = await fetch('/api/test-api-keys/progress')
        const progressData = await progressResponse.json()
        
        testingProgress.value = progressData.completed
        testingTotal.value = progressData.total
        
        if (progressData.is_completed) {
          clearInterval(pollInterval)
          apiKeyTestSuccess.value = `检测完成！有效密钥: ${progressData.valid} 个，无效密钥: ${progressData.invalid} 个`
          
          // 刷新数据
          await dashboardStore.fetchDashboardData()
          isTestingKeys.value = false
          
          // 如果成功，5秒后自动关闭对话框
          setTimeout(() => {
            if (showApiKeyTestDialog.value) {
              showApiKeyTestDialog.value = false
            }
          }, 5000)
        }
      } catch (error) {
        console.error('轮询进度时出错:', error)
      }
    }, 1000)
    
  } catch (error) {
    apiKeyTestError.value = error.message || '测试API密钥失败'
    isTestingKeys.value = false
  }
}

// 切换清除失效API密钥对话框显示/隐藏
function toggleClearInvalidKeysDialog() {
  showClearInvalidKeysDialog.value = !showClearInvalidKeysDialog.value
  if (!showClearInvalidKeysDialog.value) {
    // 重置表单
    clearInvalidKeysPassword.value = ''
    clearInvalidKeysError.value = ''
    clearInvalidKeysSuccess.value = ''
  }
}

// 提交清除失效API密钥
async function submitClearInvalidKeys() {
  // 重置消息
  clearInvalidKeysError.value = ''
  clearInvalidKeysSuccess.value = ''
  
  // 表单验证
  if (!clearInvalidKeysPassword.value.trim()) {
    clearInvalidKeysError.value = '请输入密码'
    return
  }
  
  isClearingKeys.value = true
  
  try {
    // 调用API清除失效密钥
    const response = await fetch('/api/clear-invalid-api-keys', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        password: clearInvalidKeysPassword.value
      })
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || '清除失效API密钥失败')
    }
    
    const data = await response.json()
    clearInvalidKeysSuccess.value = data.message || '清除失效API密钥成功'
    
    // 清空密码输入框
    clearInvalidKeysPassword.value = ''
    
    // 刷新数据
    await dashboardStore.fetchDashboardData()
    
    // 如果成功，3秒后自动关闭对话框
    setTimeout(() => {
      if (showClearInvalidKeysDialog.value) {
        showClearInvalidKeysDialog.value = false
      }
    }, 3000)
    
  } catch (error) {
    clearInvalidKeysError.value = error.message || '清除失效API密钥失败'
  } finally {
    isClearingKeys.value = false
  }
}

// 切换输出有效API密钥对话框显示/隐藏
function toggleExportValidKeysDialog() {
  showExportValidKeysDialog.value = !showExportValidKeysDialog.value
  if (!showExportValidKeysDialog.value) {
    // 重置表单
    exportValidKeysPassword.value = ''
    exportValidKeysError.value = ''
    exportValidKeysSuccess.value = ''
    exportedKeys.value = []
  }
}

// 提交输出有效API密钥
async function submitExportValidKeys() {
  // 重置消息
  exportValidKeysError.value = ''
  exportValidKeysSuccess.value = ''
  exportedKeys.value = []
  
  // 表单验证
  if (!exportValidKeysPassword.value.trim()) {
    exportValidKeysError.value = '请输入密码'
    return
  }
  
  isExportingKeys.value = true
  
  try {
    // 调用API获取有效密钥
    const response = await fetch('/api/export-valid-api-keys', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        password: exportValidKeysPassword.value
      })
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || '获取有效API密钥失败')
    }
    
    const data = await response.json()
    exportValidKeysSuccess.value = data.message || '获取有效API密钥成功'
    exportedKeys.value = data.keys || []
    
    // 清空密码输入框
    exportValidKeysPassword.value = ''
    
  } catch (error) {
    exportValidKeysError.value = error.message || '获取有效API密钥失败'
  } finally {
    isExportingKeys.value = false
  }
}

// 复制密钥到剪贴板
async function copyKeyToClipboard(key) {
  try {
    await navigator.clipboard.writeText(key)
    // 可以添加一个临时的成功提示
    console.log('密钥已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
  }
}

// 复制所有密钥到剪贴板
async function copyAllKeysToClipboard() {
  if (exportedKeys.value.length === 0) return
  
  try {
    const allKeys = exportedKeys.value.join('\n')
    await navigator.clipboard.writeText(allKeys)
    console.log('所有密钥已复制到剪贴板')
  } catch (error) {
    console.error('复制失败:', error)
  }
}

// 切换模型详情的折叠状态
function toggleModelFold(apiKeyId) {
  if (!modelFoldState.value[apiKeyId]) {
    modelFoldState.value[apiKeyId] = true
  } else {
    modelFoldState.value[apiKeyId] = !modelFoldState.value[apiKeyId]
  }
}

// 获取折叠图标类
const getFoldIconClass = (isVisible) => {
  return isVisible ? 'fold-icon rotated' : 'fold-icon'
}

// 计算进度条颜色类
const getProgressBarClass = (usagePercent) => {
  if (usagePercent > 75) return 'high'
  if (usagePercent > 50) return 'medium'
  return 'low'
}

// 获取模型列表并按使用次数排序
const getModelStats = (modelStats) => {
  if (!modelStats) return []
  
  return Object.entries(modelStats)
    .map(([model, data]) => ({ 
      model, 
      calls: data.calls,
      tokens: data.tokens
    }))
    .sort((a, b) => b.calls - a.calls)
}

// 判断是否需要折叠
const shouldFoldModels = (modelStats) => {
  return modelStats && Object.keys(modelStats).length > 3
}

// 计算总页数
const totalPages = computed(() => {
  if (!dashboardStore.apiKeyStats.length) return 0
  return Math.ceil(dashboardStore.apiKeyStats.length / itemsPerPage)
})

// 获取当前页的API密钥
const paginatedApiKeys = computed(() => {
  if (!dashboardStore.apiKeyStats.length) return []
  
  const startIndex = (currentPage.value - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  
  return dashboardStore.apiKeyStats.slice(startIndex, endIndex)
})

// 切换到下一页
function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

// 切换到上一页
function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

// 计算总调用次数
const totalCalls = computed(() => {
  return dashboardStore.apiKeyStats.reduce((sum, key) => sum + key.calls_24h, 0)
})

// 计算总Token使用量
const totalTokens = computed(() => {
  return dashboardStore.apiKeyStats.reduce((sum, key) => sum + key.total_tokens, 0)
})
</script>

<template>
  <div class="api-key-stats-container" v-if="!dashboardStore.status.enableVertex">
    <div class="header-section">
      <h3 class="section-title fold-header" @click="toggleApiKeyStats">
        API调用统计
        <span :class="getFoldIconClass(apiKeyStatsVisible)">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </span>
      </h3>
      
      <div class="header-buttons">
        <!-- 添加API密钥按钮 -->
        <button class="add-api-key-button" @click="toggleApiKeyInput">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          添加API密钥
        </button>
        
        <!-- 添加检测API密钥按钮 -->
        <button class="test-api-key-button" @click="toggleApiKeyTestDialog">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path>
            <line x1="16" y1="8" x2="2" y2="22"></line>
            <line x1="17.5" y1="15" x2="9" y2="15"></line>
          </svg>
          检测API密钥
        </button>
        
        <!-- 添加清除失效API密钥按钮 -->
        <button class="clear-invalid-keys-button" @click="toggleClearInvalidKeysDialog">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 6h18"></path>
            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
            <line x1="10" y1="11" x2="10" y2="17"></line>
            <line x1="14" y1="11" x2="14" y2="17"></line>
          </svg>
          清除失效密钥
        </button>
        
        <!-- 添加输出有效API密钥按钮 -->
        <button class="export-valid-keys-button" @click="toggleExportValidKeysDialog">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7,10 12,15 17,10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          输出有效密钥
        </button>
      </div>
    </div>
    
    <!-- API密钥输入表单 -->
    <transition name="slide">
      <div v-if="showApiKeyInput" class="api-key-input-form">
        <div class="form-group">
          <label for="newApiKeys">API密钥 (以逗号分隔)</label>
          <textarea 
            id="newApiKeys" 
            v-model="newApiKeys" 
            placeholder="在此输入API密钥，多个密钥请用逗号分隔（注意：如果您使用的是云部署方案或您没有配置持久化，在此处配置的api密钥在重启后会丢失）"
            :disabled="isSubmitting"
            rows="3"
            class="api-key-textarea"
          ></textarea>
        </div>
        
        <div class="form-group">
          <label for="apiKeyPassword">密码</label>
          <input 
            id="apiKeyPassword" 
            v-model="apiKeyPassword" 
            type="password" 
            placeholder="请输入管理密码"
            :disabled="isSubmitting"
            class="api-key-password"
          />
        </div>
        
        <div v-if="apiKeyError" class="api-key-error">
          {{ apiKeyError }}
        </div>
        
        <div v-if="apiKeySuccess" class="api-key-success">
          {{ apiKeySuccess }}
        </div>
        
        <div class="form-actions">
          <button 
            class="submit-api-key" 
            @click="submitApiKeys" 
            :disabled="isSubmitting"
          >
            <span v-if="isSubmitting">提交中...</span>
            <span v-else>提交</span>
          </button>
          
          <button 
            class="cancel-api-key" 
            @click="toggleApiKeyInput" 
            :disabled="isSubmitting"
          >
            取消
          </button>
        </div>
      </div>
    </transition>
    
    <!-- API密钥测试对话框 -->
    <transition name="slide">
      <div v-if="showApiKeyTestDialog" class="api-key-test-form">
        <div class="form-title">
          <h4>API密钥检测</h4>
          <p class="form-description">
            此操作将同时检测所有有效和无效API密钥的状态，有效密钥将保存在GEMINI_API_KEYS中，
            而无效密钥将移至INVALID_API_KEYS。该过程在后台异步进行，不会阻塞服务运行。
          </p>
        </div>
        
        <div v-if="isTestingKeys" class="testing-progress">
          <div class="progress-bar-container">
            <div 
              class="progress-bar-fill" 
              :style="{ width: testingTotal ? `${(testingProgress / testingTotal) * 100}%` : '0%' }"
            ></div>
          </div>
          <div class="progress-text">
            正在检测: {{ testingProgress }} / {{ testingTotal }} ({{ Math.round((testingProgress / (testingTotal || 1)) * 100) }}%)
          </div>
        </div>
        
        <div v-else class="form-group">
          <label for="apiKeyTestPassword">管理密码</label>
          <input 
            id="apiKeyTestPassword" 
            v-model="apiKeyTestPassword" 
            type="password" 
            placeholder="请输入管理密码以确认操作"
            class="api-key-password"
          />
        </div>
        
        <div v-if="apiKeyTestError" class="api-key-error">
          {{ apiKeyTestError }}
        </div>
        
        <div v-if="apiKeyTestSuccess" class="api-key-success">
          {{ apiKeyTestSuccess }}
        </div>
        
        <div class="form-actions">
          <button 
            v-if="!isTestingKeys"
            class="submit-api-key" 
            @click="submitApiKeyTest" 
          >
            开始检测
          </button>
          
          <button 
            class="cancel-api-key" 
            @click="toggleApiKeyTestDialog" 
            :disabled="isTestingKeys"
          >
            {{ isTestingKeys ? '检测中...' : '取消' }}
          </button>
        </div>
      </div>
    </transition>
    
    <!-- 清除失效API密钥对话框 -->
    <transition name="slide">
      <div v-if="showClearInvalidKeysDialog" class="clear-invalid-keys-form">
        <div class="form-title">
          <h4>清除失效API密钥</h4>
          <p class="form-description">
            此操作将永久清除所有存储在INVALID_API_KEYS中的失效API密钥。
            清除后，这些密钥将无法恢复，请确认操作。
          </p>
        </div>
        
        <div class="form-group">
          <label for="clearInvalidKeysPassword">管理密码</label>
          <input 
            id="clearInvalidKeysPassword" 
            v-model="clearInvalidKeysPassword" 
            type="password" 
            placeholder="请输入管理密码以确认操作"
            class="api-key-password"
            :disabled="isClearingKeys"
          />
        </div>
        
        <div v-if="clearInvalidKeysError" class="api-key-error">
          {{ clearInvalidKeysError }}
        </div>
        
        <div v-if="clearInvalidKeysSuccess" class="api-key-success">
          {{ clearInvalidKeysSuccess }}
        </div>
        
        <div class="form-actions">
          <button 
            class="submit-api-key" 
            @click="submitClearInvalidKeys" 
            :disabled="isClearingKeys"
          >
            <span v-if="isClearingKeys">清除中...</span>
            <span v-else>确认清除</span>
          </button>
          
          <button 
            class="cancel-api-key" 
            @click="toggleClearInvalidKeysDialog" 
            :disabled="isClearingKeys"
          >
            取消
          </button>
        </div>
      </div>
    </transition>
    
    <!-- 输出有效API密钥对话框 -->
    <transition name="slide">
      <div v-if="showExportValidKeysDialog" class="export-valid-keys-form">
        <div class="form-title">
          <h4>输出有效API密钥</h4>
          <p class="form-description">
            此操作将显示当前所有有效的API密钥。请注意保护您的密钥安全。
          </p>
        </div>
        
        <div v-if="exportedKeys.length === 0" class="form-group">
          <label for="exportValidKeysPassword">管理密码</label>
          <input 
            id="exportValidKeysPassword" 
            v-model="exportValidKeysPassword" 
            type="password" 
            placeholder="请输入管理密码以确认操作"
            class="api-key-password"
            :disabled="isExportingKeys"
          />
        </div>
        
        <div v-if="exportValidKeysError" class="api-key-error">
          {{ exportValidKeysError }}
        </div>
        
        <div v-if="exportValidKeysSuccess" class="api-key-success">
          {{ exportValidKeysSuccess }}
        </div>
        
        <!-- 显示导出的密钥列表 -->
        <div v-if="exportedKeys.length > 0" class="exported-keys-container">
          <div class="exported-keys-header">
            <h5>有效API密钥列表 ({{ exportedKeys.length }} 个)</h5>
            <button class="copy-all-button" @click="copyAllKeysToClipboard">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              复制全部
            </button>
          </div>
          
          <div class="exported-keys-list">
            <div v-for="(key, index) in exportedKeys" :key="index" class="exported-key-item">
              <div class="key-text">{{ key }}</div>
              <button class="copy-key-button" @click="copyKeyToClipboard(key)" title="复制密钥">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
            </div>
          </div>
        </div>
        
        <div class="form-actions">
          <button 
            v-if="exportedKeys.length === 0"
            class="submit-api-key" 
            @click="submitExportValidKeys" 
            :disabled="isExportingKeys"
          >
            <span v-if="isExportingKeys">获取中...</span>
            <span v-else>获取密钥</span>
          </button>
          
          <button 
            class="cancel-api-key" 
            @click="toggleExportValidKeysDialog" 
            :disabled="isExportingKeys"
          >
            关闭
          </button>
        </div>
      </div>
    </transition>
    
    <!-- 收起时显示的总计信息 -->
    <div v-if="!apiKeyStatsVisible" class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ dashboardStore.status.last24hCalls }}</div>
        <div class="stat-label">24小时调用次数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ dashboardStore.status.hourlyCalls }}</div>
        <div class="stat-label">小时调用次数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ dashboardStore.status.minuteCalls }}</div>
        <div class="stat-label">分钟调用次数</div>
      </div>
    </div>
    
    <!-- Token消耗统计 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ dashboardStore.status.last24hTokens.toLocaleString() }}</div>
        <div class="stat-label">24小时Token消耗</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ dashboardStore.status.hourlyTokens.toLocaleString() }}</div>
        <div class="stat-label">小时Token消耗</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ dashboardStore.status.minuteTokens.toLocaleString() }}</div>
        <div class="stat-label">分钟Token消耗</div>
      </div>
    </div>
    
    <!-- 添加实时API调用图表 -->
    <ApiCallsChart v-if="!apiKeyStatsVisible" />
    
    <!-- 展开时显示的详细API密钥信息 -->
    <transition name="fold">
      <div v-if="apiKeyStatsVisible" class="fold-content">
        <!-- 总计信息 -->
        <div class="stats-summary">
          <div class="summary-item">
            <div class="summary-label">总调用次数</div>
            <div class="summary-value">{{ totalCalls.toLocaleString() }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">总Token使用量</div>
            <div class="summary-value">{{ totalTokens.toLocaleString() }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">API密钥数量</div>
            <div class="summary-value">{{ dashboardStore.apiKeyStats.length }}</div>
          </div>
        </div>
        
        <!-- 添加实时API调用图表 -->
        <ApiCallsChart />
        
        <div class="api-key-stats-list">
          <div v-if="!dashboardStore.apiKeyStats.length" class="api-key-item">
            没有API密钥使用数据
          </div>
          <div v-for="(stat, index) in paginatedApiKeys" :key="index" class="api-key-item">
            <div class="api-key-header">
              <div class="api-key-name">API密钥: {{ stat.api_key }}</div>
              <div class="api-key-usage">
                <span class="api-key-count">{{ stat.calls_24h }}</span> /
                <span class="api-key-limit">{{ stat.limit }}</span>
                <span class="api-key-percent">({{ stat.usage_percent }}%)</span>
              </div>
            </div>
            <div class="progress-container">
              <div
                class="progress-bar"
                :class="getProgressBarClass(stat.usage_percent)"
                :style="{ width: Math.min(stat.usage_percent, 100) + '%' }"
              ></div>
            </div>
            
            <!-- 显示总token使用量 -->
            <div class="total-tokens">
              <span class="total-tokens-label">总Token使用量:</span>
              <span class="total-tokens-value">{{ stat.total_tokens.toLocaleString() }}</span>
            </div>
            
            <!-- 模型使用统计 -->
            <div v-if="stat.model_stats && Object.keys(stat.model_stats).length > 0" class="model-stats-container">
              <div class="model-stats-header" @click="toggleModelFold(stat.api_key)">
                <span class="model-stats-title">模型使用统计</span>
                <span :class="getFoldIconClass(modelFoldState[stat.api_key])">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="6 9 12 15 18 9"></polyline>
                  </svg>
                </span>
              </div>
              
              <transition name="fold">
                <div v-if="modelFoldState[stat.api_key]" class="model-stats-list fold-content">
                  <!-- 显示所有模型或前三个模型 -->
                  <div v-for="(modelStat, mIndex) in getModelStats(stat.model_stats).slice(0, shouldFoldModels(stat.model_stats) && !modelFoldState[stat.api_key] ? 3 : undefined)" :key="mIndex" class="model-stat-item">
                    <div class="model-info">
                      <div class="model-name">{{ modelStat.model }}</div>
                      <div class="model-count">
                        <span>{{ modelStat.calls }}</span>
                        <span class="model-usage-text">次调用</span>
                      </div>
                      <div class="model-tokens">{{ modelStat.tokens.toLocaleString() }} tokens</div>
                    </div>
                  </div>
                  
                  <!-- 显示"查看更多"按钮，如果模型数量超过3个且未展开全部 -->
                  <div
                    v-if="shouldFoldModels(stat.model_stats) && getModelStats(stat.model_stats).length > 3"
                    class="view-more-models"
                    @click="toggleModelFold(stat.api_key)"
                  >
                    {{ modelFoldState[stat.api_key] ? '收起' : '查看更多模型' }}
                  </div>
                </div>
              </transition>
            </div>
          </div>
        </div>
        
        <!-- 分页控件 -->
        <div v-if="dashboardStore.apiKeyStats.length > itemsPerPage" class="pagination">
          <button 
            class="pagination-button" 
            :disabled="currentPage === 1"
            @click="prevPage"
          >
            上一页
          </button>
          <div class="pagination-info">
            第 {{ currentPage }} 页 / 共 {{ totalPages }} 页
          </div>
          <button 
            class="pagination-button" 
            :disabled="currentPage === totalPages"
            @click="nextPage"
          >
            下一页
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.api-key-stats-container {
  margin-top: 20px;
}

/* 添加头部区域样式 */
.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

/* 头部按钮容器样式 */
.header-buttons {
  display: flex;
  gap: 10px;
}

/* API密钥添加按钮样式 */
.add-api-key-button {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: var(--button-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: var(--shadow-sm);
}

.add-api-key-button svg {
  transition: transform 0.3s ease;
  stroke: white;
}

.add-api-key-button:hover {
  background-color: var(--button-primary-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.add-api-key-button:hover svg {
  transform: rotate(90deg);
  stroke: white;
}

/* API密钥检测按钮样式 */
.test-api-key-button {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: var(--button-secondary);
  color: var(--button-secondary-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: var(--shadow-sm);
}

.test-api-key-button svg {
  transition: transform 0.3s ease;
  stroke: var(--button-secondary-text);
}

.test-api-key-button:hover {
  background-color: var(--button-secondary-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.test-api-key-button:hover svg {
  transform: rotate(15deg);
}

/* 清除失效API密钥按钮样式 */
.clear-invalid-keys-button {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: var(--button-danger, #dc3545);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: var(--shadow-sm);
}

.clear-invalid-keys-button svg {
  transition: transform 0.3s ease;
  stroke: white;
}

.clear-invalid-keys-button:hover {
  background-color: var(--button-danger-hover, #c82333);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.clear-invalid-keys-button:hover svg {
  transform: scale(1.1);
}

/* 输出有效API密钥按钮样式 */
.export-valid-keys-button {
  display: flex;
  align-items: center;
  gap: 8px;
  background-color: var(--button-success, #28a745);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: var(--shadow-sm);
}

.export-valid-keys-button svg {
  transition: transform 0.3s ease;
  stroke: white;
}

.export-valid-keys-button:hover {
  background-color: var(--button-success-hover, #218838);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.export-valid-keys-button:hover svg {
  transform: translateY(-1px);
}

/* API密钥测试表单样式 */
.api-key-test-form {
  background-color: var(--color-background-mute);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid var(--card-border);
  box-shadow: var(--shadow-md);
}

/* 清除失效API密钥表单样式 */
.clear-invalid-keys-form {
  background-color: var(--color-background-mute);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid var(--card-border);
  box-shadow: var(--shadow-md);
}

/* 输出有效API密钥表单样式 */
.export-valid-keys-form {
  background-color: var(--color-background-mute);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid var(--card-border);
  box-shadow: var(--shadow-md);
}

/* 导出的密钥容器样式 */
.exported-keys-container {
  margin-top: 15px;
}

.exported-keys-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.exported-keys-header h5 {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-heading);
  margin: 0;
}

.copy-all-button {
  display: flex;
  align-items: center;
  gap: 6px;
  background-color: var(--button-primary);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.copy-all-button:hover {
  background-color: var(--button-primary-hover);
  transform: translateY(-1px);
}

.copy-all-button svg {
  stroke: white;
}

.exported-keys-list {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background-color: var(--color-background);
}

.exported-key-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border);
  transition: background-color 0.2s ease;
}

.exported-key-item:last-child {
  border-bottom: none;
}

.exported-key-item:hover {
  background-color: var(--color-background-mute);
}

.key-text {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: var(--color-text);
  word-break: break-all;
  flex: 1;
  margin-right: 10px;
}

.copy-key-button {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: transparent;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 28px;
  height: 28px;
}

.copy-key-button:hover {
  background-color: var(--button-primary);
  color: white;
  border-color: var(--button-primary);
}

.copy-key-button svg {
  stroke: currentColor;
}

.form-title {
  margin-bottom: 15px;
}

.form-title h4 {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-heading);
  margin-bottom: 8px;
}

.form-description {
  font-size: 14px;
  color: var(--color-text);
  line-height: 1.5;
  opacity: 0.8;
}

/* 进度条样式 */
.testing-progress {
  margin: 15px 0;
}

.progress-bar-container {
  height: 10px;
  background-color: var(--color-background-soft);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-bar-fill {
  height: 100%;
  background: var(--gradient-primary);
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
  position: relative;
}

.progress-bar-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transform: translateX(-100%);
  animation: progressShine 2s infinite;
}

.progress-text {
  font-size: 14px;
  text-align: center;
  color: var(--color-heading);
}

/* 滑动动画 */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
  max-height: 500px;
  opacity: 1;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
  padding: 0;
  margin: 0;
  overflow: hidden;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
  margin-top: 15px;
  margin-bottom: 20px;
}

.stat-card {
  background-color: var(--stats-item-bg);
  padding: 15px;
  border-radius: var(--radius-lg);
  text-align: center;
  box-shadow: var(--shadow-sm);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--card-border);
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: var(--gradient-secondary);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.stat-card:hover::before {
  opacity: 1;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow-md);
  border-color: var(--button-primary);
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: var(--button-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: all 0.3s ease;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 14px;
  color: var(--color-text);
  margin-top: 5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: all 0.3s ease;
  opacity: 0.8;
}

/* 总计信息样式 */
.stats-summary {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
  background-color: var(--color-background-mute);
  border-radius: var(--radius-lg);
  padding: 15px;
  border: 1px solid var(--card-border);
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.summary-label {
  font-size: 12px;
  color: var(--color-text);
  opacity: 0.8;
  margin-bottom: 5px;
}

.summary-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--button-primary);
}

.api-key-stats-list {
  display: grid;
  grid-template-columns: repeat(3, 1fr); /* 电脑上显示为三列 */
  gap: 15px;
  margin-top: 15px;
}

.api-key-item {
  background-color: var(--stats-item-bg);
  border-radius: var(--radius-lg);
  padding: 15px;
  box-shadow: var(--shadow-sm);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--card-border);
}

.api-key-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: var(--gradient-info);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.api-key-item:hover::before {
  opacity: 1;
}

.api-key-item:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
  border-color: var(--button-primary);
}

.api-key-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.api-key-name {
  font-weight: bold;
  color: var(--color-heading);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 50%;
  transition: all 0.3s ease;
}

.api-key-usage {
  display: flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}

.api-key-count {
  font-weight: bold;
  color: var(--button-primary);
  transition: all 0.3s ease;
}

.progress-container {
  width: 100%;
  height: 10px;
  background-color: var(--color-background-soft);
  border-radius: var(--radius-full);
  overflow: hidden;
  transition: all 0.3s ease;
  margin: 10px 0;
}

.progress-bar {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.5s ease, background-color 0.3s;
  position: relative;
  overflow: hidden;
}

.progress-bar::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transform: translateX(-100%);
  animation: progressShine 2s infinite;
}

@keyframes progressShine {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.progress-bar.low {
  background: var(--gradient-success);
}

.progress-bar.medium {
  background: var(--gradient-warning);
}

.progress-bar.high {
  background: var(--gradient-danger);
}

/* 模型统计样式 */
.model-stats-container {
  margin-top: 10px;
  border-top: 1px dashed var(--color-border);
  padding-top: 10px;
  transition: all 0.3s ease;
}

.model-stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
  margin-bottom: 8px;
  color: var(--color-heading);
  font-size: 14px;
  transition: all 0.3s ease;
  padding: 5px 8px;
  border-radius: var(--radius-md);
}

.model-stats-header:hover {
  background-color: var(--color-background-mute);
}

.model-stats-title {
  font-weight: 600;
}

.model-stats-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.model-stat-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 10px;
  background-color: var(--color-background-mute);
  border-radius: var(--radius-md);
  font-size: 13px;
  transition: all 0.3s ease;
  border: 1px solid transparent;
}

.model-stat-item:hover {
  transform: translateX(5px);
  box-shadow: var(--shadow-sm);
  border-color: var(--button-primary);
}

.model-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
}

.model-name {
  font-weight: 500;
  color: var(--color-heading);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  transition: all 0.3s ease;
}

.model-count {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--button-primary);
  font-weight: 600;
  transition: all 0.3s ease;
}

.model-usage-text {
  color: var(--color-text);
  font-weight: normal;
  font-size: 12px;
  transition: all 0.3s ease;
  opacity: 0.8;
}

.model-tokens {
  font-size: 12px;
  color: var(--color-text);
  opacity: 0.8;
  transition: all 0.3s ease;
}

.view-more-models {
  text-align: center;
  color: var(--button-primary);
  font-size: 12px;
  cursor: pointer;
  padding: 8px;
  margin-top: 5px;
  border-radius: var(--radius-md);
  background-color: rgba(79, 70, 229, 0.05);
  transition: all 0.3s ease;
  border: 1px dashed var(--button-primary);
}

.view-more-models:hover {
  background-color: rgba(79, 70, 229, 0.1);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

/* 折叠动画和UI优化 */
.section-title {
  color: var(--color-heading);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 10px;
  margin-bottom: 20px;
  transition: all 0.3s ease;
  position: relative;
  font-weight: 600;
  margin: 0;
}

.section-title::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 50px;
  height: 2px;
  background: var(--gradient-primary);
}

.fold-header {
  cursor: pointer;
  user-select: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.3s ease;
  border-radius: var(--radius-md);
  padding: 8px 12px;
  background-color: var(--color-background-mute);
  margin-bottom: 0;
  margin-right: 10px;
  flex: 1;
}

.fold-header:hover {
  background-color: var(--color-background-soft);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.fold-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.3s ease;
}

.fold-icon.rotated {
  transform: rotate(180deg);
}

.fold-content {
  overflow: hidden;
}

/* 折叠动画 */
.fold-enter-active,
.fold-leave-active {
  transition: all 0.3s ease;
  max-height: 1000px;
  opacity: 1;
  overflow: hidden;
}

.fold-enter-from,
.fold-leave-to {
  max-height: 0;
  opacity: 0;
  overflow: hidden;
}

/* 修改总token使用量样式 */
.total-tokens {
  margin-top: 6px;
  padding: 8px 12px;
  background-color: var(--color-background-mute);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.3s ease;
  border: 1px solid var(--card-border);
}

.total-tokens:hover {
  background-color: var(--color-background-soft);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
  border-color: var(--button-primary);
}

.total-tokens-label {
  font-size: 11px;
  color: var(--color-text);
  opacity: 0.8;
  white-space: nowrap;
  transition: all 0.3s ease;
}

.total-tokens-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--button-primary);
  transition: all 0.3s ease;
}

/* 分页控件样式 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 20px;
  gap: 15px;
}

.pagination-button {
  background-color: var(--button-secondary);
  color: var(--button-secondary-text);
  border: none;
  border-radius: var(--radius-md);
  padding: 8px 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 500;
}

.pagination-button:hover:not(:disabled) {
  background-color: var(--button-secondary-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.pagination-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-info {
  font-size: 14px;
  color: var(--color-text);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }
  
  .header-buttons {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    width: 100%;
  }
  
  .add-api-key-button, 
  .test-api-key-button, 
  .clear-invalid-keys-button, 
  .export-valid-keys-button {
    padding: 8px 12px;
    font-size: 12px;
    justify-content: center;
    min-height: 36px;
    gap: 6px;
  }
  
  .add-api-key-button svg, 
  .test-api-key-button svg, 
  .clear-invalid-keys-button svg, 
  .export-valid-keys-button svg {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
  }
  
  .api-key-stats-list {
    grid-template-columns: 1fr;
  }
  
  .api-key-item {
    padding: 10px;
  }
  
  .api-key-name {
    font-size: 13px;
    max-width: 100%;
    color: var(--button-primary);
  }
  
  .api-key-usage {
    font-size: 12px;
    gap: 5px;
  }
  
  .model-stats-container {
    margin-top: 10px;
  }
  
  .model-info {
    gap: 3px;
  }
  
  .total-tokens-label {
    color: var(--color-heading);
    opacity: 0.9;
  }
  
  .api-key-test-form,
  .clear-invalid-keys-form,
  .export-valid-keys-form {
    padding: 15px;
  }
  
  .form-title h4 {
    font-size: 14px;
  }
  
  .form-description {
    font-size: 12px;
  }
  
  .progress-text {
    font-size: 12px;
  }
  
  .exported-keys-list {
    max-height: 250px;
  }
  
  .exported-key-item {
    padding: 8px 10px;
  }
  
  .key-text {
    font-size: 12px;
  }
  
  .copy-key-button {
    min-width: 24px;
    height: 24px;
    padding: 3px;
  }
  
  .copy-all-button {
    padding: 5px 10px;
    font-size: 11px;
  }
}

/* 超小屏幕优化 */
@media (max-width: 480px) {
  .header-buttons {
    grid-template-columns: 1fr;
    gap: 6px;
  }
  
  .add-api-key-button, 
  .test-api-key-button, 
  .clear-invalid-keys-button, 
  .export-valid-keys-button {
    padding: 10px 12px;
    font-size: 13px;
    min-height: 40px;
    gap: 8px;
  }
  
  .add-api-key-button svg, 
  .test-api-key-button svg, 
  .clear-invalid-keys-button svg, 
  .export-valid-keys-button svg {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
  }
  
  .api-key-test-form,
  .clear-invalid-keys-form,
  .export-valid-keys-form {
    padding: 12px;
    margin-bottom: 15px;
  }
  
  .form-title h4 {
    font-size: 15px;
  }
  
  .form-description {
    font-size: 13px;
  }
  
  .form-actions {
    flex-direction: column;
    gap: 8px;
  }
  
  .submit-api-key,
  .cancel-api-key {
    width: 100%;
    padding: 10px;
    font-size: 14px;
  }
  
  .exported-keys-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .copy-all-button {
    align-self: flex-end;
  }
}

/* 极小屏幕优化 */
@media (max-width: 360px) {
  .header-buttons {
    gap: 4px;
  }
  
  .add-api-key-button, 
  .test-api-key-button, 
  .clear-invalid-keys-button, 
  .export-valid-keys-button {
    padding: 8px 10px;
    font-size: 12px;
    min-height: 36px;
    gap: 6px;
  }
  
  .add-api-key-button svg, 
  .test-api-key-button svg, 
  .clear-invalid-keys-button svg, 
  .export-valid-keys-button svg {
    width: 14px;
    height: 14px;
  }
  
  .api-key-test-form,
  .clear-invalid-keys-form,
  .export-valid-keys-form {
    padding: 10px;
  }
  
  .form-title h4 {
    font-size: 14px;
  }
  
  .form-description {
    font-size: 12px;
  }
  
  .submit-api-key,
  .cancel-api-key {
    padding: 8px;
    font-size: 13px;
  }
}

/* 在中等屏幕上显示为两列 */
@media (max-width: 992px) {
  .api-key-stats-list {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 在小屏幕上显示为一列 */
@media (max-width: 576px) {
  .api-key-stats-list {
    grid-template-columns: 1fr;
  }
}

/* API密钥输入表单样式 */
.api-key-input-form {
  background-color: var(--color-background-mute);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid var(--card-border);
  box-shadow: var(--shadow-md);
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-heading);
}

.api-key-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background-color: var(--color-background);
  color: var(--color-text);
  font-family: inherit;
  font-size: 14px;
  resize: vertical;
  transition: all 0.3s ease;
}

.api-key-textarea:focus {
  outline: none;
  border-color: var(--button-primary);
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.1);
}

.api-key-password {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background-color: var(--color-background);
  color: var(--color-text);
  font-family: inherit;
  font-size: 14px;
  transition: all 0.3s ease;
}

.api-key-password:focus {
  outline: none;
  border-color: var(--button-primary);
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.1);
}

.api-key-error {
  color: var(--color-danger);
  font-size: 14px;
  margin-bottom: 15px;
  padding: 10px;
  background-color: rgba(239, 68, 68, 0.1);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-danger);
}

.api-key-success {
  color: var(--color-success);
  font-size: 14px;
  margin-bottom: 15px;
  padding: 10px;
  background-color: rgba(34, 197, 94, 0.1);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-success);
}

.form-actions {
  display: flex;
  gap: 10px;
}

.submit-api-key {
  padding: 8px 20px;
  background-color: var(--button-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.submit-api-key:hover:not(:disabled) {
  background-color: var(--button-primary-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.submit-api-key:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cancel-api-key {
  padding: 8px 20px;
  background-color: var(--button-secondary);
  color: var(--button-secondary-text);
  border: none;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.cancel-api-key:hover:not(:disabled) {
  background-color: var(--button-secondary-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.cancel-api-key:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style> 