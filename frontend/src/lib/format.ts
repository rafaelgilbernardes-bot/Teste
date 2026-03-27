/** Formata valor em reais (BRL). */
export function brl(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

/** Formata horas decimais como '4h30m'. */
export function formatHours(h: number): string {
  const intH = Math.floor(h)
  const min = Math.round((h - intH) * 60)
  return `${intH}h${min.toString().padStart(2, '0')}m`
}

/** 'YYYY-MM' → 'Mar/2026' */
export function formatMes(mes: string): string {
  const [y, m] = mes.split('-')
  const d = new Date(Number(y), Number(m) - 1)
  return d.toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' })
    .replace('. de ', '/').replace('.', '')
}
