import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useMes } from '../hooks/useMes'
import MesPicker from '../components/MesPicker'
import AlertBadge from '../components/AlertBadge'

export default function Alertas() {
  const [mes, setMes] = useMes()
  const [alertas, setAlertas] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.get<any[]>('/api/alertas', { mes })
      .then(setAlertas)
      .finally(() => setLoading(false))
  }, [mes])

  const criticals = alertas.filter((a) => a.severidade === 'critical')
  const warnings  = alertas.filter((a) => a.severidade === 'warning')
  const infos     = alertas.filter((a) => a.severidade === 'info')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Alertas Inteligentes</h1>
        <MesPicker value={mes} onChange={setMes} />
      </div>

      {loading && <p className="text-gray-400">Carregando alertas...</p>}

      {!loading && alertas.length === 0 && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center text-green-700">
          ✅ Nenhum alerta para este mês. Tudo dentro do esperado.
        </div>
      )}

      {criticals.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-red-700 mb-2">Crítico ({criticals.length})</h2>
          <div className="space-y-2">
            {criticals.map((a, i) => <AlertBadge key={i} severidade="critical" descricao={a.descricao} />)}
          </div>
        </section>
      )}

      {warnings.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-yellow-700 mb-2">Atenção ({warnings.length})</h2>
          <div className="space-y-2">
            {warnings.map((a, i) => <AlertBadge key={i} severidade="warning" descricao={a.descricao} />)}
          </div>
        </section>
      )}

      {infos.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-blue-700 mb-2">Informação ({infos.length})</h2>
          <div className="space-y-2">
            {infos.map((a, i) => <AlertBadge key={i} severidade="info" descricao={a.descricao} />)}
          </div>
        </section>
      )}
    </div>
  )
}
