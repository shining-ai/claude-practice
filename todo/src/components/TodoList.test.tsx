import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TodoList } from './TodoList'
import { Todo } from '../types/todo'

const makeTodo = (overrides: Partial<Todo> = {}): Todo => ({
  id: 'todo-1',
  title: 'Test Task',
  description: '',
  completed: false,
  priority: 'medium',
  category: 'General',
  dueDate: null,
  createdAt: Date.now(),
  ...overrides,
})

const defaultHandlers = {
  onToggleComplete: vi.fn(),
  onDelete: vi.fn(),
  onUpdate: vi.fn(),
}

describe('TodoList', () => {
  it('shows empty state message when there are no todos', () => {
    render(<TodoList todos={[]} {...defaultHandlers} />)

    expect(screen.getByText(/no todos yet/i)).toBeInTheDocument()
  })

  it('renders each todo in the list', () => {
    const todos = [
      makeTodo({ id: 'todo-1', title: 'First Task' }),
      makeTodo({ id: 'todo-2', title: 'Second Task' }),
      makeTodo({ id: 'todo-3', title: 'Third Task' }),
    ]
    render(<TodoList todos={todos} {...defaultHandlers} />)

    expect(screen.getByText('First Task')).toBeInTheDocument()
    expect(screen.getByText('Second Task')).toBeInTheDocument()
    expect(screen.getByText('Third Task')).toBeInTheDocument()
  })

  it('does not show empty state message when there are todos', () => {
    render(<TodoList todos={[makeTodo()]} {...defaultHandlers} />)

    expect(screen.queryByText(/no todos yet/i)).not.toBeInTheDocument()
  })
})
