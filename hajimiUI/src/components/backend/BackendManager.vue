<template>
  <div class="backend-manager">
    <div class="header">
      <h3>后端实例管理</h3>
      <button @click="showAddModal = true" class="btn btn-primary">
        <span class="icon">+</span> 添加实例
      </button>
    </div>

    <div class="stats">
      <div class="stat-item">
        <span class="label">总实例数：</span>
        <span class="value">{{ backendStore.backends.length }}</span>
      </div>
      <div class="stat-item">
        <span class="label">已连接：</span>
        <span class="value connected">{{ backendStore.connectedBackendsCount }}</span>
      </div>
      <div class="stat-item">
        <span class="label">当前活跃：</span>
        <span class="value active">{{ backendStore.activeBackend?.name || '无' }}</span>
      </div>
    </div>

    <div class="backend-list">
      <div
        v-for="backend in backendStore.backends"
        :key="backend.id"
        class="backend-item"
        :class="{
          active: backend.isActive,
          connected: backend.isConnected,
          disconnected: !backend.isConnected
        }"
      >
        <div class="backend-info">
          <div class="name-row">
            <h4>{{ backend.name }}</h4>
            <div class="badges">
              <span v-if="backend.isActive" class="badge active">活跃</span>
              <span v-if="backend.isConnected" class="badge connected">已连接</span>
              <span v-else class="badge disconnected">未连接</span>
            </div>
          </div>
          
          <div class="details">
            <p class="url">{{ backend.baseUrl }}</p>
            <p v-if="backend.description" class="description">{{ backend.description }}</p>
            <p v-if="backend.lastConnected" class="last-connected">
              最后连接：{{ formatTime(backend.lastConnected) }}
            </p>
          </div>
        </div>

        <div class="backend-actions">
          <button
            @click="switchBackend(backend.id)"
            :disabled="backend.isActive"
            class="btn btn-sm"
            :class="backend.isActive ? 'btn-secondary' : 'btn-primary'"
          >
            {{ backend.isActive ? '当前活跃' : '切换' }}
          </button>
          
          <button
            @click="testConnection(backend.id)"
            :disabled="testing[backend.id]"
            class="btn btn-sm btn-outline"
          >
            {{ testing[backend.id] ? '测试中...' : '测试连接' }}
          </button>
          
          <button
            @click="editBackend(backend)"
            class="btn btn-sm btn-outline"
          >
            编辑
          </button>
          
          <button
            v-if="backend.id !== 'local'"
            @click="confirmDelete(backend)"
            class="btn btn-sm btn-danger"
          >
            删除
          </button>
        </div>
      </div>
    </div>

    <div class="actions">
      <button @click="testAllConnections" :disabled="testingAll" class="btn btn-outline">
        {{ testingAll ? '测试中...' : '测试所有连接' }}
      </button>
      <button @click="refreshAll" class="btn btn-outline">
        刷新状态
      </button>
    </div>

    <!-- 添加/编辑模态框 -->
    <div v-if="showAddModal || showEditModal" class="modal-overlay" @click="closeModal">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h4>{{ showAddModal ? '添加后端实例' : '编辑后端实例' }}</h4>
          <button @click="closeModal" class="close-btn">×</button>
        </div>
        
        <div class="modal-body">
          <div class="form-group">
            <label>实例名称</label>
            <input
              v-model="formData.name"
              type="text"
              placeholder="例如：生产服务器"
              class="form-control"
            />
          </div>
          
          <div class="form-group">
            <label>服务器地址</label>
            <input
              v-model="formData.baseUrl"
              type="url"
              placeholder="https://your-hajimi-instance.com"
              class="form-control"
            />
          </div>
          
          <div class="form-group">
            <label>访问密码（可选）</label>
            <input
              v-model="formData.password"
              type="password"
              placeholder="留空如果不需要密码"
              class="form-control"
            />
          </div>
          
          <div class="form-group">
            <label>描述（可选）</label>
            <textarea
              v-model="formData.description"
              placeholder="描述这个实例的用途"
              class="form-control"
              rows="3"
            ></textarea>
          </div>
        </div>
        
        <div class="modal-footer">
          <button @click="closeModal" class="btn btn-secondary">取消</button>
          <button @click="saveBackend" class="btn btn-primary">
            {{ showAddModal ? '添加' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 删除确认模态框 -->
    <div v-if="showDeleteModal" class="modal-overlay" @click="showDeleteModal = false">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h4>确认删除</h4>
          <button @click="showDeleteModal = false" class="close-btn">×</button>
        </div>
        
        <div class="modal-body">
          <p>确定要删除后端实例 "{{ deleteTarget?.name }}" 吗？</p>
          <p class="warning">此操作不可恢复。</p>
        </div>
        
        <div class="modal-footer">
          <button @click="showDeleteModal = false" class="btn btn-secondary">取消</button>
          <button @click="deleteBackend" class="btn btn-danger">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useBackendStore } from '@/stores/backend'

const backendStore = useBackendStore()

// 状态
const showAddModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const testing = reactive({})
const testingAll = ref(false)
const editingBackend = ref(null)
const deleteTarget = ref(null)

// 表单数据
const formData = reactive({
  name: '',
  baseUrl: '',
  password: '',
  description: ''
})

// 切换后端实例
function switchBackend(backendId) {
  if (backendStore.switchBackend(backendId)) {
    backendStore.saveToStorage()
  }
}

// 测试单个连接
async function testConnection(backendId) {
  testing[backendId] = true
  try {
    const result = await backendStore.testBackendConnection(backendId)
    if (result.success) {
      console.log(`连接测试成功: ${result.message}`)
    } else {
      console.error(`连接测试失败: ${result.message}`)
    }
  } catch (error) {
    console.error('连接测试出错:', error)
  } finally {
    testing[backendId] = false
  }
}

// 测试所有连接
async function testAllConnections() {
  testingAll.value = true
  try {
    const results = await backendStore.testAllConnections()
    console.log('所有连接测试完成:', results)
  } catch (error) {
    console.error('批量测试连接出错:', error)
  } finally {
    testingAll.value = false
  }
}

// 刷新所有状态
function refreshAll() {
  testAllConnections()
}

// 编辑后端
function editBackend(backend) {
  editingBackend.value = backend
  formData.name = backend.name
  formData.baseUrl = backend.baseUrl
  formData.password = backend.password
  formData.description = backend.description
  showEditModal.value = true
}

// 确认删除
function confirmDelete(backend) {
  deleteTarget.value = backend
  showDeleteModal.value = true
}

// 删除后端
function deleteBackend() {
  if (deleteTarget.value) {
    backendStore.removeBackend(deleteTarget.value.id)
    backendStore.saveToStorage()
    showDeleteModal.value = false
    deleteTarget.value = null
  }
}

// 保存后端
function saveBackend() {
  if (!formData.name.trim() || !formData.baseUrl.trim()) {
    alert('请填写实例名称和服务器地址')
    return
  }

  if (showAddModal.value) {
    // 添加新实例
    backendStore.addBackend({
      name: formData.name.trim(),
      baseUrl: formData.baseUrl.trim(),
      password: formData.password.trim(),
      description: formData.description.trim()
    })
  } else if (showEditModal.value && editingBackend.value) {
    // 更新现有实例
    backendStore.updateBackend(editingBackend.value.id, {
      name: formData.name.trim(),
      baseUrl: formData.baseUrl.trim(),
      password: formData.password.trim(),
      description: formData.description.trim()
    })
  }

  backendStore.saveToStorage()
  closeModal()
}

// 关闭模态框
function closeModal() {
  showAddModal.value = false
  showEditModal.value = false
  editingBackend.value = null
  
  // 重置表单
  formData.name = ''
  formData.baseUrl = ''
  formData.password = ''
  formData.description = ''
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
.backend-manager {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h3 {
  margin: 0;
  color: #333;
}

.stats {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.stat-item .label {
  font-size: 12px;
  color: #666;
}

.stat-item .value {
  font-weight: bold;
  font-size: 16px;
}

.stat-item .value.connected {
  color: #28a745;
}

.stat-item .value.active {
  color: #007bff;
}

.backend-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 20px;
}

.backend-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px;
  border: 2px solid #e9ecef;
  border-radius: 10px;
  background: white;
  transition: all 0.3s ease;
}

.backend-item.active {
  border-color: #007bff;
  background: #f8f9ff;
}

.backend-item.connected:not(.active) {
  border-color: #28a745;
}

.backend-item.disconnected:not(.active) {
  border-color: #dc3545;
  background: #fff5f5;
}

.backend-info {
  flex: 1;
  min-width: 0;
}

.name-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.name-row h4 {
  margin: 0;
  color: #333;
}

.badges {
  display: flex;
  gap: 8px;
}

.badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
  text-transform: uppercase;
}

.badge.active {
  background: #007bff;
  color: white;
}

.badge.connected {
  background: #28a745;
  color: white;
}

.badge.disconnected {
  background: #dc3545;
  color: white;
}

.details p {
  margin: 5px 0;
  font-size: 14px;
}

.details .url {
  color: #007bff;
  font-family: monospace;
}

.details .description {
  color: #666;
}

.details .last-connected {
  color: #999;
  font-size: 12px;
}

.backend-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-left: 20px;
}

.actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
}

/* 按钮样式 */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
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

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #545b62;
}

.btn-outline {
  background: transparent;
  color: #007bff;
  border: 1px solid #007bff;
}

.btn-outline:hover:not(:disabled) {
  background: #007bff;
  color: white;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #c82333;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

/* 模态框样式 */
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
  border-radius: 10px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow: auto;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e9ecef;
}

.modal-header h4 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #333;
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #e9ecef;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #333;
}

.form-control {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-control:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

.warning {
  color: #dc3545;
  font-weight: 500;
}

.icon {
  font-size: 16px;
}

@media (max-width: 768px) {
  .backend-item {
    flex-direction: column;
    gap: 15px;
  }
  
  .backend-actions {
    flex-direction: row;
    margin-left: 0;
    flex-wrap: wrap;
  }
  
  .name-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .stats {
    flex-direction: column;
    gap: 10px;
  }
}
</style>