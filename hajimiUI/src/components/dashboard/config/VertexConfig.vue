<script setup>
import { useDashboardStore } from '../../../stores/dashboard'
import { ref, reactive } from 'vue'

const dashboardStore = useDashboardStore()

// 创建本地配置副本用于编辑
const localConfig = reactive({
  fakeStreaming: dashboardStore.config.fakeStreaming,
  enableVertexExpress: dashboardStore.config.enableVertexExpress,
  vertexExpressApiKey: dashboardStore.config.vertexExpressApiKey || '',
  googleCredentialsJson: dashboardStore.config.googleCredentialsJson || ''
})

// 密码和错误信息
const password = ref('')
const errorMsg = ref('')
const successMsg = ref('')
const isSaving = ref(false)

// 保存所有配置
async function saveAllConfigs() {
  if (!password.value) {
    errorMsg.value = '请输入密码'
    return
  }

  isSaving.value = true
  errorMsg.value = ''
  successMsg.value = ''

  try {
    // 处理JSON格式
    if (localConfig.googleCredentialsJson) {
      try {
        // 尝试解析 JSON 并压缩
        const jsonObj = JSON.parse(localConfig.googleCredentialsJson)
        localConfig.googleCredentialsJson = JSON.stringify(jsonObj)
      } catch (e) {
        errorMsg.value = '请输入有效的 JSON 格式'
        isSaving.value = false
        return
      }
    }
    
    // 逐个保存配置项
    const configKeys = Object.keys(localConfig)
    for (const key of configKeys) {
      // 如果配置有变化才更新
      if (localConfig[key] !== dashboardStore.config[key]) {
        await dashboardStore.updateConfig(key, localConfig[key], password.value)
        // 更新store中的值
        dashboardStore.config[key] = localConfig[key]
      }
    }
    successMsg.value = '所有配置已保存'
  } catch (error) {
    errorMsg.value = error.message || '保存失败'
  } finally {
    isSaving.value = false
  }
}

// 获取布尔值显示文本
function getBooleanText(value) {
  return value ? '启用' : '禁用'
}
</script>

<template>
  <div class="vertex-config">
    <h3 class="section-title">Vertex 配置</h3>
    
    <div class="config-form">
      <!-- 布尔值配置项 -->
      <div class="config-row">
        <div class="config-group">
          <label class="config-label">假流式响应</label>
          <div class="toggle-wrapper">
            <input type="checkbox" class="toggle" id="fakeStreaming" v-model="localConfig.fakeStreaming">
            <label for="fakeStreaming" class="toggle-label">
              <span class="toggle-text">{{ getBooleanText(localConfig.fakeStreaming) }}</span>
            </label>
          </div>
        </div>
        
        <div class="config-group">
          <label class="config-label">Vertex Express</label>
          <div class="toggle-wrapper">
            <input type="checkbox" class="toggle" id="enableVertexExpress" v-model="localConfig.enableVertexExpress">
            <label for="enableVertexExpress" class="toggle-label">
              <span class="toggle-text">{{ getBooleanText(localConfig.enableVertexExpress) }}</span>
            </label>
          </div>
        </div>
      </div>
      
      <!-- API Key 配置项 -->
      <div class="config-row">
        <div class="config-group full-width">
          <label class="config-label">Vertex Express API密钥</label>
          <input 
            type="password" 
            class="config-input" 
            v-model="localConfig.vertexExpressApiKey" 
            placeholder="请输入 Vertex Express API密钥"
          >
        </div>
      </div>
      
      <!-- Google Credentials JSON 配置项 -->
      <div class="config-row">
        <div class="config-group full-width">
          <label class="config-label">Google Credentials JSON</label>
          <textarea 
            class="config-input text-area" 
            v-model="localConfig.googleCredentialsJson" 
            placeholder="请输入 Google Credentials JSON"
            rows="6"
          ></textarea>
        </div>
      </div>
      
      <!-- 保存区域 -->
      <div class="save-section">
        <div class="password-input">
          <input 
            type="password" 
            v-model="password" 
            placeholder="请输入管理密码" 
            class="config-input"
          >
        </div>
        <button 
          class="save-button" 
          @click="saveAllConfigs" 
          :disabled="isSaving"
        >
          {{ isSaving ? '保存中...' : '保存所有配置' }}
        </button>
      </div>
      
      <!-- 消息提示 -->
      <div v-if="errorMsg" class="error-message">{{ errorMsg }}</div>
      <div v-if="successMsg" class="success-message">{{ successMsg }}</div>
    </div>
  </div>
</template>

<style scoped>
.section-title {
  color: var(--color-heading);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 10px;
  margin-bottom: 20px;
  transition: all 0.3s ease;
  position: relative;
  font-weight: 600;
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

.vertex-config {
  margin-bottom: 25px;
}

.config-form {
  background-color: var(--stats-item-bg);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--card-border);
}

.config-row {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.config-group {
  flex: 1;
  min-width: 120px;
}

.full-width {
  flex-basis: 100%;
}

.config-label {
  display: block;
  font-size: 14px;
  margin-bottom: 5px;
  color: var(--color-text);
  font-weight: 500;
}

.config-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 14px;
  transition: all 0.3s ease;
}

.config-input:focus {
  outline: none;
  border-color: var(--button-primary);
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2);
}

.text-area {
  resize: vertical;
  min-height: 80px;
  font-family: inherit;
  line-height: 1.5;
}

/* 开关样式 */
.toggle-wrapper {
  position: relative;
}

.toggle {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-label {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.toggle-label::before {
  content: '';
  display: inline-block;
  width: 36px;
  height: 20px;
  background-color: var(--color-border);
  border-radius: 10px;
  margin-right: 8px;
  position: relative;
  transition: all 0.3s ease;
}

.toggle-label::after {
  content: '';
  position: absolute;
  left: 3px;
  width: 14px;
  height: 14px;
  background-color: white;
  border-radius: 50%;
  transition: all 0.3s ease;
}

.toggle:checked + .toggle-label::before {
  background-color: var(--button-primary);
}

.toggle:checked + .toggle-label::after {
  left: 19px;
}

.toggle-text {
  font-size: 14px;
  color: var(--color-text);
}

/* 保存区域样式 */
.save-section {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  align-items: center;
}

.password-input {
  flex: 1;
}

.save-button {
  padding: 8px 16px;
  background: var(--button-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
}

.save-button:hover {
  background: var(--button-primary-hover);
  transform: translateY(-2px);
}

.save-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.error-message {
  color: var(--color-error);
  margin-top: 10px;
  font-size: 14px;
  padding: 8px;
  background-color: var(--color-error-bg);
  border-radius: var(--radius-md);
}

.success-message {
  color: var(--color-success);
  margin-top: 10px;
  font-size: 14px;
  padding: 8px;
  background-color: var(--color-success-bg);
  border-radius: var(--radius-md);
}

/* 移动端优化 */
@media (max-width: 768px) {
  .config-row {
    gap: 10px;
  }
  
  .config-group {
    min-width: 100px;
  }
  
  .save-section {
    flex-direction: column;
  }
  
  .password-input {
    width: 100%;
    margin-bottom: 10px;
  }
  
  .save-button {
    width: 100%;
  }
}

/* 小屏幕手机进一步优化 */
@media (max-width: 480px) {
  .config-row {
    flex-direction: column;
    gap: 10px;
  }
  
  .config-group {
    width: 100%;
  }
  
  .config-form {
    padding: 15px;
  }
}
</style> 