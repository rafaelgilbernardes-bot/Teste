import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useMes } from '../hooks/useMes'
import MesPicker from '../components/MesPicker'

export default function Relatorios() {
  const [mes, setMes] = useMes()
  const [contratos, setContratos] = useState<any[]>([])
  const [clientes, setClientes] = useState<any[]>([])
  const [contratoId, setContratoId] = useState('')
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    Promise.all([
      api.get<any[]>('/api/contratos'),
      api.get<any[]>('/api/clientes'),
    ]).then(([c, cl]) => { setContratos(c); setClientes(cl) })
  }, [])

  const clienteNome = (cliente_id: string) =>
    clientes.find((c) => c.id === cliente_id)?.nome ?? cliente_id

  const handleDownload = async () => {
    if (!contratoId) return
    setDownloading(true)
    try {
      const params = new URLSearchParams({ contrato_id: contratoId, mes })
      const res = await fetch(`/api/relatorios/excel?${params}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = res.headers.get('Content-Disposition')
        ?.split('filename=')?.[1]?.replace(/"/g, '') ?? `relatorio_${mes}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Gerar Relatório para Cliente</h1>

      <div className="bg-white rounded-xl shadow p-6 space-y-4 max-w-lg">
        <div>
          <label className="text-xs font-medium text-gray-500">Mês de Referência</label>
          <div className="mt-1"><MesPicker value={mes} onChange={setMes} /></div>
        </div>

        <div>
          <label className="text-xs font-medium text-gray-500">Contrato</label>
          <select
            className="w-full border rounded px-2 py-1.5 text-sm mt-1"
            value={contratoId}
            onChange={(e) => setContratoId(e.target.value)}
          >
            <option value="">Selecione o contrato...</option>
            {contratos.map((c) => (
              <option key={c.id} value={c.id}>
                {clienteNome(c.cliente_id)} — {c.modelo.replace('_', ' ')}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleDownload}
          disabled={!contratoId || downloading}
          className="w-full bg-brand-700 text-white py-2 rounded-lg text-sm font-medium hover:bg-brand-600 disabled:opacity-50"
        >
          {downloading ? 'Gerando...' : '⬇️ Baixar Relatório Excel'}
        </button>

        <p className="text-xs text-gray-400">
          O relatório segue o formato atual do escritório (Data, Responsável,
          Projeto, Descrição, Duração, Valor) com rodapé de totais.
        </p>
      </div>
    </div>
  )
}
