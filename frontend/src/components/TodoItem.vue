<script setup lang="ts">
import type { Todo } from '../api/todos'

defineProps<{
  todo: Todo
}>()

const emit = defineEmits<{
  toggle: [todo: Todo]
  remove: [todo: Todo]
}>()
</script>

<template>
  <li class="todo-item" :class="{ done: todo.completed }">
    <label>
      <input type="checkbox" :checked="todo.completed" @change="emit('toggle', todo)" />
      <span class="todo-title">{{ todo.title }}</span>
    </label>
    <button type="button" class="danger-button" aria-label="Delete todo" @click="emit('remove', todo)">
      Delete
    </button>
  </li>
</template>
