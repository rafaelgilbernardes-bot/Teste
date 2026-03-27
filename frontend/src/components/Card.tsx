interface Props {
  title: string
  value: string
  sub?: string
  color?: 'blue' | 'green' | 'yellow' | 'red'
}

const colors = {
  blue:   'border-brand-500 bg-brand-50',
  green:  'border-green-500 bg-green-50',
  yellow: 'border-yellow-500 bg-yellow-50',
  red:    'border-red-500 bg-red-50',
}

export default function Card({ title, value, sub, color = 'blue' }: Props) {
  return (
    <div className={`border-l-4 rounded-lg p-4 shadow-sm ${colors[color]}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{title}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {sub && <p className="text-sm text-gray-500 mt-0.5">{sub}</p>}
    </div>
  )
}
