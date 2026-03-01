import { describe, it, expect, beforeEach } from 'vitest'
import { saveTodos, loadTodos, clearTodos } from './storage'
import { Todo } from '../types/todo'

const makeTodo = (overrides: Partial<Todo> = {}): Todo => ({
  id: 'todo-1',
  title: 'Test Todo',
  description: 'Description',
  completed: false,
  priority: 'medium',
  category: 'Work',
  dueDate: null,
  createdAt: 1000000,
  ...overrides,
})

describe('storage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  describe('loadTodos', () => {
    it('returns empty array when localStorage is empty', () => {
      expect(loadTodos()).toEqual([])
    })

    it('returns stored todos', () => {
      const todo = makeTodo()
      localStorage.setItem('todos', JSON.stringify([todo]))

      const result = loadTodos()

      expect(result).toHaveLength(1)
      expect(result[0]).toEqual(todo)
    })

    it('returns multiple stored todos in order', () => {
      const todos = [makeTodo({ id: 'todo-1', title: 'First' }), makeTodo({ id: 'todo-2', title: 'Second' })]
      localStorage.setItem('todos', JSON.stringify(todos))

      const result = loadTodos()

      expect(result).toHaveLength(2)
      expect(result[0].title).toBe('First')
      expect(result[1].title).toBe('Second')
    })

    it('returns empty array when localStorage contains invalid JSON', () => {
      localStorage.setItem('todos', 'invalid-json{{{')

      expect(loadTodos()).toEqual([])
    })
  })

  describe('saveTodos', () => {
    it('saves todos to localStorage as JSON', () => {
      const todo = makeTodo()
      saveTodos([todo])

      const stored = localStorage.getItem('todos')
      expect(stored).not.toBeNull()
      expect(JSON.parse(stored!)).toEqual([todo])
    })

    it('saves empty array', () => {
      saveTodos([])

      expect(JSON.parse(localStorage.getItem('todos')!)).toEqual([])
    })

    it('overwrites previously saved todos', () => {
      saveTodos([makeTodo({ title: 'Old' })])
      saveTodos([makeTodo({ title: 'New' })])

      const stored = JSON.parse(localStorage.getItem('todos')!)
      expect(stored).toHaveLength(1)
      expect(stored[0].title).toBe('New')
    })
  })

  describe('clearTodos', () => {
    it('removes todos from localStorage', () => {
      localStorage.setItem('todos', JSON.stringify([makeTodo()]))
      clearTodos()

      expect(localStorage.getItem('todos')).toBeNull()
    })

    it('does not throw when localStorage is already empty', () => {
      expect(() => clearTodos()).not.toThrow()
    })
  })
})
