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
import MoonScene from './components/MoonScene.vue'
import TodoForm from './components/TodoForm.vue'
import TodoList from './components/TodoList.vue'

const todos = ref<Todo[]>([])
const health = ref<Health | null>(null)
const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)

const totalCount = computed(() => todos.value.length)
const completedCount = computed(() => todos.value.filter((todo) => todo.completed).length)
const pendingCount = computed(() => totalCount.value - completedCount.value)
const statusLabel = computed(() => {
  if (loading.value) return 'gathering your tasks…'
  if (error.value) return 'lost the thread'
  return 'all caught up'
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
      <div class="hero-text">
        <h1>Todo <em>Board</em></h1>
        <p class="subtitle">
          A small list of things to carry. Tick one off, and let it drift away like a balloon.
        </p>
      </div>
      <MoonScene class="moon-scene" />

      <div class="hero-foot">
        <dl class="stats" aria-label="Todo summary">
          <div>
            <dt>Total</dt>
            <dd>{{ totalCount }}</dd>
          </div>
          <div>
            <dt>Pending</dt>
            <dd>{{ pendingCount }}</dd>
          </div>
          <div>
            <dt>Done</dt>
            <dd>{{ completedCount }}</dd>
          </div>
        </dl>
        <div class="hero-status" aria-label="Application status">
          <span class="status-dot" :class="{ warning: error }"></span>
          <span>{{ statusLabel }}</span>
        </div>
      </div>
    </section>

    <section class="panel" aria-live="polite">
      <div class="panel-header">
        <h2>Today's list</h2>
        <span class="pill">{{ pendingCount }} still tied</span>
      </div>
      <TodoForm @submit="addTodo" />
      <p v-if="saving" class="hint">Adding…</p>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="loading" class="hint">Gathering your list…</p>
      <TodoList v-else :todos="todos" @toggle="toggleTodo" @remove="removeTodo" />
    </section>
  </main>
</template>
