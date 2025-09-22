<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useDashboardStore } from '../../../stores/dashboard'

const dashboardStore = useDashboardStore()
const showModelsModal = ref(false)

// 获取并格式化模型列表 - 直接从store获取
const modelsList = computed(() => {
  try {
    const models = dashboardStore.availableModels || []
  
  // 分类模型
  const standardModels = []
  const searchModels = []
  
  models.forEach(model => {
    if (model === 'all') return // 跳过 'all' 选项
    
    // 格式化模型名称（移除 "models/" 前缀）
    const formattedName = model.replace('models/', '')
    
    if (model.endsWith('-search')) {
      searchModels.push(formattedName)
    } else {
      standardModels.push(formattedName)
    }
  })
  
    return {
      standard: standardModels,
      search: searchModels,
      total: standardModels.length + searchModels.length
    }
  } catch (error) {
    return {
      standard: [],
      search: [],
      total: 0
    }
  }
})

// ESC 键关闭弹窗
const handleEscKey = (e) => {
  if (e.key === 'Escape' && showModelsModal.value) {
    showModelsModal.value = false
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleEscKey)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscKey)
})

// 打开模型弹窗
const openModelsModal = () => {
  showModelsModal.value = true
}

// 关闭模型弹窗
const closeModelsModal = () => {
  showModelsModal.value = false
}
</script>

<template>
  <div class="stats-grid" v-if="!dashboardStore.status.enableVertex">
    <div class="stat-card">
      <div class="stat-value">{{ dashboardStore.status.keyCount }}</div>
      <div class="stat-label">可用密钥数量</div>
    </div>
    <div class="stat-card clickable" @click="openModelsModal">
      <div class="stat-value">{{ dashboardStore.status.modelCount }}</div>
      <div class="stat-label">
        可用模型数量
        <span class="click-hint">点击查看</span>
      </div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ dashboardStore.config.maxRetryNum }}</div>
      <div class="stat-label">最大重试次数</div>
    </div>
  </div>
  
  <!-- 模型列表弹窗 - 暂时移除Teleport以排除兼容性问题 -->
  <!-- <Teleport to="body"> -->
    <div class="models-modal" v-if="showModelsModal" @click.self="closeModelsModal">
      <div class="models-modal-content">
        <div class="modal-header">
          <h3>🤖 可用模型列表</h3>
          <button class="close-btn" @click="closeModelsModal">×</button>
        </div>
        
        <div class="modal-body">
          <!-- 无模型提示 -->
          <div v-if="modelsList.total === 0" class="no-models">
            <div class="empty-icon">📭</div>
            <p>暂无可用模型</p>
            <small>请检查 API 密钥配置</small>
          </div>
          
          <!-- 模型列表 -->
          <div v-else class="models-sections">
            <!-- 标准模型 -->
            <div v-if="modelsList.standard.length > 0" class="model-section">
              <div class="section-header">
                <span class="section-icon">✨</span>
                <h4>标准模型</h4>
                <span class="model-count">{{ modelsList.standard.length }}</span>
              </div>
              <div class="models-grid">
                <div v-for="model in modelsList.standard" :key="model" class="model-item">
                  <div class="model-name">{{ model }}</div>
                  <div class="model-tags">
                    <span v-if="model.includes('pro')" class="tag tag-pro">Pro</span>
                    <span v-if="model.includes('flash')" class="tag tag-flash">Flash</span>
                    <span v-if="model.includes('thinking')" class="tag tag-thinking">思考模式</span>
                    <span v-if="model.includes('2.0')" class="tag tag-new">2.0</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 联网模型 -->
            <div v-if="modelsList.search.length > 0" class="model-section">
              <div class="section-header">
                <span class="section-icon">🔍</span>
                <h4>联网模型</h4>
                <span class="model-count">{{ modelsList.search.length }}</span>
              </div>
              <div class="models-grid">
                <div v-for="model in modelsList.search" :key="model" class="model-item">
                  <div class="model-name">{{ model }}</div>
                  <div class="model-tags">
                    <span class="tag tag-search">联网模型</span>
                    <span v-if="model.includes('pro')" class="tag tag-pro">Pro</span>
                    <span v-if="model.includes('flash')" class="tag tag-flash">Flash</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <div class="footer-info">
            共 {{ modelsList.total }} 个可用模型
          </div>
        </div>
      </div>
    </div>
  <!-- </Teleport> -->
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
  margin-top: 15px;
  margin-bottom: 20px;
}

/* 移动端优化 - 保持三栏但减小间距 */
@media (max-width: 768px) {
  .stats-grid {
    gap: 6px;
  }
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
  position: relative;
}

/* 可点击的卡片样式 */
.stat-card.clickable {
  cursor: pointer;
}

.stat-card.clickable:hover {
  transform: translateY(-5px) scale(1.02);
  box-shadow: var(--shadow-lg);
  border-color: var(--button-primary);
}

/* 点击提示 */
.click-hint {
  display: inline-block;
  font-size: 11px;
  color: var(--button-primary);
  opacity: 0.6;
  margin-left: 5px;
  transition: opacity 0.3s ease;
}

.stat-card.clickable:hover .click-hint {
  opacity: 1;
}

/* 弹窗样式 */
.models-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(5px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.3s ease;
  padding: 20px;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.models-modal-content {
  background: var(--card-background);
  border-radius: var(--radius-xl);
  width: 90%;
  max-width: 700px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-xl);
  animation: slideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  position: relative;
}

@keyframes slideUp {
  from {
    transform: translateY(20px) scale(0.95);
    opacity: 0;
  }
  to {
    transform: translateY(0) scale(1);
    opacity: 1;
  }
}

/* 弹窗头部 */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  background: var(--gradient-primary);
  color: white;
  position: relative;
  overflow: hidden;
}

.modal-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at top right, rgba(255, 255, 255, 0.1), transparent 70%);
  pointer-events: none;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 600;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 1;
}

.close-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  font-size: 24px;
  width: 35px;
  height: 35px;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: rotate(90deg);
}

/* 弹窗主体 */
.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 25px;
}

/* 无模型提示 */
.no-models {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 15px;
  opacity: 0.5;
}

.no-models p {
  font-size: 16px;
  margin: 10px 0;
  opacity: 0.8;
}

.no-models small {
  font-size: 12px;
  opacity: 0.6;
}

/* 模型区块 */
.models-sections {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.model-section {
  background: var(--stats-item-bg);
  border-radius: var(--radius-lg);
  padding: 20px;
  border: 1px solid var(--card-border);
  transition: all 0.3s ease;
}

.model-section:hover {
  box-shadow: var(--shadow-sm);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--color-border);
}

.section-icon {
  font-size: 20px;
}

.section-header h4 {
  margin: 0;
  font-size: 1rem;
  color: var(--color-heading);
  flex: 1;
}

.model-count {
  background: var(--button-primary);
  color: white;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
}

/* 模型网格 */
.models-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.model-item {
  background: var(--color-background);
  border: 1px solid var(--card-border);
  border-radius: var(--radius-md);
  padding: 12px 15px;
  transition: all 0.3s ease;
  cursor: default;
}

.model-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
  border-color: var(--button-primary);
}

.model-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);
  margin-bottom: 8px;
  word-break: break-word;
}

/* 模型标签 */
.model-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.tag {
  display: inline-block;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.tag-pro {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.tag-flash {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

.tag-thinking {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: white;
}

.tag-new {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
  color: white;
}

.tag-search {
  background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
  color: white;
}

/* 弹窗底部 */
.modal-footer {
  padding: 15px 25px;
  border-top: 1px solid var(--color-border);
  background: var(--stats-item-bg);
}

.footer-info {
  text-align: center;
  font-size: 13px;
  color: var(--color-text);
  opacity: 0.8;
}

/* 滚动条样式 */
.modal-body::-webkit-scrollbar {
  width: 8px;
}

.modal-body::-webkit-scrollbar-track {
  background: var(--color-background);
  border-radius: 4px;
}

.modal-body::-webkit-scrollbar-thumb {
  background: var(--button-primary);
  border-radius: 4px;
  opacity: 0.5;
}

.modal-body::-webkit-scrollbar-thumb:hover {
  opacity: 0.8;
}

/* 移动端优化 - 更紧凑的卡片 */
@media (max-width: 768px) {
  .stat-card {
    padding: 8px 5px;
  }
  
  .stat-value {
    font-size: 16px;
  }
  
  .stat-label {
    font-size: 11px;
    margin-top: 3px;
  }
  
  .click-hint {
    font-size: 9px;
  }
  
  .models-modal-content {
    max-width: 95%;
    max-height: 85vh;
  }
  
  .modal-header {
    padding: 15px 20px;
  }
  
  .modal-header h3 {
    font-size: 1.1rem;
  }
  
  .modal-body {
    padding: 20px 15px;
  }
  
  .models-grid {
    grid-template-columns: 1fr;
  }
  
  .model-section {
    padding: 15px;
  }
}

/* 小屏幕手机进一步优化 */
@media (max-width: 480px) {
  .stat-card {
    padding: 6px 3px;
  }
  
  .stat-value {
    font-size: 14px;
  }
  
  .stat-label {
    font-size: 10px;
    margin-top: 2px;
  }
  
  .click-hint {
    display: none;
  }
  
  .models-modal {
    padding: 10px;
  }
  
  .modal-header {
    padding: 12px 15px;
  }
  
  .modal-header h3 {
    font-size: 1rem;
  }
  
  .close-btn {
    width: 30px;
    height: 30px;
    font-size: 20px;
  }
  
  .modal-body {
    padding: 15px 10px;
  }
  
  .model-item {
    padding: 10px 12px;
  }
  
  .model-name {
    font-size: 12px;
  }
  
  .tag {
    font-size: 9px;
    padding: 1px 4px;
  }
}
</style> 