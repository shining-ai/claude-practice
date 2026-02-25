import { useState, useEffect, useCallback } from 'react'
import { Todo } from '../types/todo'
import { loadTodos, saveTodos } from '../utils/storage'

export const useTodos = () => {
  const [todos, setTodos] = useState<Todo[]>([])
  const [isLoading, setIsLoading] = useState(true)

  // Load todos from localStorage on mount
  useEffect(() => {
    const loaded = loadTodos()
    setTodos(loaded)
    setIsLoading(false)
  }, [])

  // Auto-save to localStorage whenever todos change
  useEffect(() => {
    if (!isLoading) {
      saveTodos(todos)
    }
  }, [todos, isLoading])

  const addTodo = useCallback((title: string, description: string, priority: 'low' | 'medium' | 'high', category: string, dueDate: string | null) => {
    const newTodo: Todo = {
      id: `todo-${(todos.length ? Math.max(...todos.map(t => parseInt(t.id.split('-')[1]) || 0)) : 0) + 1}`,
      title,
      description,
      completed: false,
      priority,
      category,
      dueDate,
      createdAt: Date.now(),
    }
    setTodos(prev => [newTodo, ...prev])
    return newTodo
  }, [todos.length])

  const deleteTodo = useCallback((id: string) => {
    setTodos(prev => prev.filter(todo => todo.id !== id))
  }, [])

  const toggleComplete = useCallback((id: string) => {
    setTodos(prev => prev.map(todo =>
      todo.id === id ? { ...todo, completed: !todo.completed } : todo
    ))
  }, [])

  const updateTodo = useCallback((id: string, updates: Partial<Omit<Todo, 'id' | 'createdAt'>>) => {
    setTodos(prev => prev.map(todo =>
      todo.id === id ? { ...todo, ...updates } : todo
    ))
  }, [])

  return {
    todos,
    isLoading,
    addTodo,
    deleteTodo,
    toggleComplete,
    updateTodo,
    setTodos,
  }
}
