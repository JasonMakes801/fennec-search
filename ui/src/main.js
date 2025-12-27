import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Search from './pages/Search.vue'
import Settings from './pages/Settings.vue'
import Report from './pages/Report.vue'
import './styles/tailwind.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'search', component: Search },
    { path: '/settings', name: 'settings', component: Settings },
    { path: '/report', name: 'report', component: Report }
  ]
})

const app = createApp(App)
app.use(router)
app.mount('#app')
