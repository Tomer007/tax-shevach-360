"""Consumer Price Index (CPI) historical data.

Per Section 47 of the Land Taxation Law (Appreciation and Acquisition):
"Index" = Consumer Price Index published by the Central Bureau of Statistics.

Dates before January 1952 (first published CPI) use the first published value.
Values are base 100 = average 1993.
"""

# Annual average CPI values (base: average 1993 = 100)
# Source: Israel Central Bureau of Statistics
CPI_ANNUAL: dict[int, float] = {
    1950: 0.61,
    1951: 0.80,
    1952: 1.00,
    1953: 1.28,
    1954: 1.44,
    1955: 1.49,
    1956: 1.58,
    1957: 1.66,
    1958: 1.70,
    1959: 1.72,
    1960: 1.76,
    1961: 1.84,
    1962: 1.97,
    1963: 2.10,
    1964: 2.19,
    1965: 2.35,
    1966: 2.54,
    1967: 2.58,
    1968: 2.63,
    1969: 2.70,
    1970: 2.87,
    1971: 3.22,
    1972: 3.61,
    1973: 4.33,
    1974: 6.00,
    1975: 8.34,
    1976: 11.01,
    1977: 14.87,
    1978: 22.07,
    1979: 34.96,
    1980: 54.69,
    1981: 121.66,
    1982: 210.89,
    1983: 494.59,
    1984: 2685.00,
    1985: 11775.00,
    1986: 17508.00,
    1987: 20898.00,
    1988: 24295.00,
    1989: 29282.00,
    1990: 34260.00,
    1991: 40482.00,
    1992: 45292.00,
    1993: 50145.00,
    1994: 55807.00,
    1995: 61266.00,
    1996: 68019.00,
    1997: 74085.00,
    1998: 77982.00,
    1999: 82132.00,
    2000: 83274.00,
    2001: 84433.00,
    2002: 89143.00,
    2003: 88373.00,
    2004: 88063.00,
    2005: 89265.00,
    2006: 91244.00,
    2007: 91719.00,
    2008: 95898.00,
    2009: 99226.00,
    2010: 101854.00,
    2011: 105356.00,
    2012: 107222.00,
    2013: 109046.00,
    2014: 108761.00,
    2015: 107808.00,
    2016: 107317.00,
    2017: 107649.00,
    2018: 108552.00,
    2019: 109430.00,
    2020: 108729.00,
    2021: 110398.00,
    2022: 115190.00,
    2023: 119090.00,
    2024: 120500.00,
    2025: 122300.00,
    2026: 124100.00,
}

# First published CPI (January 1952)
FIRST_CPI_VALUE: float = 1.00
FIRST_CPI_YEAR: int = 1952


def get_cpi_for_year(year: int) -> float:
    """Get CPI value for a given year.

    If before first publication (1952), returns the first published value.
    If after last known year, returns last known value.
    For years between known values, uses linear interpolation.
    """
    if year <= FIRST_CPI_YEAR:
        return FIRST_CPI_VALUE

    max_year = max(CPI_ANNUAL.keys())
    if year >= max_year:
        return CPI_ANNUAL[max_year]

    if year in CPI_ANNUAL:
        return CPI_ANNUAL[year]

    # Linear interpolation between known years
    lower_year = max(y for y in CPI_ANNUAL if y < year)
    upper_year = min(y for y in CPI_ANNUAL if y > year)
    lower_val = CPI_ANNUAL[lower_year]
    upper_val = CPI_ANNUAL[upper_year]
    ratio = (year - lower_year) / (upper_year - lower_year)
    return lower_val + (upper_val - lower_val) * ratio


def get_indexation_ratio(acquisition_year: int, sale_year: int) -> float:
    """Calculate the CPI indexation ratio between two years.

    Returns sale_cpi / acquisition_cpi.
    """
    cpi_acq = get_cpi_for_year(acquisition_year)
    cpi_sale = get_cpi_for_year(sale_year)

    if cpi_acq == 0:
        return 1.0

    return cpi_sale / cpi_acq
