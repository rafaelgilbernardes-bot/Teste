import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts'
import { api } from '../lib/api'
import { brl, formatHours } from '../lib/format'
import { useMes } from '../hooks/useMes'
import MesPicker from '../components/MesPicker'
import Card from '../components/Card'

const MODELO_COLORS: Record<string, string> = {
  hora:           '#3b5bdb',
  laas:           '#0ca678',
  escopo_fechado: '#f59f00',
}

export default function Faturamento() {
  const [mes, setMes] = useMes()
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.get<any[]>('/api/faturamento', { mes })
      .then(setData)
      .finally(() => setLoading(false))
  }, [mes])

  const total = data.reduce((s, d) => s + d.valor_faturamento, 0)
  const totalHoras = data.reduce((s, d) => s + d.total_horas, 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Faturamento por Cliente</h1>
        <MesPicker value={mes} onChange={setMes} />
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card title="Total do Mês" value={brl(total)} color="blue" />
        <Card title="Total de Horas" value={formatHours(totalHoras)} color="green" />
        <Card title="Clientes Ativos" value={String(data.length)} color="yellow" />
      </div>

      {/* Gráfico */}
      {!loading && data.length > 0 && (
        <div className="bg-white rounded-xl shadow p-4">
          <h2 className="text-sm font-semibold text-gray-600 mb-3">Faturamento por Cliente</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data} margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="cliente_nome" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={(v) => `R$${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v: number) => brl(v)} />
              <Bar dataKey="valor_faturamento" radius={[4, 4, 0, 0]}>
                {data.map((d, i) => (
                  <Cell key={i} fill={MODELO_COLORS[d.modelo] ?? '#6c757d'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Tabela */}
      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-brand-700 text-white">
            <tr>
              {['Cliente', 'Modelo', 'Horas', 'Faturamento'].map((h) => (
                <th key={h} className="text-left px-4 py-2">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400">Carregando...</td></tr>
            ) : data.length === 0 ? (
              <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400">Sem dados para este mês.</td></tr>
            ) : (
              data.map((d) => (
                <tr key={d.cliente_id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium">{d.cliente_nome}</td>
                  <td className="px-4 py-2 capitalize">{d.modelo.replace('_', ' ')}</td>
                  <td className="px-4 py-2">{formatHours(d.total_horas)}</td>
                  <td className="px-4 py-2 font-semibold">{brl(d.valor_faturamento)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
