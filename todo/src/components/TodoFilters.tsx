import { Todo, Priority, FilterOptions, SortBy } from '../types/todo'
import styles from './TodoFilters.module.css'

interface TodoFiltersProps {
  todos: Todo[]
  filters: FilterOptions
  sortBy: SortBy
  onFilterChange: (filters: FilterOptions) => void
  onSortChange: (sortBy: SortBy) => void
}

export const TodoFilters = ({
  todos,
  filters,
  sortBy,
  onFilterChange,
  onSortChange,
}: TodoFiltersProps) => {
  const categories = Array.from(new Set(todos.map(t => t.category)))
  const priorities: Priority[] = ['low', 'medium', 'high']

  const handlePriorityChange = (value: string) => {
    onFilterChange({
      ...filters,
      priority: value === 'all' ? 'all' : (value as Priority),
    })
  }

  const handleCategoryChange = (value: string) => {
    onFilterChange({
      ...filters,
      category: value === 'all' ? 'all' : value,
    })
  }

  const handleShowCompletedChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      ...filters,
      showCompleted: e.target.checked,
    })
  }

  const handleShowIncompleteChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      ...filters,
      showIncompleted: e.target.checked,
    })
  }

  const handleClearFilters = () => {
    onFilterChange({
      priority: 'all',
      category: 'all',
      showCompleted: true,
      showIncompleted: true,
    })
    onSortChange('created')
  }

  return (
    <div className={styles.filters}>
      <div className={styles.filterGroup}>
        <label htmlFor="priority-filter">Priority:</label>
        <select
          id="priority-filter"
          value={filters.priority || 'all'}
          onChange={(e) => handlePriorityChange(e.target.value)}
        >
          <option value="all">All</option>
          {priorities.map(p => (
            <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
          ))}
        </select>
      </div>

      {categories.length > 0 && (
        <div className={styles.filterGroup}>
          <label htmlFor="category-filter">Category:</label>
          <select
            id="category-filter"
            value={filters.category || 'all'}
            onChange={(e) => handleCategoryChange(e.target.value)}
          >
            <option value="all">All</option>
            {categories.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      )}

      <div className={styles.filterGroup}>
        <label htmlFor="sort-filter">Sort by:</label>
        <select
          id="sort-filter"
          value={sortBy}
          onChange={(e) => onSortChange(e.target.value as SortBy)}
        >
          <option value="created">Created</option>
          <option value="dueDate">Due Date</option>
          <option value="priority">Priority</option>
          <option value="title">Title</option>
        </select>
      </div>

      <div className={styles.statusGroup}>
        <label>
          <input
            type="checkbox"
            checked={filters.showIncompleted}
            onChange={handleShowIncompleteChange}
          />
          Incomplete
        </label>
        <label>
          <input
            type="checkbox"
            checked={filters.showCompleted}
            onChange={handleShowCompletedChange}
          />
          Completed
        </label>
      </div>

      <button onClick={handleClearFilters} className={styles.clearBtn}>
        Clear Filters
      </button>
    </div>
  )
}
