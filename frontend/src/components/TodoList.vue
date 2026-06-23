<script setup lang="ts">
import type { Todo } from '../api/todos'
import TodoItem from './TodoItem.vue'

defineProps<{
  todos: Todo[]
  pendingIds: Set<number>
}>()

const emit = defineEmits<{
  toggle: [todo: Todo]
  remove: [todo: Todo]
}>()
</script>

<template>
  <div v-if="todos.length === 0" class="empty">
    <p class="empty-title">The sky is empty</p>
    <p class="empty-body">Add something above, and it'll wait here until you're ready to let it go.</p>
  </div>
  <ul v-else class="todo-list">
    <TodoItem
      v-for="todo in todos"
      :key="todo.id"
      :todo="todo"
      :pending="pendingIds.has(todo.id)"
      @toggle="emit('toggle', $event)"
      @remove="emit('remove', $event)"
    />
  </ul>
</template>
