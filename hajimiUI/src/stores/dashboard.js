import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useDashboardStore = defineStore('dashboard', () => {
  // 状态
  const status = ref({
    keyCount: 0,
    modelCount: 0,
    retryCount: 0,
    last24hCalls: 0,
    hourlyCalls: 0,
    minuteCalls: 0
  })

  // 添加图表相关的时间序列数据
  const timeSeriesData = ref({
    calls: [],  // API调用时间序列
    tokens: []  // Token使用时间序列
  })

  const config = ref({
    maxRequestsPerMinute: 0,
    maxRequestsPerDayPerIp: 0,
    currentTime: '',
    fakeStreaming: false,
    fakeStreamingInterval: 0,
    randomString: false,
    localVersion: '',
    remoteVersion: '',
    hasUpdate: false,
    concurrentRequests: 0,
    increaseConcurrentOnFailure: 0,
    maxConcurrentRequests: 0,
    maxRetryNum: 0,
    searchPrompt: '',
    maxEmptyResponses: 0
  })

  const apiKeyStats = ref([])
  const logs = ref([])
  const isRefreshing = ref(false)
  const isConfigLoaded = ref(false)
  
  // 添加模型相关状态
  const selectedModel = ref('all')
  const availableModels = ref([])
  
  // 夜间模式状态
  const isDarkMode = ref(localStorage.getItem('darkMode') === 'true')
  
  // 监听夜间模式变化，保存到localStorage
  watch(isDarkMode, (newValue) => {
    localStorage.setItem('darkMode', newValue)
    applyDarkMode(newValue)
  })
  
  // 应用夜间模式
  function applyDarkMode(isDark) {
    if (isDark) {
      document.documentElement.classList.add('dark-mode')
    } else {
      document.documentElement.classList.remove('dark-mode')
    }
  }
  
  // 初始应用夜间模式
  applyDarkMode(isDarkMode.value)

  // 获取仪表盘数据
  async function fetchDashboardData() {
    if (isRefreshing.value) return // 防止重复请求
    
    isRefreshing.value = true
    try {
      const response = await fetch('/api/dashboard-data')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      updateDashboardData(data)
    } catch (error) {
      console.error('获取数据失败:', error)
    } finally {
      isRefreshing.value = false
    }
  }

  // 更新仪表盘数据
  function updateDashboardData(data) {
    // 更新状态数据
    status.value = {
      keyCount: data.key_count || 0,
      modelCount: data.model_count || 0,
      retryCount: data.retry_count || 0,
      last24hCalls: data.last_24h_calls || 0,
      hourlyCalls: data.hourly_calls || 0,
      minuteCalls: data.minute_calls || 0,
      enableVertex: data.enable_vertex || false
    }

    // 更新时间序列数据
    if (data.calls_time_series) {
      timeSeriesData.value.calls = data.calls_time_series
    }
    
    if (data.tokens_time_series) {
      timeSeriesData.value.tokens = data.tokens_time_series
    }

    // 更新配置数据
    config.value = {
      maxRequestsPerMinute: data.max_requests_per_minute || 0,
      maxRequestsPerDayPerIp: data.max_requests_per_day_per_ip || 0,
      currentTime: data.current_time || '',
      fakeStreaming: data.fake_streaming || false,
      fakeStreamingInterval: data.fake_streaming_interval || 0,
      randomString: data.random_string || false,
      randomStringLength: data.random_string_length || 0,
      searchMode: data.search_mode || false,
      searchPrompt: data.search_prompt || '',
      localVersion: data.local_version || '',
      remoteVersion: data.remote_version || '',
      hasUpdate: data.has_update || false,
      concurrentRequests: data.concurrent_requests || 0,
      increaseConcurrentOnFailure: data.increase_concurrent_on_failure || 0,
      maxConcurrentRequests: data.max_concurrent_requests || 0,
      enableVertex: data.enable_vertex || false,
      enableVertexExpress: data.enable_vertex_express || false,
      vertexExpressApiKey: data.vertex_express_api_key || false,
      maxRetryNum: data.max_retry_num || 0,
      maxEmptyResponses: data.max_empty_responses || 0
    }

    // 更新API密钥统计
    if (data.api_key_stats) {
      apiKeyStats.value = data.api_key_stats.map(stat => ({
        ...stat,
        // 确保model_stats的每个模型都有calls和tokens两个指标
        model_stats: Object.entries(stat.model_stats || {}).reduce((acc, [model, data]) => {
          acc[model] = {
            calls: typeof data === 'object' ? data.calls : data, // 兼容旧格式
            tokens: typeof data === 'object' ? data.tokens : 0
          }
          return acc
        }, {})
      }))
      
      // 提取所有可用的模型
      const models = new Set(['all']) // 始终包含"全部"选项
      data.api_key_stats.forEach(stat => {
        if (stat.model_stats) {
          Object.keys(stat.model_stats).forEach(model => {
            models.add(model)
          })
        }
      })
      availableModels.value = Array.from(models)
      
      // 如果当前选择的模型不在可用模型列表中，重置为"all"
      if (!availableModels.value.includes(selectedModel.value)) {
        selectedModel.value = 'all'
      }
    }

    // 更新日志
    if (data.logs) {
      logs.value = data.logs
    }

    isConfigLoaded.value = true
  }
  
  // 设置选择的模型
  function setSelectedModel(model) {
    selectedModel.value = model
  }

  // 切换夜间模式
  function toggleDarkMode() {
    isDarkMode.value = !isDarkMode.value
  }

  // 切换Vertex AI配置
  async function toggleVertex() {
    try {
      const newValue = !config.value.enableVertex
      await updateConfig('enableVertex', newValue, '123') // 使用默认密码
      // 更新本地状态
      config.value.enableVertex = newValue
    } catch (error) {
      console.error('切换Vertex AI失败:', error)
    }
  }

  // 更新配置项
  async function updateConfig(key, value, password) {
    try {
      // 将驼峰命名转换为下划线命名
      const snakeCaseKey = key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
      
      const response = await fetch('/api/update-config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          key: snakeCaseKey,
          value,
          password
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '更新配置失败')
      }
      
      const data = await response.json()
      return data
    } catch (error) {
      console.error('更新配置失败:', error)
      throw error
    }
  }

  return {
    status,
    config,
    apiKeyStats,
    logs,
    isRefreshing,
    timeSeriesData,  // 导出时间序列数据
    fetchDashboardData,
    selectedModel,
    availableModels,
    setSelectedModel,
    isDarkMode,
    toggleDarkMode,
    updateConfig,
    toggleVertex,
    isConfigLoaded
  }
})