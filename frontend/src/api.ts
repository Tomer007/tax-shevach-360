import axios from 'axios'
import type { CalculationResult, TransactionInput } from './types'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export async function calculateTax(input: TransactionInput): Promise<CalculationResult> {
  const { data } = await client.post<CalculationResult>('/calculate', input)
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
