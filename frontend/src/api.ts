import axios from 'axios'
import type { CalculationResult, TransactionInput } from './types'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach auth token to all requests
client.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 responses globally (expired token)
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem('token')
      window.location.reload()
    }
    return Promise.reject(error)
  }
)

export async function calculateTax(input: TransactionInput): Promise<CalculationResult> {
  // Validate required fields before sending
  for (const acq of input.acquisitions) {
    if (!acq.acquisition_date) {
      throw new Error('חסר תאריך רכישה. יש למלא את תאריך הרכישה המקורי.')
    }
  }

  // Sanitize: convert empty date strings to null for optional fields
  const sanitized = {
    ...input,
    sellers: input.sellers.map(s => ({
      ...s,
      birth_date: s.birth_date || null,
    })),
  }
  const { data } = await client.post<CalculationResult>('/calculate-and-notify', sanitized)
  return data
}

export async function getCpi(year: number): Promise<{ year: number; cpi: number }> {
  const { data } = await client.get(`/cpi/${year}`)
  return data
}

export async function getIndexation(acquisitionYear: number, saleYear: number) {
  const { data } = await client.get('/indexation', {
    params: { acquisition_year: acquisitionYear, sale_year: saleYear },
  })
  return data
}
