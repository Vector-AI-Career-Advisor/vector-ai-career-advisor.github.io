import api from './client'

export const signup = (email: string, password: string) =>
  api.post('/auth/signup', { email, password })

export const login = async (email: string, password: string): Promise<string> => {
  const { data } = await api.post('/auth/login', { email, password })
  return data.access_token
}
