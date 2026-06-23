<script setup lang="ts">
import { computed } from 'vue'
import type { Todo } from '../api/todos'
import { formatAge } from '../utils/age'

const props = defineProps<{
  todo: Todo
  pendingAction: 'toggle' | 'remove' | null
}>()

const emit = defineEmits<{
  toggle: [todo: Todo]
  remove: [todo: Todo]
}>()

const age = computed(() => formatAge(props.todo.created_at))

const ageLabel = computed(() => {
  if (props.pendingAction === 'toggle') return 'updating…'
  return props.todo.completed ? 'drifted away' : `carried for ${age.value}`
})

const removeLabel = computed(() => (props.pendingAction === 'remove' ? 'removing…' : 'remove'))
</script>

<template>
  <li class="todo-item" :class="{ done: todo.completed, pending: !!pendingAction }">
    <label>
      <input
        type="checkbox"
        :checked="todo.completed"
        :disabled="!!pendingAction"
        @change="emit('toggle', todo)"
      />
      <span class="balloon" aria-hidden="true"></span>
      <span class="todo-text">
        <span class="todo-title">{{ todo.title }}</span>
        <span class="todo-age" :class="{ busy: pendingAction === 'toggle' }">{{ ageLabel }}</span>
      </span>
    </label>
    <button
      type="button"
      class="balloon-button"
      aria-label="Remove todo"
      :disabled="!!pendingAction"
      @click="emit('remove', todo)"
    >
      {{ removeLabel }}
    </button>
  </li>
</template>
