<template>
  <div class="backend-switcher">
    <div class="current-backend">
      <div class="status-indicator" :class="{ connected: activeBackend?.isConnected }"></div>
      <select 
        v-model="selectedBackendId" 
        @change="switchToBackend"
        class="backend-select"
      >
        <option 
          v-for="backend in backendStore.backends" 
          :key="backend.id"
          :value="backend.id"
        >
          {{ backend.name }} {{ backend.isConnected ? '●' : '○' }}
        </option>
      </select>
    </div>
    
    <div class="actions">
      <button 
        @click="testCurrentConnection"
        :disabled="testing"
        class="btn btn-sm btn-outline"
        :title="testing ? '测试中...' : '测试当前连接'"
      >
        <span class="icon">{{ testing ? '⟳' : '🔄' }}</span>
      </button>
      
      <button 
        @click="$emit('openManager')"
        class="btn btn-sm btn-outline"
        title="管理后端实例"
      >
        <span class="icon">⚙️</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useBackendStore } from '@/stores/backend'

const emit = defineEmits(['openManager'])

const backendStore = useBackendStore()
const testing = ref(false)

// 当前选择的后端ID
const selectedBackendId = ref(backendStore.activeBackendId)

// 当前活跃的后端
const activeBackend = computed(() => backendStore.activeBackend)

// 监听活跃后端变化
watch(() => backendStore.activeBackendId, (newId) => {
  selectedBackendId.value = newId
})

// 切换后端
function switchToBackend() {
  if (selectedBackendId.value !== backendStore.activeBackendId) {
    backendStore.switchBackend(selectedBackendId.value)
    backendStore.saveToStorage()
  }
}

// 测试当前连接
async function testCurrentConnection() {
  if (!activeBackend.value) return
  
  testing.value = true
  try {
    await backendStore.testBackendConnection(activeBackend.value.id)
  } catch (error) {
    console.error('测试连接失败:', error)
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.backend-switcher {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.current-backend {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #dc3545;
  transition: background-color 0.3s ease;
}

.status-indicator.connected {
  background: #28a745;
}

.backend-select {
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 14px;
  background: white;
  cursor: pointer;
  min-width: 150px;
}

.backend-select:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.1);
}

.actions {
  display: flex;
  gap: 6px;
}

.btn {
  padding: 4px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn:hover:not(:disabled) {
  border-color: #007bff;
  background: #f8f9ff;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-outline {
  color: #666;
}

.btn-sm {
  min-width: 28px;
  height: 28px;
}

.icon {
  font-size: 12px;
  user-select: none;
}

@media (max-width: 768px) {
  .backend-switcher {
    padding: 6px 8px;
  }
  
  .backend-select {
    min-width: 120px;
    font-size: 12px;
  }
}
</style>