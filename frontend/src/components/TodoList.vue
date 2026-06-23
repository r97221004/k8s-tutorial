<script setup lang="ts">
import type { Todo } from '../api/todos'
import TodoItem from './TodoItem.vue'

defineProps<{
  todos: Todo[]
}>()

const emit = defineEmits<{
  toggle: [todo: Todo]
  remove: [todo: Todo]
}>()
</script>

<template>
  <div v-if="todos.length === 0" class="empty">
    <p class="empty-title">No todos yet</p>
    <p>Add the first deployment task to test the Vue to FastAPI path.</p>
  </div>
  <ul v-else class="todo-list">
    <TodoItem
      v-for="todo in todos"
      :key="todo.id"
      :todo="todo"
      @toggle="emit('toggle', $event)"
      @remove="emit('remove', $event)"
    />
  </ul>
</template>
