type Severidade = 'info' | 'warning' | 'critical'

const styles: Record<Severidade, string> = {
  info:     'bg-blue-100 text-blue-800 border-blue-200',
  warning:  'bg-yellow-100 text-yellow-800 border-yellow-200',
  critical: 'bg-red-100 text-red-800 border-red-200',
}

const icons: Record<Severidade, string> = {
  info: 'ℹ️',
  warning: '⚠️',
  critical: '🚨',
}

export default function AlertBadge({ severidade, descricao }: { severidade: Severidade; descricao: string }) {
  return (
    <div className={`flex gap-2 border rounded-lg px-4 py-3 text-sm ${styles[severidade]}`}>
      <span>{icons[severidade]}</span>
      <span>{descricao}</span>
    </div>
  )
}
