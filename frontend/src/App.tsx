import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Faturamento from './pages/Faturamento'
import Produtividade from './pages/Produtividade'
import Rentabilidade from './pages/Rentabilidade'
import Orcamento from './pages/Orcamento'
import Alertas from './pages/Alertas'
import Contratos from './pages/Contratos'
import Relatorios from './pages/Relatorios'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/faturamento" replace />} />
        <Route path="faturamento" element={<Faturamento />} />
        <Route path="produtividade" element={<Produtividade />} />
        <Route path="rentabilidade" element={<Rentabilidade />} />
        <Route path="orcamento" element={<Orcamento />} />
        <Route path="alertas" element={<Alertas />} />
        <Route path="contratos" element={<Contratos />} />
        <Route path="relatorios" element={<Relatorios />} />
      </Route>
    </Routes>
  )
}
