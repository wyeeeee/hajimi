<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import StatusSection from '../components/dashboard/StatusSection.vue'
import ConfigSection from '../components/dashboard/ConfigSection.vue'
import LogSection from '../components/dashboard/LogSection.vue'
import BackendSwitcher from '../components/backend/BackendSwitcher.vue'
import { useDashboardStore } from '../stores/dashboard'
import { useBackendStore } from '../stores/backend'

const dashboardStore = useDashboardStore()
const backendStore = useBackendStore()
const router = useRouter()
const refreshInterval = ref(null)
const isPageLoaded = ref(false)
const animationStep = ref(0)
const animationCompleted = ref(false)

// 计算属性：夜间模式状态
const isDarkMode = computed(() => dashboardStore.isDarkMode)
const config = computed(() => dashboardStore.config)

// 密码验证对话框状态
const showPasswordDialog = ref(false)
const password = ref('')
const passwordError = ref('')

// 页面加载时获取数据并启动自动刷新
onMounted(() => {
  fetchDashboardData()
  startAutoRefresh()
  
  // 添加开屏动画效果
  setTimeout(() => {
    isPageLoaded.value = true
    
    // 逐步触发动画
    const animateStep = () => {
      if (animationStep.value < 10) {
        animationStep.value++
        setTimeout(animateStep, 100)
      } else {
        // 动画完成后标记
        animationCompleted.value = true
      }
    }
    
    setTimeout(animateStep, 50)
  }, 50)
})

// 组件卸载时停止自动刷新
onUnmounted(() => {
  stopAutoRefresh()
})

// 开始自动刷新
function startAutoRefresh() {
  if (!refreshInterval.value) {
    refreshInterval.value = setInterval(fetchDashboardData, 1000) // 1秒刷新一次
    console.log('自动刷新已启动')
  }
}

// 停止自动刷新
function stopAutoRefresh() {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
    refreshInterval.value = null
    console.log('自动刷新已停止')
  }
}

// 获取仪表盘数据
async function fetchDashboardData() {
  try {
    await dashboardStore.fetchDashboardData()
  } catch (error) {
    console.error('获取仪表盘数据失败:', error)
    // 可以显示错误提示
  }
}

// 手动刷新
function handleRefresh() {
  fetchDashboardData()
}

// 打开后端管理页面
function openBackendManager() {
  router.push('/backends')
}

// 切换夜间模式
function toggleDarkMode() {
  dashboardStore.toggleDarkMode()
}

// 打开密码验证对话框
function openPasswordDialog() {
  showPasswordDialog.value = true
  password.value = ''
  passwordError.value = ''
}

// 关闭密码验证对话框
function closePasswordDialog() {
  showPasswordDialog.value = false
  password.value = ''
  passwordError.value = ''
}

// 验证密码并切换Vertex
async function verifyAndToggleVertex() {
  if (!password.value) {
    passwordError.value = '请输入密码'
    return
  }
  
  try {
    // 调用API更新配置
    await dashboardStore.updateConfig('enableVertex', !config.value.enableVertex, password.value)
    
    // 更新本地状态
    dashboardStore.config.enableVertex = !config.value.enableVertex
    
    // 关闭对话框
    closePasswordDialog()
  } catch (error) {
    passwordError.value = error.message || '密码错误'
  }
}
</script>

<template>
  <div class="dashboard" :class="{ 'page-loaded': isPageLoaded }">
    <!-- 后端切换器 -->
    <div class="backend-switcher-container" :class="{ 'animate-in': animationStep >= 0 || animationCompleted }">
      <BackendSwitcher @openManager="openBackendManager" />
    </div>
    
    <div class="header-container" :class="{ 'animate-in': animationStep >= 1 || animationCompleted }">
      <div class="title-container">
        <h1><span>🤖 Gemini API 代理服务</span></h1>
        <div class="backend-indicator">
          <span class="current-backend">{{ backendStore.activeBackend?.name || '未连接' }}</span>
        </div>
      </div>
      <div class="toggle-container">
        <button class="vertex-button" :class="{ 'active': config.enableVertex }" @click="openPasswordDialog">
          {{ config.enableVertex ? 'Vertex 开' : 'Vertex 关' }}
        </button>
        <button class="theme-button" :class="{ 'active': isDarkMode }" @click="toggleDarkMode">
          {{ isDarkMode ? '🌙 夜间' : '☀️ 日间' }}
        </button>
      </div>
    </div>
    
    <!-- 运行状态和环境配置并排显示 -->
    <div class="sections-row">
      <!-- 运行状态部分 -->
      <StatusSection class="section-animate status-section" :class="{ 'animate-in': animationStep >= 2 || animationCompleted }" />
      
      <!-- 环境配置部分 -->
      <ConfigSection class="section-animate config-section" :class="{ 'animate-in': animationStep >= 3 || animationCompleted }" />
    </div>
    
    <!-- 系统日志部分 -->
    <LogSection class="section-animate" :class="{ 'animate-in': animationStep >= 4 || animationCompleted }" />
    
    <button class="refresh-button" :class="{ 'animate-in': animationStep >= 5 || animationCompleted }" @click="handleRefresh">刷新数据</button>
    
    <!-- 密码验证对话框 -->
    <div class="password-dialog" v-if="showPasswordDialog">
      <div class="password-dialog-content">
        <h3>验证密码</h3>
        <p>请输入密码以{{ config.enableVertex ? '禁用' : '启用' }} Vertex AI</p>
        <div class="password-input-container">
          <input 
            type="password" 
            v-model="password"
            class="password-input"
            placeholder="请输入密码"
            @keyup.enter="verifyAndToggleVertex"
          >
          <div class="password-error" v-if="passwordError">{{ passwordError }}</div>
        </div>
        <div class="password-actions">
          <button class="cancel-btn" @click="closePasswordDialog">取消</button>
          <button class="confirm-btn" @click="verifyAndToggleVertex">确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  line-height: 1.6;
  background-color: var(--color-background);
  color: var(--color-text);
  margin: 0;
  padding: 0;
  transition: background-color 0.3s, color 0.3s;
}

.dashboard {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94), transform 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.dashboard.page-loaded {
  opacity: 1;
  transform: translateY(0);
}

/* 后端切换器容器 */
.backend-switcher-container {
  position: sticky;
  top: 20px;
  z-index: 100;
  margin-bottom: 20px;
  opacity: 0;
  transform: translateY(-20px);
  transition: opacity 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.backend-switcher-container.animate-in {
  opacity: 1;
  transform: translateY(0);
}

.header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  opacity: 0;
  transform: translateY(20px) scale(0.95);
  transition: opacity 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  background: var(--gradient-primary);
  padding: 20px;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  position: relative;
  overflow: hidden;
}

.header-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at top right, rgba(255, 255, 255, 0.1), transparent 70%);
  z-index: 0;
}

.header-container::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at bottom left, rgba(255, 255, 255, 0.1), transparent 70%);
  z-index: 0;
}

.header-container.animate-in {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.title-container {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  flex-wrap: wrap;
  position: relative;
  z-index: 1;
}

.backend-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.current-backend {
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(5px);
}

.toggle-container {
  display: flex;
  align-items: center;
  gap: 15px;
  position: relative;
  z-index: 1;
}

.vertex-button, .theme-button {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(255, 255, 255, 0.15);
  padding: 8px 16px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;
  box-shadow: var(--shadow-md);
  cursor: pointer;
  font-size: 0.9rem;
  color: white;
  font-weight: 500;
  min-width: 90px;
  backdrop-filter: blur(5px);
}

.vertex-button.active, .theme-button.active {
  background-color: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.3);
  color: white;
}

.vertex-button:hover, .theme-button:hover {
  background-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

h1 {
  color: white;
  margin: 0;
  font-size: 1.8rem;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* 按钮样式替代滑块 */
.vertex-toggle, .theme-toggle, .switch, .slider {
  display: none;
}

/* 并排显示部分 */
.sections-row {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 20px;
}

.status-section, .config-section {
  width: 100%;
}

/* 移动端优化 - 减小整体边距 */
@media (max-width: 768px) {
  .dashboard {
    padding: 10px 8px;
  }
  
  .header-container {
    flex-direction: row;
    align-items: center;
    margin-bottom: 15px;
    padding: 15px;
  }
  
  .title-container {
    width: auto;
    justify-content: flex-start;
    margin-bottom: 0;
    flex: 1;
  }
  
  h1 {
    font-size: 1.4rem;
    text-align: left;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  h1::before {
    content: '🤖Gemini代理';
  }
  
  h1 span {
    display: none;
  }
  
  .toggle-container {
    width: auto;
    justify-content: flex-end;
    flex-direction: row;
    gap: 8px;
    margin-top: 0;
    align-self: center;
  }
  
  .vertex-button, .theme-button {
    padding: 6px 12px;
    font-size: 0.8rem;
    min-width: 80px;
  }
  
  /* 移动端下保持垂直布局 */
  .sections-row {
    flex-direction: column;
    gap: 15px;
  }
}

@media (max-width: 480px) {
  .dashboard {
    padding: 6px 4px;
  }
  
  .header-container {
    flex-direction: row;
    align-items: center;
    margin-bottom: 15px;
    padding: 12px;
  }
  
  .title-container {
    width: auto;
    justify-content: flex-start;
    margin-bottom: 0;
    flex: 1;
  }
  
  h1 {
    font-size: 1.1rem;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .toggle-container {
    width: auto;
    justify-content: flex-end;
    flex-direction: row;
    gap: 4px;
    margin-top: 0;
    align-self: center;
  }
  
  .vertex-button, .theme-button {
    padding: 4px 8px;
    font-size: 0.65rem;
    min-width: 70px;
  }
  
  /* 移动端下保持垂直布局 */
  .sections-row {
    flex-direction: column;
    gap: 10px;
  }
}

.refresh-button {
  display: block;
  margin: 20px auto;
  padding: 12px 24px;
  background: var(--gradient-secondary);
  color: white;
  border: none;
  border-radius: var(--radius-lg);
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  opacity: 0;
  transform: translateY(20px) scale(0.95);
  box-shadow: var(--shadow-md);
  position: relative;
  overflow: hidden;
}

.refresh-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(to right, transparent, rgba(255, 255, 255, 0.2), transparent);
  transform: translateX(-100%);
  transition: transform 0.6s ease;
}

.refresh-button:hover::before {
  transform: translateX(100%);
}

.refresh-button.animate-in {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.refresh-button:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}

/* 全局响应式样式 - 保持三栏布局但优化显示 */
@media (max-width: 768px) {
  /* 覆盖所有组件中的卡片样式 */
  :deep(.info-box) {
    padding: 15px 10px;
    margin-bottom: 15px;
    border-radius: var(--radius-lg);
    background-color: var(--card-background);
    border: 1px solid var(--card-border);
    box-shadow: var(--shadow-md);
    position: relative;
    overflow: hidden;
  }
  
  :deep(.info-box)::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: var(--gradient-primary);
  }
  
  :deep(.section-title) {
    font-size: 1.1rem;
    margin-bottom: 15px;
    padding-bottom: 8px;
    color: var(--color-heading);
    border-bottom: 1px solid var(--color-border);
    position: relative;
  }
  
  :deep(.section-title)::after {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 0;
    width: 50px;
    height: 2px;
    background: var(--gradient-primary);
  }
  
  :deep(.stats-grid) {
    gap: 10px;
    margin-top: 15px;
    margin-bottom: 20px;
  }
  
  .refresh-button {
    margin: 20px auto;
    padding: 10px 20px;
    font-size: 14px;
  }
}

/* 小屏幕手机适配 */
@media (max-width: 480px) {
  :deep(.info-box) {
    padding: 12px 8px;
    margin-bottom: 10px;
    border-radius: var(--radius-md);
  }
  
  :deep(.section-title) {
    font-size: 1rem;
    margin-bottom: 10px;
    padding-bottom: 6px;
  }
  
  :deep(.stats-grid) {
    gap: 8px;
    margin-top: 10px;
    margin-bottom: 15px;
  }
  
  .refresh-button {
    margin: 15px auto;
    padding: 8px 16px;
    font-size: 13px;
  }
}

/* 开屏动画效果 */
.section-animate {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
  transition: opacity 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.section-animate.animate-in {
  opacity: 1;
  transform: translateY(0) scale(1);
}

/* 子元素动画 */
:deep(.stats-grid) {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
  transition: opacity 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.animate-in :deep(.stats-grid) {
  opacity: 1;
  transform: translateY(0) scale(1);
  transition-delay: 0.1s;
}

/* 卡片动画 */
:deep(.stat-card) {
  opacity: 0;
  transform: scale(0.9) translateY(10px);
  transition: opacity 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s, background-color 0.3s;
  position: relative;
  overflow: hidden;
}

:deep(.stat-card)::before {
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

:deep(.stat-card:hover)::before {
  opacity: 1;
}

.animate-in :deep(.stat-card) {
  opacity: 1;
  transform: scale(1) translateY(0);
}

.animate-in :deep(.stat-card:nth-child(1)) {
  transition-delay: 0.15s;
}

.animate-in :deep(.stat-card:nth-child(2)) {
  transition-delay: 0.2s;
}

.animate-in :deep(.stat-card:nth-child(3)) {
  transition-delay: 0.25s;
}

.animate-in :deep(.stat-card:nth-child(4)) {
  transition-delay: 0.3s;
}

.animate-in :deep(.stat-card:nth-child(5)) {
  transition-delay: 0.35s;
}

.animate-in :deep(.stat-card:nth-child(6)) {
  transition-delay: 0.4s;
}

.animate-in :deep(.stat-card:nth-child(7)) {
  transition-delay: 0.45s;
}

.animate-in :deep(.stat-card:nth-child(8)) {
  transition-delay: 0.5s;
}

/* 日志条目动画 */
:deep(.log-entry) {
  opacity: 0;
  transform: translateX(-10px) scale(0.98);
  transition: opacity 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  position: relative;
  overflow: hidden;
}

:deep(.log-entry)::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.05), transparent);
  transform: translateX(-100%);
  transition: transform 0.6s ease;
}

:deep(.log-entry:hover)::after {
  transform: translateX(100%);
}

.animate-in :deep(.log-entry) {
  opacity: 1;
  transform: translateX(0) scale(1);
}

.animate-in :deep(.log-entry:nth-child(1)) {
  transition-delay: 0.15s;
}

.animate-in :deep(.log-entry:nth-child(2)) {
  transition-delay: 0.2s;
}

.animate-in :deep(.log-entry:nth-child(3)) {
  transition-delay: 0.25s;
}

.animate-in :deep(.log-entry:nth-child(4)) {
  transition-delay: 0.3s;
}

.animate-in :deep(.log-entry:nth-child(5)) {
  transition-delay: 0.35s;
}

.animate-in :deep(.log-entry:nth-child(n+6)) {
  transition-delay: 0.4s;
}

/* 添加飞入动画效果 */
@keyframes flyIn {
  0% {
    opacity: 0;
    transform: translateY(30px) scale(0.9);
  }
  50% {
    opacity: 0.5;
    transform: translateY(15px) scale(0.95);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes flyInFromLeft {
  0% {
    opacity: 0;
    transform: translateX(-20px) scale(0.9);
  }
  50% {
    opacity: 0.5;
    transform: translateX(-10px) scale(0.95);
  }
  100% {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
}

@keyframes flyInFromRight {
  0% {
    opacity: 0;
    transform: translateX(20px) scale(0.9);
  }
  50% {
    opacity: 0.5;
    transform: translateX(10px) scale(0.95);
  }
  100% {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
}

/* 应用飞入动画 */
.header-container.animate-in {
  animation: flyIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.section-animate.animate-in {
  animation: flyIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.animate-in :deep(.stat-card:nth-child(odd)) {
  animation: flyInFromLeft 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.animate-in :deep(.stat-card:nth-child(even)) {
  animation: flyInFromRight 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.animate-in :deep(.log-entry) {
  animation: flyInFromLeft 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

.refresh-button.animate-in {
  animation: flyIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

/* 密码验证对话框样式 */
.password-dialog {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  z-index: 1000;
  padding-top: 100px;
  backdrop-filter: blur(5px);
}

.password-dialog-content {
  background-color: var(--card-background);
  border-radius: var(--radius-xl);
  padding: 25px;
  width: 90%;
  max-width: 400px;
  box-shadow: var(--shadow-xl);
  position: relative;
  overflow: hidden;
}

.password-dialog-content::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 5px;
  background: var(--gradient-primary);
}

.password-dialog-content h3 {
  margin-top: 0;
  margin-bottom: 10px;
  color: var(--color-heading);
  font-size: 1.3rem;
}

.password-dialog-content p {
  margin-bottom: 15px;
  color: var(--color-text);
  font-size: 14px;
}

.password-input-container {
  margin-bottom: 20px;
  position: relative;
}

.password-input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 14px;
  transition: all 0.3s ease;
}

.password-input:focus {
  outline: none;
  border-color: var(--button-primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2);
}

.password-error {
  color: #ef4444;
  font-size: 12px;
  margin-top: 8px;
  padding-left: 5px;
}

.password-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.cancel-btn, .confirm-btn {
  padding: 10px 18px;
  border-radius: var(--radius-md);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-btn {
  background-color: var(--button-secondary);
  border: 1px solid var(--color-border);
  color: var(--button-secondary-text);
}

.confirm-btn {
  background: var(--gradient-primary);
  border: none;
  color: white;
  box-shadow: var(--shadow-sm);
}

.cancel-btn:hover {
  background-color: var(--button-secondary-hover);
  transform: translateY(-2px);
}

.confirm-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

/* 移动端优化 */
@media (max-width: 768px) {
  .password-dialog {
    padding-top: 80px;
  }
  
  .password-dialog-content {
    padding: 20px;
  }
}

@media (max-width: 480px) {
  .password-dialog {
    padding-top: 60px;
  }
  
  .password-dialog-content {
    padding: 15px;
  }
  
  .password-dialog-content h3 {
    font-size: 1.1rem;
  }
  
  .password-dialog-content p {
    font-size: 12px;
  }
  
  .password-input {
    font-size: 12px;
    padding: 10px 14px;
  }
  
  .cancel-btn, .confirm-btn {
    padding: 8px 14px;
    font-size: 12px;
  }
}
</style>