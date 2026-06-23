<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  createTodo,
  deleteTodo,
  getHealth,
  listTodos,
  updateTodo,
  type Health,
  type Todo
} from './api/todos'
import TodoForm from './components/TodoForm.vue'
import TodoList from './components/TodoList.vue'

const todos = ref<Todo[]>([])
const health = ref<Health | null>(null)
const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)

const totalCount = computed(() => todos.value.length)
const completedCount = computed(() => todos.value.filter((todo) => todo.completed).length)
const openCount = computed(() => totalCount.value - completedCount.value)
const statusLabel = computed(() => {
  if (loading.value) return 'Syncing'
  if (error.value) return 'Needs attention'
  return health.value ? `API ${health.value.status} · v${health.value.version}` : 'Ready'
})

async function load() {
  loading.value = true
  error.value = null
  try {
    const [todoResult, healthResult] = await Promise.all([listTodos(), getHealth()])
    todos.value = todoResult
    health.value = healthResult
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to load todos'
  } finally {
    loading.value = false
  }
}

async function addTodo(title: string) {
  saving.value = true
  error.value = null
  try {
    const created = await createTodo(title)
    todos.value = [created, ...todos.value]
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to add todo'
  } finally {
    saving.value = false
  }
}

async function toggleTodo(todo: Todo) {
  error.value = null
  try {
    const updated = await updateTodo(todo.id, { completed: !todo.completed })
    todos.value = todos.value.map((item) => (item.id === updated.id ? updated : item))
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to update todo'
  }
}

async function removeTodo(todo: Todo) {
  error.value = null
  try {
    await deleteTodo(todo.id)
    todos.value = todos.value.filter((item) => item.id !== todo.id)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to delete todo'
  }
}

onMounted(load)
</script>

<template>
  <main class="shell">
    <section class="hero">
      <div>
        <p class="eyebrow">Kubernetes Capstone</p>
        <h1>Todo Board</h1>
        <p class="subtitle">Vue calls FastAPI, FastAPI persists todos in SQLite on a PVC.</p>
      </div>
      <div class="hero-status" aria-label="Application status">
        <span class="status-dot" :class="{ warning: error }"></span>
        <span>{{ statusLabel }}</span>
      </div>
      <dl class="stats" aria-label="Todo summary">
        <div>
          <dt>Total</dt>
          <dd>{{ totalCount }}</dd>
        </div>
        <div>
          <dt>Open</dt>
          <dd>{{ openCount }}</dd>
        </div>
        <div>
          <dt>Done</dt>
          <dd>{{ completedCount }}</dd>
        </div>
      </dl>
    </section>

    <section class="panel" aria-live="polite">
      <div class="panel-header">
        <div>
          <p class="section-label">Workspace</p>
          <h2>Deployment tasks</h2>
        </div>
        <span class="pill">{{ openCount }} open</span>
      </div>
      <TodoForm @submit="addTodo" />
      <p v-if="saving" class="hint">Saving...</p>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="loading" class="hint">Loading todos...</p>
      <TodoList v-else :todos="todos" @toggle="toggleTodo" @remove="removeTodo" />
    </section>
  </main>
</template>
