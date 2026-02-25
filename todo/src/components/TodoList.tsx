import { Todo } from '../types/todo'
import { TodoItem } from './TodoItem'
import styles from './TodoList.module.css'

interface TodoListProps {
  todos: Todo[]
  onToggleComplete: (id: string) => void
  onDelete: (id: string) => void
  onUpdate: (id: string, updates: Partial<Omit<Todo, 'id' | 'createdAt'>>) => void
}

export const TodoList = ({ todos, onToggleComplete, onDelete, onUpdate }: TodoListProps) => {
  if (todos.length === 0) {
    return (
      <div className={styles.empty}>
        <p>No TODOs yet. Create one to get started!</p>
      </div>
    )
  }

  return (
    <div className={styles.list}>
      {todos.map((todo) => (
        <TodoItem
          key={todo.id}
          todo={todo}
          onToggleComplete={onToggleComplete}
          onDelete={onDelete}
          onUpdate={onUpdate}
        />
      ))}
    </div>
  )
}
