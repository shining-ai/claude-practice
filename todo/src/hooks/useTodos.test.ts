import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useTodos } from './useTodos'

describe('useTodos', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('initializes with empty todos and isLoading false', () => {
    const { result } = renderHook(() => useTodos())

    expect(result.current.todos).toEqual([])
    expect(result.current.isLoading).toBe(false)
  })

  it('loads todos from localStorage on mount', () => {
    const stored = [
      {
        id: 'todo-1',
        title: 'Persisted Todo',
        description: '',
        completed: false,
        priority: 'medium',
        category: 'General',
        dueDate: null,
        createdAt: 1000,
      },
    ]
    localStorage.setItem('todos', JSON.stringify(stored))

    const { result } = renderHook(() => useTodos())

    expect(result.current.todos).toHaveLength(1)
    expect(result.current.todos[0].title).toBe('Persisted Todo')
  })

  it('addTodo creates a todo with all specified fields', () => {
    const { result } = renderHook(() => useTodos())

    act(() => {
      result.current.addTodo('Buy milk', 'Organic only', 'high', 'Shopping', '2025-12-31')
    })

    expect(result.current.todos).toHaveLength(1)
    const todo = result.current.todos[0]
    expect(todo.title).toBe('Buy milk')
    expect(todo.description).toBe('Organic only')
    expect(todo.priority).toBe('high')
    expect(todo.category).toBe('Shopping')
    expect(todo.dueDate).toBe('2025-12-31')
    expect(todo.completed).toBe(false)
    expect(todo.id).toMatch(/^todo-\d+$/)
    expect(typeof todo.createdAt).toBe('number')
  })

  it('addTodo accepts null dueDate', () => {
    const { result } = renderHook(() => useTodos())

    act(() => {
      result.current.addTodo('No due date', '', 'low', 'General', null)
    })

    expect(result.current.todos[0].dueDate).toBeNull()
  })

  it('deleteTodo removes only the specified todo', () => {
    const { result } = renderHook(() => useTodos())

    act(() => {
      result.current.addTodo('First', '', 'low', 'General', null)
    })
    act(() => {
      result.current.addTodo('Second', '', 'low', 'General', null)
    })

    const idToDelete = result.current.todos.find(t => t.title === 'First')!.id

    act(() => {
      result.current.deleteTodo(idToDelete)
    })

    expect(result.current.todos).toHaveLength(1)
    expect(result.current.todos[0].title).toBe('Second')
  })

  it('toggleComplete flips completed from false to true and back', () => {
    const { result } = renderHook(() => useTodos())

    act(() => {
      result.current.addTodo('Toggle me', '', 'medium', 'General', null)
    })
    const id = result.current.todos[0].id

    expect(result.current.todos[0].completed).toBe(false)

    act(() => { result.current.toggleComplete(id) })
    expect(result.current.todos[0].completed).toBe(true)

    act(() => { result.current.toggleComplete(id) })
    expect(result.current.todos[0].completed).toBe(false)
  })

  it('updateTodo updates only specified fields and leaves others unchanged', () => {
    const { result } = renderHook(() => useTodos())

    act(() => {
      result.current.addTodo('Original title', 'Original desc', 'low', 'Work', null)
    })
    const id = result.current.todos[0].id

    act(() => {
      result.current.updateTodo(id, { title: 'New title', priority: 'high' })
    })

    const updated = result.current.todos[0]
    expect(updated.title).toBe('New title')
    expect(updated.priority).toBe('high')
    expect(updated.description).toBe('Original desc')
    expect(updated.category).toBe('Work')
  })

  it('persists added todos to localStorage', () => {
    const { result } = renderHook(() => useTodos())

    act(() => {
      result.current.addTodo('Persist me', '', 'medium', 'General', null)
    })

    const stored = JSON.parse(localStorage.getItem('todos') || '[]')
    expect(stored).toHaveLength(1)
    expect(stored[0].title).toBe('Persist me')
  })

  it('persists deletion to localStorage', () => {
    const { result } = renderHook(() => useTodos())

    act(() => {
      result.current.addTodo('Delete me', '', 'medium', 'General', null)
    })
    const id = result.current.todos[0].id

    act(() => {
      result.current.deleteTodo(id)
    })

    const stored = JSON.parse(localStorage.getItem('todos') || '[]')
    expect(stored).toHaveLength(0)
  })
})
