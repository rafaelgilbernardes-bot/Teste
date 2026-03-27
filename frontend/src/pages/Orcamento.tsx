import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { brl, formatHours } from '../lib/format'
import { useMes } from '../hooks/useMes'
import MesPicker from '../components/MesPicker'

export default function Orcamento() {
  const [mes, setMes] = useMes()
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.get<any[]>('/api/orcado-vs-realizado', { mes })
      .then(setData)
      .finally(() => setLoading(false))
  }, [mes])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Orçado vs Realizado</h1>
        <MesPicker value={mes} onChange={setMes} />
      </div>

      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-brand-700 text-white">
            <tr>
              {['Cliente', 'Horas Previstas', 'Horas Realizadas', 'Receita Prevista', 'Receita Realizada', 'Variação'].map((h) => (
                <th key={h} className="text-left px-4 py-2">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">Carregando...</td></tr>
            ) : data.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">Sem dados para este mês.</td></tr>
            ) : data.map((d) => {
              const varHoras = d.horas_realizadas - (d.horas_previstas ?? 0)
              const varReceita = d.receita_realizada - (d.receita_prevista ?? 0)
              return (
                <tr key={d.cliente_id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium">{d.cliente_nome}</td>
                  <td className="px-4 py-2">{d.horas_previstas != null ? `${d.horas_previstas}h` : '—'}</td>
                  <td className="px-4 py-2">{formatHours(d.horas_realizadas)}</td>
                  <td className="px-4 py-2">{d.receita_prevista != null ? brl(d.receita_prevista) : '—'}</td>
                  <td className="px-4 py-2">{brl(d.receita_realizada)}</td>
                  <td className={`px-4 py-2 font-semibold ${
                    varReceita >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {varReceita >= 0 ? '+' : ''}{brl(varReceita)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
