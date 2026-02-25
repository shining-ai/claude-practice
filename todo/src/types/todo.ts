export type Priority = 'low' | 'medium' | 'high'

export interface Todo {
  id: string
  title: string
  description: string
  completed: boolean
  priority: Priority
  category: string
  dueDate: string | null
  createdAt: number
}

export interface FilterOptions {
  priority?: Priority | 'all'
  category?: string | 'all'
  showCompleted: boolean
  showIncompleted: boolean
}

export type SortBy = 'dueDate' | 'priority' | 'created' | 'title'
