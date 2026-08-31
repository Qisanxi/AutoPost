import { useMemo, useState } from 'react'

export function useAuth() {
  const [user] = useState({
    name: 'DevRel Operator',
    role: 'admin',
    isAuthenticated: true,
  })

  return useMemo(() => ({ user }), [user])
}
