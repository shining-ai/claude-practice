import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TodoForm } from './TodoForm'

describe('TodoForm', () => {
  it('renders all form fields and submit button', () => {
    render(<TodoForm onAddTodo={vi.fn()} />)

    expect(screen.getByLabelText(/title/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/priority/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/category/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/due date/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /add todo/i })).toBeInTheDocument()
  })

  it('calls onAddTodo with all entered values on submission', async () => {
    const user = userEvent.setup()
    const onAddTodo = vi.fn()
    render(<TodoForm onAddTodo={onAddTodo} />)

    await user.type(screen.getByLabelText(/title/i), 'New Task')
    await user.type(screen.getByLabelText(/description/i), 'Task description')
    await user.selectOptions(screen.getByLabelText(/priority/i), 'high')
    await user.type(screen.getByLabelText(/category/i), 'Work')
    await user.click(screen.getByRole('button', { name: /add todo/i }))

    expect(onAddTodo).toHaveBeenCalledOnce()
    expect(onAddTodo).toHaveBeenCalledWith('New Task', 'Task description', 'high', 'Work', null)
  })

  it('does not call onAddTodo when title is empty', async () => {
    const user = userEvent.setup()
    const onAddTodo = vi.fn()
    render(<TodoForm onAddTodo={onAddTodo} />)

    await user.click(screen.getByRole('button', { name: /add todo/i }))

    expect(onAddTodo).not.toHaveBeenCalled()
  })

  it('does not call onAddTodo when title is only whitespace', async () => {
    const user = userEvent.setup()
    const onAddTodo = vi.fn()
    render(<TodoForm onAddTodo={onAddTodo} />)

    await user.type(screen.getByLabelText(/title/i), '   ')
    await user.click(screen.getByRole('button', { name: /add todo/i }))

    expect(onAddTodo).not.toHaveBeenCalled()
  })

  it('resets all fields to defaults after successful submission', async () => {
    const user = userEvent.setup()
    render(<TodoForm onAddTodo={vi.fn()} />)

    await user.type(screen.getByLabelText(/title/i), 'Task')
    await user.type(screen.getByLabelText(/description/i), 'Desc')
    await user.selectOptions(screen.getByLabelText(/priority/i), 'high')
    await user.type(screen.getByLabelText(/category/i), 'Work')
    await user.click(screen.getByRole('button', { name: /add todo/i }))

    expect(screen.getByLabelText(/title/i)).toHaveValue('')
    expect(screen.getByLabelText(/description/i)).toHaveValue('')
    expect(screen.getByLabelText(/priority/i)).toHaveValue('medium')
    expect(screen.getByLabelText(/category/i)).toHaveValue('')
  })

  it('uses "General" as category when category field is left empty', async () => {
    const user = userEvent.setup()
    const onAddTodo = vi.fn()
    render(<TodoForm onAddTodo={onAddTodo} />)

    await user.type(screen.getByLabelText(/title/i), 'Task')
    await user.click(screen.getByRole('button', { name: /add todo/i }))

    expect(onAddTodo).toHaveBeenCalledWith('Task', '', 'medium', 'General', null)
  })

  it('passes null for dueDate when due date field is left empty', async () => {
    const user = userEvent.setup()
    const onAddTodo = vi.fn()
    render(<TodoForm onAddTodo={onAddTodo} />)

    await user.type(screen.getByLabelText(/title/i), 'Task')
    await user.click(screen.getByRole('button', { name: /add todo/i }))

    const [, , , , dueDate] = onAddTodo.mock.calls[0]
    expect(dueDate).toBeNull()
  })
})
