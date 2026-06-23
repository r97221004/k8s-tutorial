<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  submit: [title: string]
}>()

const title = ref('')

function submit() {
  const trimmed = title.value.trim()
  if (!trimmed) return
  emit('submit', trimmed)
  title.value = ''
}
</script>

<template>
  <form class="todo-form" @submit.prevent="submit">
    <input
      v-model="title"
      type="text"
      maxlength="200"
      placeholder="Add something to carry…"
      aria-label="Todo title"
    />
    <button type="submit" :disabled="!title.trim()">Add</button>
  </form>
</template>
