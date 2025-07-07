<template>
  <div class="user-guide" v-if="showGuide">
    <div class="guide-overlay" @click="closeGuide"></div>
    <div class="guide-content">
      <div class="guide-header">
        <h3>🎯 多后端实例使用指南</h3>
        <button @click="closeGuide" class="close-btn">×</button>
      </div>
      
      <div class="guide-body">
        <div class="guide-section">
          <h4>📚 什么是多后端实例？</h4>
          <p>多后端实例功能允许您同时管理和切换多个 Hajimi 服务器，比如：</p>
          <ul>
            <li>本地开发环境</li>
            <li>生产服务器</li>
            <li>测试环境</li>
            <li>不同地区的部署</li>
          </ul>
        </div>

        <div class="guide-section">
          <h4>🚀 快速开始</h4>
          <div class="guide-steps">
            <div class="step">
              <div class="step-number">1</div>
              <div class="step-content">
                <h5>添加后端实例</h5>
                <p>点击"添加实例"按钮，输入服务器地址和访问密码</p>
              </div>
            </div>
            
            <div class="step">
              <div class="step-number">2</div>
              <div class="step-content">
                <h5>测试连接</h5>
                <p>添加后自动测试连接，确保服务器可正常访问</p>
              </div>
            </div>
            
            <div class="step">
              <div class="step-number">3</div>
              <div class="step-content">
                <h5>切换实例</h5>
                <p>在顶部下拉菜单中选择要使用的后端实例</p>
              </div>
            </div>
          </div>
        </div>

        <div class="guide-section">
          <h4>💡 使用技巧</h4>
          <div class="tips">
            <div class="tip">
              <span class="tip-icon">🔧</span>
              <div class="tip-content">
                <strong>管理实例：</strong>在后端管理页面可以编辑、删除、测试连接
              </div>
            </div>
            
            <div class="tip">
              <span class="tip-icon">💾</span>
              <div class="tip-content">
                <strong>配置保存：</strong>所有配置自动保存到本地存储，刷新页面不会丢失
              </div>
            </div>
            
            <div class="tip">
              <span class="tip-icon">📊</span>
              <div class="tip-content">
                <strong>实时状态：</strong>顶部显示当前连接的后端实例和连接状态
              </div>
            </div>
            
            <div class="tip">
              <span class="tip-icon">📁</span>
              <div class="tip-content">
                <strong>导入导出：</strong>支持配置的导入导出，方便在不同设备间同步
              </div>
            </div>
          </div>
        </div>

        <div class="guide-section">
          <h4>⚠️ 注意事项</h4>
          <div class="warnings">
            <div class="warning">
              <span class="warning-icon">🔒</span>
              <span>访问密码将保存在本地浏览器中，请确保设备安全</span>
            </div>
            
            <div class="warning">
              <span class="warning-icon">🌐</span>
              <span>跨域访问可能需要后端服务器配置 CORS 支持</span>
            </div>
            
            <div class="warning">
              <span class="warning-icon">📡</span>
              <span>建议定期测试连接，确保后端服务正常运行</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="guide-footer">
        <label class="dont-show-again">
          <input type="checkbox" v-model="dontShowAgain" />
          <span>不再显示此指南</span>
        </label>
        <button @click="closeGuide" class="btn btn-primary">
          开始使用
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['close'])

const showGuide = ref(false)
const dontShowAgain = ref(false)

// 检查是否需要显示指南
onMounted(() => {
  const hasShownGuide = localStorage.getItem('hajimi_guide_shown')
  if (!hasShownGuide) {
    showGuide.value = true
  }
})

// 关闭指南
function closeGuide() {
  if (dontShowAgain.value) {
    localStorage.setItem('hajimi_guide_shown', 'true')
  }
  showGuide.value = false
  emit('close')
}

// 显示指南（外部调用）
function show() {
  showGuide.value = true
}

// 重置指南状态
function reset() {
  localStorage.removeItem('hajimi_guide_shown')
  dontShowAgain.value = false
}

defineExpose({
  show,
  reset
})
</script>

<style scoped>
.user-guide {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  box-sizing: border-box;
}

.guide-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(5px);
}

.guide-content {
  position: relative;
  background: white;
  border-radius: 16px;
  width: 100%;
  max-width: 700px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.guide-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 24px 16px 24px;
  border-bottom: 1px solid #e9ecef;
}

.guide-header h3 {
  margin: 0;
  color: #333;
  font-size: 20px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 4px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: #f8f9fa;
  color: #333;
}

.guide-body {
  padding: 24px;
}

.guide-section {
  margin-bottom: 32px;
}

.guide-section:last-child {
  margin-bottom: 0;
}

.guide-section h4 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 16px;
  font-weight: 600;
}

.guide-section p {
  margin: 0 0 12px 0;
  color: #666;
  line-height: 1.6;
}

.guide-section ul {
  margin: 0 0 12px 0;
  padding-left: 20px;
  color: #666;
}

.guide-section li {
  margin-bottom: 8px;
}

.guide-steps {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.step {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.step-number {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 14px;
  flex-shrink: 0;
}

.step-content h5 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 14px;
  font-weight: 600;
}

.step-content p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.tips {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tip {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #28a745;
}

.tip-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.tip-content {
  color: #666;
  font-size: 14px;
  line-height: 1.5;
}

.tip-content strong {
  color: #333;
}

.warnings {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.warning {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px 16px;
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 6px;
  color: #856404;
  font-size: 14px;
}

.warning-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.guide-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px 24px 24px;
  border-top: 1px solid #e9ecef;
}

.dont-show-again {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #666;
  font-size: 14px;
  user-select: none;
}

.dont-show-again input[type="checkbox"] {
  margin: 0;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* 移动端优化 */
@media (max-width: 768px) {
  .user-guide {
    padding: 10px;
  }
  
  .guide-content {
    max-width: 100%;
    max-height: 95vh;
  }
  
  .guide-header {
    padding: 20px 20px 12px 20px;
  }
  
  .guide-header h3 {
    font-size: 18px;
  }
  
  .guide-body {
    padding: 20px;
  }
  
  .guide-section {
    margin-bottom: 24px;
  }
  
  .guide-steps {
    gap: 16px;
  }
  
  .step {
    gap: 12px;
  }
  
  .step-number {
    width: 28px;
    height: 28px;
    font-size: 12px;
  }
  
  .tips {
    gap: 12px;
  }
  
  .tip {
    padding: 12px;
  }
  
  .guide-footer {
    padding: 12px 20px 20px 20px;
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .btn {
    width: 100%;
    justify-content: center;
  }
}
</style>