import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TodoFilters } from './TodoFilters'
import { FilterOptions, SortBy, Todo } from '../types/todo'

const makeTodo = (overrides: Partial<Todo> = {}): Todo => ({
  id: 'todo-1',
  title: 'Task',
  description: '',
  completed: false,
  priority: 'medium',
  category: 'Work',
  dueDate: null,
  createdAt: Date.now(),
  ...overrides,
})

const defaultFilters: FilterOptions = {
  priority: 'all',
  category: 'all',
  showCompleted: true,
  showIncompleted: true,
}

const defaultProps = {
  todos: [makeTodo()],
  filters: defaultFilters,
  sortBy: 'created' as SortBy,
  onFilterChange: vi.fn(),
  onSortChange: vi.fn(),
}

describe('TodoFilters', () => {
  it('renders priority filter with all options', () => {
    render(<TodoFilters {...defaultProps} />)

    const select = screen.getByLabelText(/priority/i)
    const prioritySelect = within(select as HTMLElement)
    expect(prioritySelect.getByRole('option', { name: 'All' })).toBeInTheDocument()
    expect(prioritySelect.getByRole('option', { name: 'Low' })).toBeInTheDocument()
    expect(prioritySelect.getByRole('option', { name: 'Medium' })).toBeInTheDocument()
    expect(prioritySelect.getByRole('option', { name: 'High' })).toBeInTheDocument()
  })

  it('calls onFilterChange with selected priority', async () => {
    const user = userEvent.setup()
    const onFilterChange = vi.fn()
    render(<TodoFilters {...defaultProps} onFilterChange={onFilterChange} />)

    await user.selectOptions(screen.getByLabelText(/priority/i), 'high')

    expect(onFilterChange).toHaveBeenCalledWith({ ...defaultFilters, priority: 'high' })
  })

  it('renders category filter with categories from todos', () => {
    const todos = [
      makeTodo({ id: 'todo-1', category: 'Work' }),
      makeTodo({ id: 'todo-2', category: 'Personal' }),
    ]
    render(<TodoFilters {...defaultProps} todos={todos} />)

    expect(screen.getByRole('option', { name: 'Work' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Personal' })).toBeInTheDocument()
  })

  it('calls onFilterChange with selected category', async () => {
    const user = userEvent.setup()
    const onFilterChange = vi.fn()
    const todos = [makeTodo({ category: 'Work' }), makeTodo({ id: 'todo-2', category: 'Personal' })]
    render(<TodoFilters {...defaultProps} todos={todos} onFilterChange={onFilterChange} />)

    await user.selectOptions(screen.getByLabelText(/category/i), 'Personal')

    expect(onFilterChange).toHaveBeenCalledWith({ ...defaultFilters, category: 'Personal' })
  })

  it('calls onSortChange when sort option is changed', async () => {
    const user = userEvent.setup()
    const onSortChange = vi.fn()
    render(<TodoFilters {...defaultProps} onSortChange={onSortChange} />)

    await user.selectOptions(screen.getByLabelText(/sort by/i), 'priority')

    expect(onSortChange).toHaveBeenCalledWith('priority')
  })

  it('calls onFilterChange when Completed checkbox is toggled', async () => {
    const user = userEvent.setup()
    const onFilterChange = vi.fn()
    render(<TodoFilters {...defaultProps} onFilterChange={onFilterChange} />)

    const completedCheckbox = screen.getByRole('checkbox', { name: /completed/i })
    await user.click(completedCheckbox)

    expect(onFilterChange).toHaveBeenCalledWith({ ...defaultFilters, showCompleted: false })
  })

  it('calls onFilterChange when Incomplete checkbox is toggled', async () => {
    const user = userEvent.setup()
    const onFilterChange = vi.fn()
    render(<TodoFilters {...defaultProps} onFilterChange={onFilterChange} />)

    const incompleteCheckbox = screen.getByRole('checkbox', { name: /incomplete/i })
    await user.click(incompleteCheckbox)

    expect(onFilterChange).toHaveBeenCalledWith({ ...defaultFilters, showIncompleted: false })
  })

  it('resets all filters and sort to defaults when Clear Filters is clicked', async () => {
    const user = userEvent.setup()
    const onFilterChange = vi.fn()
    const onSortChange = vi.fn()
    const activeFilters: FilterOptions = {
      priority: 'high',
      category: 'Work',
      showCompleted: false,
      showIncompleted: true,
    }
    render(
      <TodoFilters
        {...defaultProps}
        filters={activeFilters}
        sortBy="priority"
        onFilterChange={onFilterChange}
        onSortChange={onSortChange}
      />,
    )

    await user.click(screen.getByRole('button', { name: /clear filters/i }))

    expect(onFilterChange).toHaveBeenCalledWith({
      priority: 'all',
      category: 'all',
      showCompleted: true,
      showIncompleted: true,
    })
    expect(onSortChange).toHaveBeenCalledWith('created')
  })
})
