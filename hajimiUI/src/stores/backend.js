import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useBackendStore = defineStore('backend', () => {
  // 后端实例列表
  const backends = ref([
    {
      id: 'local',
      name: '本地实例',
      baseUrl: window.location.origin,
      password: '',
      isActive: true,
      isConnected: false,
      lastConnected: null,
      description: '当前页面的后端实例'
    }
  ])

  // 当前活跃的后端实例
  const activeBackendId = ref('local')

  // 获取当前活跃的后端实例
  const activeBackend = computed(() => {
    return backends.value.find(backend => backend.id === activeBackendId.value)
  })

  // 获取连接的后端数量
  const connectedBackendsCount = computed(() => {
    return backends.value.filter(backend => backend.isConnected).length
  })

  // 添加后端实例
  function addBackend(backend) {
    const newBackend = {
      id: `backend_${Date.now()}`,
      name: backend.name || '未命名实例',
      baseUrl: backend.baseUrl,
      password: backend.password || '',
      isActive: false,
      isConnected: false,
      lastConnected: null,
      description: backend.description || ''
    }
    
    backends.value.push(newBackend)
    return newBackend
  }

  // 删除后端实例
  function removeBackend(backendId) {
    if (backendId === 'local') {
      throw new Error('不能删除本地实例')
    }
    
    const index = backends.value.findIndex(backend => backend.id === backendId)
    if (index > -1) {
      backends.value.splice(index, 1)
      
      // 如果删除的是当前活跃实例，切换到本地实例
      if (activeBackendId.value === backendId) {
        activeBackendId.value = 'local'
      }
    }
  }

  // 更新后端实例
  function updateBackend(backendId, updates) {
    const backend = backends.value.find(b => b.id === backendId)
    if (backend) {
      Object.assign(backend, updates)
    }
  }

  // 切换活跃的后端实例
  function switchBackend(backendId) {
    const backend = backends.value.find(b => b.id === backendId)
    if (backend) {
      // 取消其他实例的活跃状态
      backends.value.forEach(b => { b.isActive = false })
      
      // 设置新的活跃实例
      backend.isActive = true
      activeBackendId.value = backendId
      
      console.log(`已切换到后端实例: ${backend.name}`)
      return true
    }
    return false
  }

  // 测试后端连接
  async function testBackendConnection(backendId) {
    const backend = backends.value.find(b => b.id === backendId)
    if (!backend) {
      throw new Error('后端实例不存在')
    }

    try {
      const response = await fetch(`${backend.baseUrl}/api/dashboard-data`, {
        method: 'GET',
        headers: {
          'Authorization': backend.password ? `Bearer ${backend.password}` : '',
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        backend.isConnected = true
        backend.lastConnected = new Date().toISOString()
        return { success: true, message: '连接成功' }
      } else {
        backend.isConnected = false
        return { success: false, message: `连接失败: ${response.status}` }
      }
    } catch (error) {
      backend.isConnected = false
      return { success: false, message: `连接错误: ${error.message}` }
    }
  }

  // 批量测试所有后端连接
  async function testAllConnections() {
    const results = await Promise.allSettled(
      backends.value.map(backend => testBackendConnection(backend.id))
    )
    
    return results.map((result, index) => ({
      backendId: backends.value[index].id,
      ...result.value
    }))
  }

  // 构造 API 请求 URL
  function buildApiUrl(endpoint) {
    const backend = activeBackend.value
    if (!backend) {
      throw new Error('没有活跃的后端实例')
    }
    
    const baseUrl = backend.baseUrl.replace(/\/$/, '') // 移除末尾斜杠
    const cleanEndpoint = endpoint.replace(/^\//, '') // 移除开头斜杠
    
    return `${baseUrl}/${cleanEndpoint}`
  }

  // 获取当前后端的认证头
  function getAuthHeaders() {
    const backend = activeBackend.value
    const headers = {
      'Content-Type': 'application/json'
    }
    
    if (backend && backend.password) {
      headers['Authorization'] = `Bearer ${backend.password}`
    }
    
    return headers
  }

  // 发起 API 请求（带自动重试）
  async function apiRequest(endpoint, options = {}) {
    const url = buildApiUrl(endpoint)
    const headers = { ...getAuthHeaders(), ...options.headers }
    
    try {
      const response = await fetch(url, {
        ...options,
        headers
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      // 更新连接状态
      if (activeBackend.value) {
        activeBackend.value.isConnected = true
        activeBackend.value.lastConnected = new Date().toISOString()
      }
      
      return response
    } catch (error) {
      // 更新连接状态
      if (activeBackend.value) {
        activeBackend.value.isConnected = false
      }
      
      console.error(`API请求失败 [${activeBackend.value?.name}]:`, error)
      throw error
    }
  }

  // 保存配置到 localStorage
  function saveToStorage() {
    const data = {
      backends: backends.value,
      activeBackendId: activeBackendId.value
    }
    localStorage.setItem('hajimi_backends', JSON.stringify(data))
  }

  // 从 localStorage 加载配置
  function loadFromStorage() {
    try {
      const stored = localStorage.getItem('hajimi_backends')
      if (stored) {
        const data = JSON.parse(stored)
        
        if (data.backends && Array.isArray(data.backends)) {
          // 确保本地实例始终存在
          const hasLocal = data.backends.some(b => b.id === 'local')
          if (!hasLocal) {
            data.backends.unshift({
              id: 'local',
              name: '本地实例',
              baseUrl: window.location.origin,
              password: '',
              isActive: false,
              isConnected: false,
              lastConnected: null,
              description: '当前页面的后端实例'
            })
          }
          
          backends.value = data.backends
        }
        
        if (data.activeBackendId) {
          activeBackendId.value = data.activeBackendId
          switchBackend(data.activeBackendId)
        }
      }
    } catch (error) {
      console.error('加载后端配置失败:', error)
    }
  }

  // 重置为默认配置
  function resetToDefault() {
    backends.value = [
      {
        id: 'local',
        name: '本地实例',
        baseUrl: window.location.origin,
        password: '',
        isActive: true,
        isConnected: false,
        lastConnected: null,
        description: '当前页面的后端实例'
      }
    ]
    activeBackendId.value = 'local'
    saveToStorage()
  }

  // 初始化时加载配置
  loadFromStorage()

  return {
    backends,
    activeBackendId,
    activeBackend,
    connectedBackendsCount,
    addBackend,
    removeBackend,
    updateBackend,
    switchBackend,
    testBackendConnection,
    testAllConnections,
    buildApiUrl,
    getAuthHeaders,
    apiRequest,
    saveToStorage,
    loadFromStorage,
    resetToDefault
  }
})