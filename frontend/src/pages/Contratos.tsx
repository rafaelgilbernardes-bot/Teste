import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { brl } from '../lib/format'

export default function Contratos() {
  const [contratos, setContratos] = useState<any[]>([])
  const [clientes, setClientes] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState<any>({
    modelo: 'hora', data_inicio: '', cliente_id: '',
  })
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    Promise.all([
      api.get<any[]>('/api/contratos'),
      api.get<any[]>('/api/clientes'),
    ]).then(([c, cl]) => { setContratos(c); setClientes(cl) })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleSave = async () => {
    if (!form.cliente_id || !form.data_inicio) {
      setMsg('Preencha cliente e data de início.')
      return
    }
    setSaving(true)
    try {
      await api.post('/api/contratos', form)
      setMsg('Contrato criado com sucesso!')
      setForm({ modelo: 'hora', data_inicio: '', cliente_id: '' })
      load()
    } catch {
      setMsg('Erro ao salvar contrato.')
    } finally {
      setSaving(false)
    }
  }

  const modeloLabel: Record<string, string> = {
    hora: 'Hora', laas: 'LaaS', escopo_fechado: 'Escopo Fechado'
  }

  return (
    <div className="space-y-8">
      <h1 className="text-xl font-bold">Contratos</h1>

      {/* Formulário novo contrato */}
      <div className="bg-white rounded-xl shadow p-6 space-y-4">
        <h2 className="font-semibold text-gray-700">Novo Contrato</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="text-xs font-medium text-gray-500">Cliente</label>
            <select className="w-full border rounded px-2 py-1.5 text-sm mt-1"
              value={form.cliente_id} onChange={(e) => setForm({ ...form, cliente_id: e.target.value })}>
              <option value="">Selecione...</option>
              {clientes.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-500">Modelo</label>
            <select className="w-full border rounded px-2 py-1.5 text-sm mt-1"
              value={form.modelo} onChange={(e) => setForm({ ...form, modelo: e.target.value })}>
              <option value="hora">Hora</option>
              <option value="laas">LaaS</option>
              <option value="escopo_fechado">Escopo Fechado</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-500">Início</label>
            <input type="date" className="w-full border rounded px-2 py-1.5 text-sm mt-1"
              value={form.data_inicio} onChange={(e) => setForm({ ...form, data_inicio: e.target.value })} />
          </div>

          {form.modelo === 'hora' && (
            <div>
              <label className="text-xs font-medium text-gray-500">Valor/hora (R$)</label>
              <input type="number" className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                value={form.valor_hora ?? ''}
                onChange={(e) => setForm({ ...form, valor_hora: parseFloat(e.target.value) })} />
            </div>
          )}

          {form.modelo === 'laas' && (
            <>
              <div>
                <label className="text-xs font-medium text-gray-500">Valor Fixo Mensal (R$)</label>
                <input type="number" className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                  value={form.valor_fixo_mensal ?? ''}
                  onChange={(e) => setForm({ ...form, valor_fixo_mensal: parseFloat(e.target.value) })} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500">Limite de Horas/mês</label>
                <input type="number" className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                  value={form.horas_laas_limite ?? ''}
                  onChange={(e) => setForm({ ...form, horas_laas_limite: parseInt(e.target.value) })} />
              </div>
            </>
          )}

          {form.modelo === 'escopo_fechado' && (
            <>
              <div>
                <label className="text-xs font-medium text-gray-500">Valor do Escopo (R$)</label>
                <input type="number" className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                  value={form.valor_escopo ?? ''}
                  onChange={(e) => setForm({ ...form, valor_escopo: parseFloat(e.target.value) })} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500">Total de Horas do Escopo</label>
                <input type="number" className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                  value={form.horas_escopo ?? ''}
                  onChange={(e) => setForm({ ...form, horas_escopo: parseInt(e.target.value) })} />
              </div>
            </>
          )}
        </div>

        {msg && <p className="text-sm text-brand-600">{msg}</p>}

        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-brand-700 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-brand-600 disabled:opacity-50"
        >
          {saving ? 'Salvando...' : 'Salvar Contrato'}
        </button>
      </div>

      {/* Lista de contratos */}
      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-brand-700 text-white">
            <tr>
              {['Cliente', 'Modelo', 'Valor', 'Início', 'Status'].map((h) => (
                <th key={h} className="text-left px-4 py-2">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">Carregando...</td></tr>
            ) : contratos.map((c) => {
              const valor = c.valor_hora ?? c.valor_fixo_mensal ?? c.valor_escopo
              return (
                <tr key={c.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-2">{c.cliente_id}</td>
                  <td className="px-4 py-2">{modeloLabel[c.modelo]}</td>
                  <td className="px-4 py-2">{valor ? brl(valor) : '—'}</td>
                  <td className="px-4 py-2">{c.data_inicio}</td>
                  <td className="px-4 py-2 capitalize">{c.status}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
