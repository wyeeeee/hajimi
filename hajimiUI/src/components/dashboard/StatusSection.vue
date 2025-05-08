<script setup>
  import { useDashboardStore } from '../../stores/dashboard'
  import { ref } from 'vue'
  import StatusStats from './status/StatusStats.vue'
  import ApiKeyStats from './status/ApiKeyStats.vue'
  import DailyStatsChart from './status/DailyStatsChart.vue'
  
  const dashboardStore = useDashboardStore()
  
  // 重置对话框状态
  const showResetDialog = ref(false)
  const resetPassword = ref('')
  const resetError = ref('')
  const isResetting = ref(false)
  
  // 打开重置对话框
  function openResetDialog() {
    showResetDialog.value = true
    resetPassword.value = ''
    resetError.value = ''
  }
  
  // 关闭重置对话框
  function closeResetDialog() {
    showResetDialog.value = false
    resetPassword.value = ''
    resetError.value = ''
  }
  
  // 重置统计数据
  async function resetStats() {
    if (!resetPassword.value) {
      resetError.value = '请输入密码'
      return
    }
    
    isResetting.value = true
    resetError.value = ''
    
    try {
      const response = await fetch('/api/reset-stats', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ password: resetPassword.value })
      })
      
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.detail || '重置失败')
      }
      
      // 重置成功，刷新数据
      await dashboardStore.fetchDashboardData()
      
      // 添加短暂延迟，确保后端数据已完全重置
      setTimeout(async () => {
        try {
          await dashboardStore.fetchDashboardData()
          console.log('重置后数据已刷新')
        } catch (error) {
          console.error('刷新数据失败:', error)
        } finally {
          closeResetDialog()
        }
      }, 1000) // 增加延迟时间到1秒
    } catch (error) {
      console.error('重置失败:', error)
      resetError.value = error.message || '重置失败，请检查密码是否正确'
    } finally {
      isResetting.value = false
    }
  }
</script>
  
  <template>
    <div class="info-box">
      <div class="section-header">
        <h2 class="section-title">🟢 运行状态</h2>
        <div class="status-container">
          <p class="status">服务运行中</p>
        </div>
        <button class="reset-button" @click="openResetDialog" v-if="!dashboardStore.status.enableVertex">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
            <path d="M3 3v5h5"></path>
          </svg>
          重置次数
        </button>
      </div>
      <div class="vertex-notice" v-if="dashboardStore.status.enableVertex">
        <div class="notice-icon">ℹ️</div>
        <div class="notice-content">
          <h3 class="notice-title">Vertex 模式说明</h3>
          <p class="notice-text">当前项目处于 Vertex 模式，完全基于 gzzhongqi/vertex2openai 项目开发。目前处于初步适配阶段，统计功能正在逐步完善中。</p>
        </div>
      </div>
      
      <!-- 引入运行状态统计组件 -->
      <StatusStats />
      
      <!-- 引入每日统计图表组件 -->
      <DailyStatsChart />
      
      <!-- 引入API密钥统计组件 -->
      <ApiKeyStats />
      
      <!-- 重置对话框 -->
      <div v-if="showResetDialog" class="dialog-overlay">
        <div class="dialog">
          <h3>重置API调用统计</h3>
          <p>请输入密码以确认重置操作：</p>
          <input 
            type="password" 
            v-model="resetPassword" 
            placeholder="请输入密码"
            @keyup.enter="resetStats"
          />
          <div v-if="resetError" class="error-message">{{ resetError }}</div>
          <div class="dialog-buttons">
            <button class="cancel-button" @click="closeResetDialog">取消</button>
            <button 
              class="confirm-button" 
              @click="resetStats" 
              :disabled="isResetting"
            >
              {{ isResetting ? '重置中...' : '确认重置' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <style scoped>
  .info-box {
    background-color: var(--card-background);
    border: 1px solid var(--card-border);
    border-radius: var(--radius-xl);
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: var(--shadow-md);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
  }
  
  .info-box::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: var(--gradient-success);
    opacity: 0.8;
  }
  
  /* 移动端优化 - 减小外边距 */
  @media (max-width: 768px) {
    .info-box {
      margin-bottom: 12px;
      padding: 15px 10px;
      border-radius: var(--radius-lg);
    }
  }
  
  @media (max-width: 480px) {
    .info-box {
      margin-bottom: 8px;
      padding: 12px 8px;
      border-radius: var(--radius-md);
    }
  }
  
  /* 添加section-header样式 */
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
    position: relative;
  }
  
  /* 状态容器样式 */
  .status-container {
    display: flex;
    align-items: center;
    justify-content: center;
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
  }
  
  /* 重置按钮样式 */
  .reset-button {
    display: flex;
    align-items: center;
    gap: 5px;
    background-color: var(--button-secondary);
    color: var(--button-secondary-text);
    border: none;
    border-radius: var(--radius-md);
    padding: 8px 12px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow-sm);
    height: 100%;
    z-index: 1;
  }
  
  .reset-button::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
    transform: translateX(-100%);
    transition: transform 0.6s ease;
  }
  
  .reset-button:hover::before {
    transform: translateX(100%);
  }
  
  .reset-button:hover {
    background-color: var(--button-secondary-hover);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }
  
  .reset-button svg {
    transition: transform 0.3s;
  }
  
  .reset-button:hover svg {
    transform: rotate(180deg);
  }
  
  /* 对话框样式 */
  .dialog-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: flex-start;
    z-index: 1000;
    padding-top: 20px;
    backdrop-filter: blur(5px);
  }
  
  .dialog {
    background-color: var(--card-background);
    border-radius: var(--radius-xl);
    padding: 20px;
    width: 90%;
    max-width: 400px;
    box-shadow: var(--shadow-xl);
    margin-top: 20px;
    position: relative;
    overflow: hidden;
    animation: dialogAppear 0.3s ease forwards;
  }
  
  @keyframes dialogAppear {
    0% {
      opacity: 0;
      transform: translateY(-20px) scale(0.95);
    }
    100% {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }
  
  .dialog::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 4px;
    background: var(--gradient-primary);
  }
  
  .dialog h3 {
    margin-top: 0;
    margin-bottom: 10px;
    color: var(--color-heading);
    font-size: 1.2rem;
    font-weight: 600;
  }
  
  .dialog p {
    margin-bottom: 15px;
    color: var(--color-text);
    font-size: 14px;
    line-height: 1.5;
  }
  
  .dialog input {
    width: 100%;
    padding: 12px 16px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    margin-bottom: 15px;
    background-color: var(--color-background);
    color: var(--color-text);
    transition: all 0.3s ease;
    font-size: 14px;
  }
  
  .dialog input:focus {
    outline: none;
    border-color: var(--button-primary);
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2);
  }
  
  .error-message {
    color: #ef4444;
    margin-bottom: 15px;
    font-size: 14px;
    padding: 8px 12px;
    background-color: rgba(239, 68, 68, 0.1);
    border-radius: var(--radius-md);
    border-left: 3px solid #ef4444;
  }
  
  .dialog-buttons {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
  
  .cancel-button {
    background-color: var(--button-secondary);
    color: var(--button-secondary-text);
    border: none;
    border-radius: var(--radius-md);
    padding: 10px 18px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-weight: 500;
  }
  
  .cancel-button:hover {
    background-color: var(--button-secondary-hover);
    transform: translateY(-2px);
    box-shadow: var(--shadow-sm);
  }
  
  .confirm-button {
    background: var(--gradient-primary);
    color: white;
    border: none;
    border-radius: var(--radius-md);
    padding: 10px 18px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-weight: 500;
    box-shadow: var(--shadow-sm);
  }
  
  .confirm-button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }
  
  .confirm-button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
  
  .status {
    color: #10b981;
    font-weight: bold;
    font-size: 16px;
    padding: 8px 12px;
    background-color: rgba(16, 185, 129, 0.1);
    border-radius: var(--radius-md);
    border-left: none;
    transition: all 0.3s ease;
    animation: pulse 2s infinite;
    margin: 0;
    white-space: nowrap;
  }
  
  @keyframes pulse {
    0% {
      box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
    }
    70% {
      box-shadow: 0 0 0 10px rgba(16, 185, 129, 0);
    }
    100% {
      box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
    }
  }
  
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
  
  .vertex-notice {
    background-color: var(--color-background-soft);
    border-radius: var(--radius-lg);
    padding: 16px;
    margin: 20px 0;
    display: flex;
    gap: 16px;
    align-items: flex-start;
    border: 1px solid var(--color-border);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
  }
  
  .vertex-notice::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: var(--gradient-info);
    opacity: 0.8;
  }
  
  .vertex-notice:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow-md);
    border-color: var(--button-primary);
  }
  
  .notice-icon {
    font-size: 24px;
    background-color: var(--color-background-mute);
    padding: 8px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 40px;
    height: 40px;
    transition: all 0.3s ease;
    box-shadow: var(--shadow-sm);
  }
  
  .notice-content {
    flex: 1;
  }
  
  .notice-title {
    color: var(--color-heading);
    font-size: 16px;
    font-weight: 600;
    margin: 0 0 8px 0;
    transition: all 0.3s ease;
  }
  
  .notice-text {
    color: var(--color-text);
    font-size: 14px;
    line-height: 1.5;
    margin: 0;
    transition: all 0.3s ease;
  }
  
  @media (max-width: 768px) {
    .vertex-notice {
      padding: 12px;
      gap: 12px;
    }
    
    .notice-icon {
      font-size: 20px;
      min-width: 32px;
      height: 32px;
      padding: 6px;
    }
    
    .notice-title {
      font-size: 14px;
      margin-bottom: 6px;
    }
    
    .notice-text {
      font-size: 12px;
    }
    
    .status {
      font-size: 14px;
      padding: 6px 10px;
    }
    
    .reset-button {
      font-size: 12px;
      padding: 6px 10px;
    }
  }
  
  /* 小屏幕手机进一步优化 */
  @media (max-width: 480px) {
    .status {
      font-size: 12px;
      padding: 4px 8px;
    }
    
    .reset-button {
      font-size: 11px;
      padding: 4px 8px;
    }
    
    .section-header {
      flex-direction: row;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      position: relative;
      padding-top: 0;
    }
    
    .section-title {
      font-size: 14px;
      margin-right: auto;
    }
    
    .status-container {
      position: static;
      transform: none;
      margin: 0;
    }
    
    .reset-button {
      align-self: center;
    }
  }
</style>