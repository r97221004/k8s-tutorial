export interface Todo {
  id: number
  title: string
  completed: boolean
  created_at: string
}

export interface Health {
  status: string
  version: string
}

const API_BASE = '/api'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Request failed with ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export function getHealth(): Promise<Health> {
  return request<Health>('/healthz')
}

export function listTodos(): Promise<Todo[]> {
  return request<Todo[]>('/todos')
}

export function createTodo(title: string): Promise<Todo> {
  return request<Todo>('/todos', {
    method: 'POST',
    body: JSON.stringify({ title })
  })
}

export function updateTodo(id: number, updates: Partial<Pick<Todo, 'title' | 'completed'>>): Promise<Todo> {
  return request<Todo>(`/todos/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(updates)
  })
}

export function deleteTodo(id: number): Promise<void> {
  return request<void>(`/todos/${id}`, { method: 'DELETE' })
}
