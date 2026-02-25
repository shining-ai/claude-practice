import { useMemo, useState } from 'react'
import { useTodos } from '../hooks/useTodos'
import { FilterOptions, SortBy } from '../types/todo'
import { TodoForm } from './TodoForm'
import { TodoList } from './TodoList'
import { TodoFilters } from './TodoFilters'
import styles from './TodoApp.module.css'

export const TodoApp = () => {
  const { todos, addTodo, deleteTodo, toggleComplete, updateTodo } = useTodos()
  const [filters, setFilters] = useState<FilterOptions>({
    priority: 'all',
    category: 'all',
    showCompleted: true,
    showIncompleted: true,
  })
  const [sortBy, setSortBy] = useState<SortBy>('created')

  const filteredAndSortedTodos = useMemo(() => {
    let filtered = todos.filter(todo => {
      // Filter by completion status
      if (!filters.showCompleted && todo.completed) return false
      if (!filters.showIncompleted && !todo.completed) return false

      // Filter by priority
      if (filters.priority && filters.priority !== 'all' && todo.priority !== filters.priority) {
        return false
      }

      // Filter by category
      if (filters.category && filters.category !== 'all' && todo.category !== filters.category) {
        return false
      }

      return true
    })

    // Sort todos
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'dueDate':
          if (!a.dueDate && !b.dueDate) return 0
          if (!a.dueDate) return 1
          if (!b.dueDate) return -1
          return new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime()

        case 'priority':
          const priorityOrder = { high: 0, medium: 1, low: 2 }
          return priorityOrder[a.priority] - priorityOrder[b.priority]

        case 'title':
          return a.title.localeCompare(b.title)

        case 'created':
        default:
          return b.createdAt - a.createdAt
      }
    })

    return filtered
  }, [todos, filters, sortBy])

  const stats = {
    total: todos.length,
    completed: todos.filter(t => t.completed).length,
    incomplete: todos.filter(t => !t.completed).length,
  }

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <h1>📋 TODO App</h1>
        <div className={styles.stats}>
          <span>Total: {stats.total}</span>
          <span>Completed: {stats.completed}</span>
          <span>Remaining: {stats.incomplete}</span>
        </div>
      </header>

      <main className={styles.main}>
        <TodoForm onAddTodo={addTodo} />

        {todos.length > 0 && (
          <>
            <TodoFilters
              todos={todos}
              filters={filters}
              sortBy={sortBy}
              onFilterChange={setFilters}
              onSortChange={setSortBy}
            />
            <div className={styles.resultInfo}>
              Showing {filteredAndSortedTodos.length} of {todos.length} TODOs
            </div>
          </>
        )}

        <TodoList
          todos={filteredAndSortedTodos}
          onToggleComplete={toggleComplete}
          onDelete={deleteTodo}
          onUpdate={updateTodo}
        />
      </main>
    </div>
  )
}
