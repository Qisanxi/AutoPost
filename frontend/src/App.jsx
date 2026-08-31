import { useState, useCallback, useEffect, useRef } from 'react'
import { Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import Dashboard from './pages/Dashboard'

/* ─── Global toast provider ─── */
function ToastItem({ msg, err }) {
  const ref = useRef(null)
  useEffect(() => { requestAnimationFrame(() => { if (ref.current) ref.current.classList.add('show') }) }, [])
  return <div ref={ref} className={`toast${err ? ' err' : ''}`}>{msg}</div>
}

export default function App() {
  const [toasts, setToasts] = useState([])
  const toast = useCallback((msg, ok = true) => {
    const id = Date.now() + Math.random()
    setToasts(p => [...p, { id, msg, err: ok === false }])
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 4200)
  }, [])

  return (
    <>
      <Routes>
        <Route path="/" element={<LandingPage toast={toast} />} />
        <Route path="/dashboard" element={<Dashboard toast={toast} />} />
      </Routes>
      <div id="toasts">
        {toasts.map(t => <ToastItem key={t.id} msg={t.msg} err={t.err} />)}
      </div>
    </>
  )
}