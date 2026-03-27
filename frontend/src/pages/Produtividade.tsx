import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts'
import { api } from '../lib/api'
import { formatHours } from '../lib/format'
import { useMes } from '../hooks/useMes'
import MesPicker from '../components/MesPicker'
import Card from '../components/Card'

export default function Produtividade() {
  const [mes, setMes] = useMes()
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.get<any[]>('/api/produtividade', { mes })
      .then(setData)
      .finally(() => setLoading(false))
  }, [mes])

  const totalH = data.reduce((s, d) => s + d.total_horas, 0)
  const fatH = data.reduce((s, d) => s + d.horas_faturaveis, 0)
  const pctGeral = totalH ? (fatH / totalH) * 100 : 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Produtividade por Colaborador</h1>
        <MesPicker value={mes} onChange={setMes} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card title="Total de Horas" value={formatHours(totalH)} color="blue" />
        <Card title="Horas Faturáveis" value={formatHours(fatH)} color="green" />
        <Card title="% Faturável" value={`${pctGeral.toFixed(1)}%`} color="yellow" />
      </div>

      {!loading && data.length > 0 && (
        <div className="bg-white rounded-xl shadow p-4">
          <h2 className="text-sm font-semibold text-gray-600 mb-3">Horas por Colaborador vs Meta</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="colaborador_nome" tick={{ fontSize: 11 }} />
              <YAxis />
              <Tooltip formatter={(v: number, name: string) => [
                formatHours(v as number),
                name === 'horas_faturaveis' ? 'Faturável' : 'Não Faturável'
              ]} />
              <Bar dataKey="horas_faturaveis" stackId="a" fill="#0ca678" name="Faturável" radius={[0, 0, 0, 0]} />
              <Bar dataKey="horas_nao_faturaveis" stackId="a" fill="#adb5bd" name="Não Faturável" radius={[4, 4, 0, 0]} />
              <ReferenceLine y={160} stroke="#e03131" strokeDasharray="4 4" label={{ value: 'Meta', fill: '#e03131', fontSize: 11 }} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-brand-700 text-white">
            <tr>
              {['Colaborador', 'Total', 'Faturável', 'Não Faturável', '% Faturável', 'Meta', '% Meta'].map((h) => (
                <th key={h} className="text-left px-4 py-2">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-400">Carregando...</td></tr>
            ) : data.map((d) => (
              <tr key={d.colaborador_id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{d.colaborador_nome}</td>
                <td className="px-4 py-2">{formatHours(d.total_horas)}</td>
                <td className="px-4 py-2 text-green-700">{formatHours(d.horas_faturaveis)}</td>
                <td className="px-4 py-2 text-gray-500">{formatHours(d.horas_nao_faturaveis)}</td>
                <td className="px-4 py-2">{d.pct_faturavel}%</td>
                <td className="px-4 py-2">{d.meta_horas}h</td>
                <td className={`px-4 py-2 font-semibold ${
                  d.pct_meta < 80 ? 'text-red-600' : d.pct_meta >= 100 ? 'text-green-600' : 'text-yellow-600'
                }`}>{d.pct_meta}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
