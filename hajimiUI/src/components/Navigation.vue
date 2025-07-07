<template>
  <nav class="navigation">
    <div class="nav-container">
      <div class="nav-brand">
        <span class="logo">🤖</span>
        <span class="brand-text">Hajimi</span>
      </div>
      
      <div class="nav-links">
        <router-link 
          to="/" 
          class="nav-link"
          :class="{ active: $route.path === '/' }"
        >
          <span class="nav-icon">📊</span>
          <span class="nav-text">仪表盘</span>
        </router-link>
        
        <router-link 
          to="/backends" 
          class="nav-link"
          :class="{ active: $route.path === '/backends' }"
        >
          <span class="nav-icon">🔧</span>
          <span class="nav-text">后端管理</span>
          <span v-if="backendStore.connectedBackendsCount > 0" class="nav-badge">
            {{ backendStore.connectedBackendsCount }}
          </span>
        </router-link>
      </div>
      
      <div class="nav-actions">
        <BackendSwitcher class="nav-switcher" />
      </div>
    </div>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useBackendStore } from '@/stores/backend'
import BackendSwitcher from './backend/BackendSwitcher.vue'

const route = useRoute()
const backendStore = useBackendStore()
</script>

<style scoped>
.navigation {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 1000;
  backdrop-filter: blur(10px);
}

.nav-container {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  color: white;
  font-weight: 600;
  font-size: 1.2rem;
}

.logo {
  font-size: 24px;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

.brand-text {
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.nav-links {
  display: flex;
  gap: 8px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  transition: all 0.3s ease;
  font-weight: 500;
  position: relative;
  backdrop-filter: blur(5px);
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.15);
  color: white;
  transform: translateY(-1px);
}

.nav-link.active {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.nav-icon {
  font-size: 16px;
}

.nav-text {
  font-size: 14px;
}

.nav-badge {
  background: #ff4757;
  color: white;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
  font-weight: bold;
}

.nav-actions {
  display: flex;
  align-items: center;
}

.nav-switcher {
  transform: scale(0.9);
}

/* 移动端优化 */
@media (max-width: 768px) {
  .nav-container {
    padding: 10px 16px;
  }
  
  .nav-brand {
    font-size: 1rem;
    gap: 8px;
  }
  
  .logo {
    font-size: 20px;
  }
  
  .nav-links {
    gap: 4px;
  }
  
  .nav-link {
    padding: 6px 12px;
  }
  
  .nav-text {
    font-size: 12px;
  }
  
  .nav-icon {
    font-size: 14px;
  }
  
  .nav-switcher {
    transform: scale(0.8);
  }
}

@media (max-width: 480px) {
  .nav-container {
    padding: 8px 12px;
  }
  
  .nav-brand .brand-text {
    display: none;
  }
  
  .nav-text {
    display: none;
  }
  
  .nav-link {
    padding: 6px 8px;
  }
  
  .nav-switcher {
    transform: scale(0.7);
  }
}
</style>