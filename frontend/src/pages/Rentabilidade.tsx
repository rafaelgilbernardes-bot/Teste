import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { brl } from '../lib/format'
import { useMes } from '../hooks/useMes'
import MesPicker from '../components/MesPicker'
import Card from '../components/Card'

export default function Rentabilidade() {
  const [mes, setMes] = useMes()
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.get<any[]>('/api/rentabilidade', { mes })
      .then(setData)
      .finally(() => setLoading(false))
  }, [mes])

  const totalReceita = data.reduce((s, d) => s + d.receita, 0)
  const totalCusto = data.reduce((s, d) => s + d.custo, 0)
  const totalMargem = totalReceita - totalCusto
  const pctMargem = totalReceita ? (totalMargem / totalReceita) * 100 : 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Rentabilidade por Contrato</h1>
        <MesPicker value={mes} onChange={setMes} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <Card title="Receita Total" value={brl(totalReceita)} color="green" />
        <Card title="Custo Total" value={brl(totalCusto)} color="red" />
        <Card title="Margem" value={brl(totalMargem)} color="blue" />
        <Card title="% Margem" value={`${pctMargem.toFixed(1)}%`}
          color={pctMargem >= 50 ? 'green' : pctMargem >= 30 ? 'yellow' : 'red'} />
      </div>

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-brand-700 text-white">
            <tr>
              {['Cliente', 'Modelo', 'Receita', 'Custo', 'Margem', '% Margem'].map((h) => (
                <th key={h} className="text-left px-4 py-2">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">Carregando...</td></tr>
            ) : data.map((d) => (
              <tr key={d.contrato_id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{d.cliente_nome}</td>
                <td className="px-4 py-2 capitalize">{d.modelo.replace('_', ' ')}</td>
                <td className="px-4 py-2">{brl(d.receita)}</td>
                <td className="px-4 py-2">{brl(d.custo)}</td>
                <td className="px-4 py-2">{brl(d.margem)}</td>
                <td className={`px-4 py-2 font-semibold ${
                  d.pct_margem >= 50 ? 'text-green-600' : d.pct_margem >= 30 ? 'text-yellow-600' : 'text-red-600'
                }`}>{d.pct_margem}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
