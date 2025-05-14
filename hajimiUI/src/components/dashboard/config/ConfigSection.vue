<script setup>
import { ref } from 'vue'
import BasicConfig from './BasicConfig.vue'
import FeaturesConfig from './FeaturesConfig.vue'
import VertexConfig from './VertexConfig.vue'

const basicConfigRef = ref(null)
const featuresConfigRef = ref(null)
const managementPassword = ref('')
const saveMessage = ref('')
const messageType = ref('') // 'success' or 'error'

async function handleSaveAllConfigs() {
  saveMessage.value = ''
  messageType.value = ''

  if (!managementPassword.value) {
    saveMessage.value = '请输入管理密码'
    messageType.value = 'error'
    return
  }

  const results = []
  let allSucceeded = true

  if (basicConfigRef.value) {
    const result = await basicConfigRef.value.saveComponentConfigs(managementPassword.value)
    results.push(result)
    if (!result.success) {
      allSucceeded = false
    }
  }

  if (featuresConfigRef.value) {
    const result = await featuresConfigRef.value.saveComponentConfigs(managementPassword.value)
    results.push(result)
    if (!result.success) {
      allSucceeded = false
    }
  }

  const messages = results.map(r => r.message).filter(m => m).join('\n');
  saveMessage.value = messages || (allSucceeded ? '所有配置已成功保存。' : '部分配置保存失败。');
  messageType.value = allSucceeded ? 'success' : 'error';

  // 清空密码
  managementPassword.value = ''
}
</script>

<template>
  <div class="config-section">
    <BasicConfig ref="basicConfigRef" />
    <FeaturesConfig ref="featuresConfigRef" />
    
    <div class="shared-save-area">
      <div class="password-input-group">
        <input 
          type="password" 
          v-model="managementPassword" 
          placeholder="请输入管理密码"
          class="management-password-input"
        />
      </div>
      <button @click="handleSaveAllConfigs" class="save-all-button">保存所有配置</button>
    </div>

    <div v-if="saveMessage" :class="['save-message', messageType]">
      <p v-for="(line, index) in saveMessage.split('\n')" :key="index">{{ line }}</p>
    </div>
    
    <VertexConfig />
  </div>
</template>

<style scoped>
.config-section {
  padding: 20px;
  background-color: var(--color-background);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  max-width: 800px;
  margin: 20px auto;
}

.shared-save-area {
  display: flex;
  align-items: center; /* 垂直居中对齐 */
  gap: 10px; /* 输入框和按钮之间的间距 */
  padding: 15px;
  background-color: var(--stats-item-bg);
  border-radius: var(--radius-md);
  margin-top: 20px;
  margin-bottom: 15px;
  border: 1px solid var(--card-border);
}

.password-input-group {
  flex-grow: 1; /* 让密码输入框占据更多空间 */
}

.management-password-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background-color: var(--color-input-bg);
  color: var(--color-text);
  font-size: 14px;
}

.management-password-input:focus {
  outline: none;
  border-color: var(--button-primary);
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2);
}

.save-all-button {
  padding: 10px 20px;
  background: var(--gradient-primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-weight: 500;
  font-size: 14px;
  transition: all 0.3s ease;
  white-space: nowrap; /* 防止按钮文字换行 */
}

.save-all-button:hover {
  opacity: 0.9;
  box-shadow: var(--shadow-sm);
}

.save-message {
  margin-top: 10px;
  padding: 10px;
  border-radius: var(--radius-md);
  font-size: 14px;
  text-align: left;
  white-space: pre-wrap; /* 保留换行符 */
}

.save-message.success {
  background-color: rgba(74, 222, 128, 0.1);
  color: #34d399;
  border: 1px solid rgba(74, 222, 128, 0.3);
}

.save-message.error {
  background-color: rgba(248, 113, 113, 0.1);
  color: #f87171;
  border: 1px solid rgba(248, 113, 113, 0.3);
}

@media (max-width: 768px) {
  .config-section {
    padding: 15px;
  }
  .shared-save-area {
    flex-direction: column; /* 在小屏幕上堆叠 */
    align-items: stretch; /* 在小屏幕上拉伸项目以填充宽度 */
  }
  .save-all-button {
    width: 100%; /* 按钮宽度也100% */
  }
}
</style> 