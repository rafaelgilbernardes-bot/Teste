import { useState } from 'react'

/** Retorna o mês atual no formato 'YYYY-MM' e um setter. */
export function useMes() {
  const now = new Date()
  const defaultMes = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  return useState<string>(defaultMes)
}
