import type { TransactionInput } from './types'

export const MOCK_TRANSACTION: TransactionInput = {
  sale_date: '2025-03-15',
  sale_amount: 3_500_000,
  sale_currency: 'ILS',
  sellers: [
    {
      name: 'ישראל ישראלי',
      id_number: '012345678',
      birth_date: '1970-05-12',
      share_percent: 50,
      is_israeli_resident: true,
      marital_status: 'married',
      annual_incomes: { 2025: 180_000, 2024: 170_000, 2023: 160_000, 2022: 150_000 },
      prisa_max_years: [],
    },
    {
      name: 'שרה ישראלי',
      id_number: '987654321',
      birth_date: '1972-08-20',
      share_percent: 50,
      is_israeli_resident: true,
      marital_status: 'married',
      annual_incomes: { 2025: 0, 2024: 0, 2023: 0, 2022: 0 },
      prisa_max_years: [2025, 2024, 2023, 2022],
    },
  ],
  acquisitions: [
    {
      acquisition_date: '2005-06-01',
      acquisition_type: 'purchase',
      amount: 1_200_000,
      currency: 'ILS',
      share_percent: 100,
      deceased_eligible_for_exemption: false,
    },
  ],
  deductions: [
    {
      description: 'שיפוץ מטבח ואמבטיה',
      amount: 85_000,
      currency: 'ILS',
      deduction_date: '2018-04-10',
    },
    {
      description: 'שכ"ט עו"ד רכישה',
      amount: 15_000,
      currency: 'ILS',
      deduction_date: '2005-06-01',
    },
  ],
  depreciation: {
    mode: 'manual',
    manual_amount: 0,
    rental_periods: [],
    land_ratio: 1 / 3,
  },
  exemption: {
    is_single_apartment: false,
    ownership_months: 237,
    is_inheritance: false,
    has_building_rights: false,
    building_rights_value: 0,
    apartment_value_without_rights: 0,
  },
  prisa_years: 0,
  is_residential: true,
  betterment_levy: 0,
}
