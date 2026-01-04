import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Search from './pages/Search.vue'
import Settings from './pages/Settings.vue'
import Report from './pages/Report.vue'
import Edl from './pages/Edl.vue'
import Admin from './pages/Admin.vue'
import './styles/tailwind.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'search', component: Search },
    { path: '/settings', name: 'settings', component: Settings },
    { path: '/report', name: 'report', component: Report },
    { path: '/edl', name: 'edl', component: Edl },
    { path: '/admin', name: 'admin', component: Admin }
  ]
})

const app = createApp(App)
app.use(router)
app.mount('#app')
