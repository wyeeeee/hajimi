<template>
  <div class="backend-view">
    <div class="header">
      <div class="title-section">
        <h1>后端实例管理</h1>
        <p class="subtitle">管理和切换不同的 Hajimi 后端实例</p>
      </div>
      
      <BackendSwitcher @openManager="scrollToManager" />
    </div>

    <div class="content">
      <!-- 概览卡片 -->
      <div class="overview-cards">
        <div class="card">
          <div class="card-icon">🏠</div>
          <div class="card-content">
            <h3>{{ backendStore.backends.length }}</h3>
            <p>总实例数</p>
          </div>
        </div>
        
        <div class="card">
          <div class="card-icon">✅</div>
          <div class="card-content">
            <h3>{{ backendStore.connectedBackendsCount }}</h3>
            <p>已连接</p>
          </div>
        </div>
        
        <div class="card">
          <div class="card-icon">⚡</div>
          <div class="card-content">
            <h3>{{ backendStore.activeBackend?.name || '无' }}</h3>
            <p>当前活跃</p>
          </div>
        </div>
        
        <div class="card">
          <div class="card-icon">🔄</div>
          <div class="card-content">
            <h3>{{ formatTime(backendStore.activeBackend?.lastConnected) || '从未' }}</h3>
            <p>最后连接</p>
          </div>
        </div>
      </div>

      <!-- 快速操作 -->
      <div class="quick-actions">
        <h2>快速操作</h2>
        <div class="action-buttons">
          <button @click="testAllConnections" :disabled="testingAll" class="btn btn-primary">
            <span class="icon">🔍</span>
            {{ testingAll ? '测试中...' : '测试所有连接' }}
          </button>
          
          <button @click="showAddModal = true" class="btn btn-success">
            <span class="icon">➕</span>
            添加新实例
          </button>
          
          <button @click="exportConfig" class="btn btn-outline">
            <span class="icon">📤</span>
            导出配置
          </button>
          
          <button @click="importConfig" class="btn btn-outline">
            <span class="icon">📥</span>
            导入配置
          </button>
          
          <button @click="showUserGuide" class="btn btn-outline">
            <span class="icon">❓</span>
            使用指南
          </button>
        </div>
      </div>

      <!-- 后端管理器 -->
      <div ref="managerRef">
        <BackendManager />
      </div>
    </div>

    <!-- 添加实例快速模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click="closeAddModal">
      <div class="modal quick-add-modal" @click.stop>
        <div class="modal-header">
          <h4>快速添加后端实例</h4>
          <button @click="closeAddModal" class="close-btn">×</button>
        </div>
        
        <div class="modal-body">
          <div class="preset-buttons">
            <button 
              v-for="preset in presets" 
              :key="preset.id"
              @click="usePreset(preset)"
              class="preset-btn"
            >
              <div class="preset-icon">{{ preset.icon }}</div>
              <div class="preset-info">
                <h5>{{ preset.name }}</h5>
                <p>{{ preset.description }}</p>
              </div>
            </button>
          </div>
          
          <div class="divider">或手动添加</div>
          
          <div class="form-group">
            <label>服务器地址</label>
            <input
              v-model="quickAddUrl"
              type="url"
              placeholder="https://your-hajimi-instance.com"
              class="form-control"
              @keyup.enter="quickAddInstance"
            />
          </div>
        </div>
        
        <div class="modal-footer">
          <button @click="closeAddModal" class="btn btn-secondary">取消</button>
          <button 
            @click="quickAddInstance" 
            :disabled="!quickAddUrl.trim()"
            class="btn btn-primary"
          >
            添加
          </button>
        </div>
      </div>
    </div>

    <!-- 隐藏的文件输入 -->
    <input
      ref="fileInput"
      type="file"
      accept=".json"
      style="display: none"
      @change="handleFileImport"
    />

    <!-- 用户指南 -->
    <UserGuide ref="userGuideRef" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useBackendStore } from '@/stores/backend'
import BackendManager from '@/components/backend/BackendManager.vue'
import BackendSwitcher from '@/components/backend/BackendSwitcher.vue'
import UserGuide from '@/components/backend/UserGuide.vue'

const backendStore = useBackendStore()

// 状态
const testingAll = ref(false)
const showAddModal = ref(false)
const quickAddUrl = ref('')
const managerRef = ref(null)
const fileInput = ref(null)
const userGuideRef = ref(null)

// 预设配置
const presets = [
  {
    id: 'localhost',
    name: '本地开发',
    icon: '🏠',
    description: '本地开发服务器 (localhost:7860)',
    baseUrl: 'http://localhost:7860'
  },
  {
    id: 'production',
    name: '生产服务器',
    icon: '🚀',
    description: '生产环境服务器',
    baseUrl: 'https://'
  },
  {
    id: 'staging',
    name: '测试服务器',
    icon: '🧪',
    description: '测试环境服务器',
    baseUrl: 'https://'
  }
]

// 测试所有连接
async function testAllConnections() {
  testingAll.value = true
  try {
    await backendStore.testAllConnections()
  } catch (error) {
    console.error('批量测试失败:', error)
  } finally {
    testingAll.value = false
  }
}

// 使用预设
function usePreset(preset) {
  if (preset.id === 'localhost') {
    quickAddUrl.value = preset.baseUrl
  } else {
    quickAddUrl.value = preset.baseUrl
  }
}

// 快速添加实例
function quickAddInstance() {
  if (!quickAddUrl.value.trim()) return
  
  try {
    const url = new URL(quickAddUrl.value)
    const name = url.hostname
    
    backendStore.addBackend({
      name: name,
      baseUrl: quickAddUrl.value.trim(),
      password: '',
      description: `通过快速添加创建: ${url.hostname}`
    })
    
    backendStore.saveToStorage()
    closeAddModal()
  } catch (error) {
    alert('请输入有效的 URL 地址')
  }
}

// 关闭添加模态框
function closeAddModal() {
  showAddModal.value = false
  quickAddUrl.value = ''
}

// 滚动到管理器
function scrollToManager() {
  if (managerRef.value) {
    managerRef.value.scrollIntoView({ behavior: 'smooth' })
  }
}

// 导出配置
function exportConfig() {
  const config = {
    backends: backendStore.backends,
    activeBackendId: backendStore.activeBackendId,
    exportTime: new Date().toISOString()
  }
  
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `hajimi-backends-${new Date().toISOString().split('T')[0]}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// 导入配置
function importConfig() {
  fileInput.value?.click()
}

// 处理文件导入
function handleFileImport(event) {
  const file = event.target.files[0]
  if (!file) return
  
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const config = JSON.parse(e.target.result)
      
      if (config.backends && Array.isArray(config.backends)) {
        // 合并配置，保留本地实例
        const localBackend = backendStore.backends.find(b => b.id === 'local')
        const importedBackends = config.backends.filter(b => b.id !== 'local')
        
        backendStore.backends.splice(0, backendStore.backends.length)
        if (localBackend) {
          backendStore.backends.push(localBackend)
        }
        backendStore.backends.push(...importedBackends)
        
        backendStore.saveToStorage()
        alert(`成功导入 ${importedBackends.length} 个后端实例`)
      } else {
        alert('无效的配置文件格式')
      }
    } catch (error) {
      alert('配置文件解析失败: ' + error.message)
    }
  }
  reader.readAsText(file)
  
  // 清空文件输入
  event.target.value = ''
}

// 显示用户指南
function showUserGuide() {
  userGuideRef.value?.show()
}

// 格式化时间
function formatTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN')
}

// 初始化
onMounted(() => {
  testAllConnections()
})
</script>

<style scoped>
.backend-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  min-height: 100vh;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e9ecef;
}

.title-section h1 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 28px;
  font-weight: 600;
}

.subtitle {
  margin: 0;
  color: #666;
  font-size: 16px;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid #f0f0f0;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
}

.card-icon {
  font-size: 24px;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  border-radius: 10px;
}

.card-content h3 {
  margin: 0 0 4px 0;
  font-size: 24px;
  font-weight: 600;
  color: #333;
}

.card-content p {
  margin: 0;
  font-size: 14px;
  color: #666;
}

.quick-actions h2 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 20px;
}

.action-buttons {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.btn {
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0056b3;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #1e7e34;
}

.btn-outline {
  background: transparent;
  color: #666;
  border: 1px solid #ddd;
}

.btn-outline:hover:not(:disabled) {
  background: #f8f9fa;
  border-color: #007bff;
  color: #007bff;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #545b62;
}

.icon {
  font-size: 16px;
}

/* 快速添加模态框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow: auto;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.quick-add-modal {
  max-width: 600px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h4 {
  margin: 0;
  color: #333;
  font-size: 18px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
}

.close-btn:hover {
  background: #f8f9fa;
  color: #333;
}

.modal-body {
  padding: 24px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 24px;
  border-top: 1px solid #e9ecef;
}

.preset-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.preset-btn {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
  width: 100%;
}

.preset-btn:hover {
  border-color: #007bff;
  background: #f8f9ff;
}

.preset-icon {
  font-size: 24px;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  border-radius: 8px;
}

.preset-info h5 {
  margin: 0 0 4px 0;
  color: #333;
  font-size: 16px;
}

.preset-info p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.divider {
  text-align: center;
  color: #666;
  font-size: 14px;
  margin: 24px 0;
  position: relative;
}

.divider::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: #e9ecef;
  z-index: 0;
}

.divider span {
  background: white;
  padding: 0 16px;
  position: relative;
  z-index: 1;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
  font-size: 14px;
}

.form-control {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.form-control:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

@media (max-width: 768px) {
  .backend-view {
    padding: 16px;
  }
  
  .header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .overview-cards {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
  }
  
  .card {
    padding: 16px;
    gap: 12px;
  }
  
  .card-icon {
    font-size: 20px;
    width: 40px;
    height: 40px;
  }
  
  .card-content h3 {
    font-size: 20px;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .btn {
    justify-content: center;
  }
}
</style>