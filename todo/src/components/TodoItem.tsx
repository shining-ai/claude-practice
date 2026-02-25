import { useState } from 'react'
import { Todo } from '../types/todo'
import styles from './TodoItem.module.css'

interface TodoItemProps {
  todo: Todo
  onToggleComplete: (id: string) => void
  onDelete: (id: string) => void
  onUpdate: (id: string, updates: Partial<Omit<Todo, 'id' | 'createdAt'>>) => void
}

export const TodoItem = ({ todo, onToggleComplete, onDelete, onUpdate }: TodoItemProps) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editedTitle, setEditedTitle] = useState(todo.title)
  const [editedDescription, setEditedDescription] = useState(todo.description)

  const handleSaveEdit = () => {
    if (editedTitle.trim()) {
      onUpdate(todo.id, {
        title: editedTitle,
        description: editedDescription,
      })
      setIsEditing(false)
    }
  }

  const handleCancelEdit = () => {
    setEditedTitle(todo.title)
    setEditedDescription(todo.description)
    setIsEditing(false)
  }

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this TODO?')) {
      onDelete(todo.id)
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return null
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  const isOverdue = todo.dueDate && new Date(todo.dueDate) < new Date() && !todo.completed

  return (
    <div className={`${styles.item} ${todo.completed ? styles.completed : ''} ${isOverdue ? styles.overdue : ''}`}>
      <div className={styles.content}>
        <input
          type="checkbox"
          checked={todo.completed}
          onChange={() => onToggleComplete(todo.id)}
          className={styles.checkbox}
        />

        {isEditing ? (
          <div className={styles.editForm}>
            <input
              type="text"
              value={editedTitle}
              onChange={(e) => setEditedTitle(e.target.value)}
              className={styles.editInput}
              placeholder="Title"
            />
            <textarea
              value={editedDescription}
              onChange={(e) => setEditedDescription(e.target.value)}
              className={styles.editTextarea}
              placeholder="Description"
              rows={2}
            />
            <div className={styles.editActions}>
              <button onClick={handleSaveEdit} className={styles.saveBtn}>
                Save
              </button>
              <button onClick={handleCancelEdit} className={styles.cancelBtn}>
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className={styles.todoContent}>
            <div className={styles.titleRow}>
              <h3 className={styles.title}>{todo.title}</h3>
              <span className={`${styles.priority} ${styles[`priority-${todo.priority}`]}`}>
                {todo.priority}
              </span>
            </div>
            {todo.description && (
              <p className={styles.description}>{todo.description}</p>
            )}
            <div className={styles.meta}>
              <span className={styles.category}>{todo.category}</span>
              {todo.dueDate && (
                <span className={`${styles.dueDate} ${isOverdue ? styles.overdueText : ''}`}>
                  {formatDate(todo.dueDate)}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {!isEditing && (
        <div className={styles.actions}>
          <button
            onClick={() => setIsEditing(true)}
            className={styles.editBtn}
            title="Edit"
          >
            ✏️
          </button>
          <button
            onClick={handleDelete}
            className={styles.deleteBtn}
            title="Delete"
          >
            🗑️
          </button>
        </div>
      )}
    </div>
  )
}
