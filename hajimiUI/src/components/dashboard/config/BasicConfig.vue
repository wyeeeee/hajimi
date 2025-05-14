<script setup>
import { useDashboardStore } from '../../../stores/dashboard'
import { ref, reactive, watch } from 'vue'

const dashboardStore = useDashboardStore()

// Initialize localConfig with default structure
const localConfig = reactive({
  maxRequestsPerMinute: 0,
  maxRequestsPerDayPerIp: 0
})

const populatedFromStore = ref(false);

// Watch for store changes to populate localConfig ONCE when config is loaded
watch(
  () => ({
    storeMaxRequestsPerMinute: dashboardStore.config.maxRequestsPerMinute,
    storeMaxRequestsPerDayPerIp: dashboardStore.config.maxRequestsPerDayPerIp,
    configIsActuallyLoaded: dashboardStore.isConfigLoaded,
  }),
  (newValues) => {
    if (newValues.configIsActuallyLoaded && !populatedFromStore.value) {
      localConfig.maxRequestsPerMinute = newValues.storeMaxRequestsPerMinute;
      localConfig.maxRequestsPerDayPerIp = newValues.storeMaxRequestsPerDayPerIp;
      populatedFromStore.value = true;
    }
  },
  { deep: true, immediate: true }
)

// 保存组件配置
async function saveComponentConfigs(passwordFromParent) {
  if (!passwordFromParent) {
    return { success: false, message: '基本配置: 密码未提供' }
  }

  let allSucceeded = true;
  let individualMessages = [];

  // 逐个保存配置项
  const configKeys = Object.keys(localConfig)
  for (const key of configKeys) {
    // 如果配置有变化才更新
    if (localConfig[key] !== dashboardStore.config[key]) {
      try {
        await dashboardStore.updateConfig(key, localConfig[key], passwordFromParent)
        // 更新store中的值 - 仅在API调用成功后
        dashboardStore.config[key] = localConfig[key]
        individualMessages.push(`${key} 保存成功`);
      } catch (error) {
        allSucceeded = false;
        individualMessages.push(`${key} 保存失败: ${error.message || '未知错误'}`);
      }
    }
  }

  if (allSucceeded && individualMessages.length === 0) {
    // 如果没有任何更改，也算成功，但提示用户
     return { success: true, message: '基本配置: 无更改需要保存' };
  }
  
  return {
    success: allSucceeded,
    message: `基本配置: ${individualMessages.join('; ')}`
  };
}

defineExpose({
  saveComponentConfigs,
  localConfig
})
</script>

<template>
  <div class="basic-config">
    <h3 class="section-title">基本配置</h3>
    
    <div class="config-form">
      <!-- 数值配置项 -->
      <div class="config-row">
        <div class="config-group">
          <label class="config-label">每分钟请求限制</label>
          <input 
            type="number" 
            class="config-input" 
            v-model.number="localConfig.maxRequestsPerMinute" 
            min="0"
          >
        </div>
        
        <div class="config-group">
          <label class="config-label">每IP每日请求限制</label>
          <input 
            type="number" 
            class="config-input" 
            v-model.number="localConfig.maxRequestsPerDayPerIp" 
            min="0"
          >
        </div>
      </div>
      
      <!-- 移除独立的保存区域 -->
      <!-- 消息提示由父组件处理 -->
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

.basic-config {
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

/* 移动端优化 */
@media (max-width: 768px) {
  .config-row {
    gap: 10px;
  }
  
  .config-group {
    min-width: 100px;
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