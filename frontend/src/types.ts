// Mirrors backend Pydantic models

export type Currency = 'ILS' | 'USD' | 'EUR' | 'GBP' | 'ILP' | 'ILR'
export type AcquisitionType = 'purchase' | 'inheritance' | 'gift' | 'divorce'
export type RentalTaxTrack = 'marginal' | 'flat_10' | 'exempt' | 'exempt_chen'
export type DepreciationRate = '2_full' | '1.5_building' | '2_building' | '4_building' | '6.5_building' | '4_tiaumim'

export interface Seller {
  name: string
  id_number: string
  birth_date: string // ISO date, optional - may not be in contract
  share_percent: number
  is_israeli_resident: boolean
  marital_status: string
  annual_incomes: Record<number, number>
  prisa_max_years: number[]
}

export interface AcquisitionPart {
  acquisition_date: string
  acquisition_type: AcquisitionType
  amount: number | null // May not be available from sale contract
  currency: Currency
  share_percent: number
  deceased_eligible_for_exemption: boolean
}

export interface Deduction {
  description: string
  amount: number
  currency: Currency
  deduction_date: string
}

export interface RentalPeriod {
  start_date: string
  end_date: string
  tax_track: RentalTaxTrack
  depreciation_rate: DepreciationRate
}

export interface DepreciationInput {
  mode: 'manual' | 'auto'
  manual_amount: number
  rental_periods: RentalPeriod[]
  land_ratio: number
}

export interface ExemptionCheck {
  is_single_apartment: boolean
  ownership_months: number
  is_inheritance: boolean
  has_building_rights: boolean
  building_rights_value: number
  apartment_value_without_rights: number
}

export interface TransactionInput {
  sale_date: string
  sale_amount: number
  sale_currency: Currency
  sellers: Seller[]
  acquisitions: AcquisitionPart[]
  deductions: Deduction[]
  depreciation: DepreciationInput
  exemption: ExemptionCheck
  prisa_years: number
  is_residential: boolean
  betterment_levy: number
}

// Result types
export interface TaxPeriodBreakdown {
  days_total: number
  days_before_2001_11_07: number
  days_2001_to_2012: number
  days_after_2012: number
  days_to_2014_01_01: number
  days_after_2014: number
}

export interface PrisaYearResult {
  year: number
  spread_amount: number
  other_income: number
  total_taxable: number
  tax_calculated: number
  is_max_mode: boolean
}

export interface PrisaResult {
  years: number
  year_results: PrisaYearResult[]
  total_tax: number
  tax_without_prisa: number
  savings: number
}

export interface SellerResult {
  seller_name: string
  share_percent: number
  sale_amount_ils: number
  acquisition_amount_ils_indexed: number
  deductions_total_indexed: number
  total_cost_indexed: number
  shevach_mekarkein: number
  inflationary_amount: number
  real_shevach: number
  period_breakdown: TaxPeriodBreakdown
  shevach_to_2014: number
  shevach_after_2014: number
  tax_linear: number
  tax_regular: number
  tax_with_prisa: number | null
  mas_yesaf: number
  total_tax: number
  recommended_route: string
  prisa_result: PrisaResult | null
  depreciation_amount: number
  cpi_acquisition: number
  cpi_sale: number
  indexation_ratio: number
}

export interface ComparisonRoute {
  route_name: string
  tax_amount: number
  effective_rate: number
  savings_vs_regular: number
}

export interface CalculationResult {
  seller_results: SellerResult[]
  full_shevach_mekarkein: number
  full_inflationary: number
  full_real_shevach: number
  full_tax: number
  route_comparison: ComparisonRoute[]
  prisa_comparison: PrisaResult[]
}
