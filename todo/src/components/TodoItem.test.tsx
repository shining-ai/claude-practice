import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TodoItem } from './TodoItem'
import { Todo } from '../types/todo'

const makeTodo = (overrides: Partial<Todo> = {}): Todo => ({
  id: 'todo-1',
  title: 'Test Task',
  description: 'Test description',
  completed: false,
  priority: 'medium',
  category: 'Work',
  dueDate: null,
  createdAt: Date.now(),
  ...overrides,
})

const defaultProps = {
  onToggleComplete: vi.fn(),
  onDelete: vi.fn(),
  onUpdate: vi.fn(),
}

describe('TodoItem', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders title, description, priority, and category', () => {
    render(<TodoItem todo={makeTodo()} {...defaultProps} />)

    expect(screen.getByText('Test Task')).toBeInTheDocument()
    expect(screen.getByText('Test description')).toBeInTheDocument()
    expect(screen.getByText('medium')).toBeInTheDocument()
    expect(screen.getByText('Work')).toBeInTheDocument()
  })

  it('does not render description when it is empty', () => {
    render(<TodoItem todo={makeTodo({ description: '' })} {...defaultProps} />)

    expect(screen.queryByRole('paragraph')).not.toBeInTheDocument()
  })

  it('renders due date when provided', () => {
    render(<TodoItem todo={makeTodo({ dueDate: '2025-06-15' })} {...defaultProps} />)

    expect(screen.getByText(/Jun 15, 2025/i)).toBeInTheDocument()
  })

  it('does not render due date when dueDate is null', () => {
    render(<TodoItem todo={makeTodo({ dueDate: null })} {...defaultProps} />)

    expect(screen.queryByText(/jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec/i)).not.toBeInTheDocument()
  })

  it('calls onToggleComplete with the todo id when checkbox is clicked', async () => {
    const user = userEvent.setup()
    render(<TodoItem todo={makeTodo()} {...defaultProps} />)

    await user.click(screen.getByRole('checkbox'))

    expect(defaultProps.onToggleComplete).toHaveBeenCalledOnce()
    expect(defaultProps.onToggleComplete).toHaveBeenCalledWith('todo-1')
  })

  it('shows checkbox as checked for completed todo', () => {
    render(<TodoItem todo={makeTodo({ completed: true })} {...defaultProps} />)

    expect(screen.getByRole('checkbox')).toBeChecked()
  })

  it('shows checkbox as unchecked for incomplete todo', () => {
    render(<TodoItem todo={makeTodo({ completed: false })} {...defaultProps} />)

    expect(screen.getByRole('checkbox')).not.toBeChecked()
  })

  it('switches to edit mode when edit button is clicked', async () => {
    const user = userEvent.setup()
    render(<TodoItem todo={makeTodo()} {...defaultProps} />)

    await user.click(screen.getByTitle('Edit'))

    expect(screen.getByPlaceholderText('Title')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Description')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
  })

  it('calls onUpdate with edited title and description when Save is clicked', async () => {
    const user = userEvent.setup()
    render(<TodoItem todo={makeTodo()} {...defaultProps} />)

    await user.click(screen.getByTitle('Edit'))
    const titleInput = screen.getByPlaceholderText('Title')
    await user.clear(titleInput)
    await user.type(titleInput, 'Updated Task')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(defaultProps.onUpdate).toHaveBeenCalledWith('todo-1', {
      title: 'Updated Task',
      description: 'Test description',
    })
  })

  it('does not call onUpdate when Save is clicked with empty title', async () => {
    const user = userEvent.setup()
    render(<TodoItem todo={makeTodo()} {...defaultProps} />)

    await user.click(screen.getByTitle('Edit'))
    await user.clear(screen.getByPlaceholderText('Title'))
    await user.click(screen.getByRole('button', { name: 'Save' }))

    expect(defaultProps.onUpdate).not.toHaveBeenCalled()
  })

  it('restores original values and exits edit mode when Cancel is clicked', async () => {
    const user = userEvent.setup()
    render(<TodoItem todo={makeTodo()} {...defaultProps} />)

    await user.click(screen.getByTitle('Edit'))
    await user.clear(screen.getByPlaceholderText('Title'))
    await user.type(screen.getByPlaceholderText('Title'), 'Changed')
    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(defaultProps.onUpdate).not.toHaveBeenCalled()
    expect(screen.getByText('Test Task')).toBeInTheDocument()
    expect(screen.queryByPlaceholderText('Title')).not.toBeInTheDocument()
  })

  it('calls onDelete when delete is confirmed', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<TodoItem todo={makeTodo()} {...defaultProps} />)

    await user.click(screen.getByTitle('Delete'))

    expect(defaultProps.onDelete).toHaveBeenCalledWith('todo-1')
  })

  it('does not call onDelete when delete is cancelled', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    render(<TodoItem todo={makeTodo()} {...defaultProps} />)

    await user.click(screen.getByTitle('Delete'))

    expect(defaultProps.onDelete).not.toHaveBeenCalled()
  })

  it('applies overdue class for incomplete todo with past due date', () => {
    const { container } = render(
      <TodoItem todo={makeTodo({ dueDate: '2020-01-01', completed: false })} {...defaultProps} />,
    )

    expect(container.firstChild).toHaveClass('overdue')
  })

  it('does not apply overdue class for completed todo with past due date', () => {
    const { container } = render(
      <TodoItem todo={makeTodo({ dueDate: '2020-01-01', completed: true })} {...defaultProps} />,
    )

    expect(container.firstChild).not.toHaveClass('overdue')
  })
})
