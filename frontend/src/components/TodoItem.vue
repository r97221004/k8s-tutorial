<script setup lang="ts">
import { computed } from 'vue'
import type { Todo } from '../api/todos'
import { formatAge } from '../utils/age'

const props = defineProps<{
  todo: Todo
  pending: boolean
}>()

const emit = defineEmits<{
  toggle: [todo: Todo]
  remove: [todo: Todo]
}>()

const age = computed(() => formatAge(props.todo.created_at))
</script>

<template>
  <li class="todo-item" :class="{ done: todo.completed, pending }">
    <label>
      <input
        type="checkbox"
        :checked="todo.completed"
        :disabled="pending"
        @change="emit('toggle', todo)"
      />
      <span class="balloon" aria-hidden="true"></span>
      <span class="todo-text">
        <span class="todo-title">{{ todo.title }}</span>
        <span class="todo-age">{{ todo.completed ? 'drifted away' : `carried for ${age}` }}</span>
      </span>
    </label>
    <button
      type="button"
      class="balloon-button"
      aria-label="Remove todo"
      :disabled="pending"
      @click="emit('remove', todo)"
    >
      remove
    </button>
  </li>
</template>
