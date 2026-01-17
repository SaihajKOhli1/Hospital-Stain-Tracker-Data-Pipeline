import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card"
import { apiUrl } from "./lib/apiBase"

interface MetricsRow {
  region: string
  bed_occ_pct?: number
  icu_occ_pct?: number | null
  strain_index: number
  prev_strain_index?: number | null
  delta?: number | null
}

interface MetricsResponse {
  date: string | null
  rows: MetricsRow[]
}

function App() {
  const [date, setDate] = useState<string>('2024-01-16')
  const [data, setData] = useState<MetricsResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const fetchMetrics = async (selectedDate: string) => {
    setLoading(true)
    setError(null)
    
    try {
      const url = selectedDate 
        ? apiUrl(`/metrics/compare?date=${selectedDate}`)
        : apiUrl("/metrics/latest")
      
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const result: MetricsResponse = await response.json()
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics')
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMetrics(date)
  }, [])

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newDate = e.target.value
    setDate(newDate)
    if (newDate) {
      fetchMetrics(newDate)
    } else {
      fetchMetrics('')
    }
  }

  const formatPercent = (value: number | null): string => {
    if (value === null) return '-'
    return `${value.toFixed(1)}%`
  }

  const formatDelta = (delta: number | null | undefined): string => {
    if (delta === null || delta === undefined) return '-'
    const sign = delta > 0 ? '+' : ''
    return `${sign}${delta.toFixed(2)}`
  }

  const getStrainColor = (strain: number): string => {
    if (strain > 80) return 'text-red-600'
    if (strain >= 70) return 'text-orange-600'
    return 'text-green-600'
  }

  // Calculate KPIs
  const highestStrain = data?.rows.length 
    ? data.rows.reduce((max, row) => row.strain_index > max.strain_index ? row : max, data.rows[0])
    : null

  const averageStrain = data?.rows.length
    ? (data.rows.reduce((sum, row) => sum + row.strain_index, 0) / data.rows.length).toFixed(2)
    : null

  const statesInCrisis = data?.rows.length
    ? data.rows.filter(row => row.strain_index > 80).length
    : 0

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Hospital Strain Tracker</h1>
        <div className="flex items-center gap-4">
          <label htmlFor="date-input" className="text-sm font-medium text-gray-700">
            Date:
          </label>
          <input
            id="date-input"
            type="date"
            value={date}
            onChange={handleDateChange}
            className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      </div>

      {loading && <p className="text-gray-600">Loading...</p>}
      {error && <p className="text-red-600">Error: {error}</p>}
      
      {data && !loading && !error && (
        <>
          {data.date && (
            <p className="text-gray-600 mb-6">
              Showing data for: {data.date}
            </p>
          )}
          
          {data.rows.length === 0 ? (
            <p className="text-gray-600">No data available for the selected date.</p>
          ) : (
            <>
              {/* KPI Cards */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium text-gray-500">Highest Strain State</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {highestStrain && (
                        <span className={getStrainColor(highestStrain.strain_index)}>
                          {highestStrain.region}: {highestStrain.strain_index.toFixed(2)}
                        </span>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium text-gray-500">Average Strain</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-gray-900">
                      {averageStrain || '-'}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-medium text-gray-500">States in Crisis</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-red-600">
                      {statesInCrisis}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">Strain &gt; 80</p>
                  </CardContent>
                </Card>
              </div>

              {/* Data Table */}
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>Metrics Table</CardTitle>
                  <CardDescription>Detailed hospital capacity metrics by region</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900 border-b">Region</th>
                          {!date && (
                            <>
                              <th className="px-4 py-3 text-right text-sm font-semibold text-gray-900 border-b">Bed Occ %</th>
                              <th className="px-4 py-3 text-right text-sm font-semibold text-gray-900 border-b">ICU Occ %</th>
                            </>
                          )}
                          <th className="px-4 py-3 text-right text-sm font-semibold text-gray-900 border-b">Strain Index</th>
                          {date && (
                            <th className="px-4 py-3 text-right text-sm font-semibold text-gray-900 border-b">Δ Strain</th>
                          )}
                        </tr>
                      </thead>
                      <tbody>
                        {data.rows.map((row, index) => (
                          <tr key={index} className="border-b hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm text-gray-900">{row.region}</td>
                            {!date && (
                              <>
                                <td className="px-4 py-3 text-sm text-right text-gray-600">
                                  {row.bed_occ_pct !== undefined ? formatPercent(row.bed_occ_pct * 100) : '-'}
                                </td>
                                <td className="px-4 py-3 text-sm text-right text-gray-600">
                                  {row.icu_occ_pct !== null && row.icu_occ_pct !== undefined ? formatPercent(row.icu_occ_pct * 100) : '-'}
                                </td>
                              </>
                            )}
                            <td className={`px-4 py-3 text-sm text-right font-bold ${getStrainColor(row.strain_index)}`}>
                              {row.strain_index.toFixed(2)}
                            </td>
                            {date && (
                              <td className={`px-4 py-3 text-sm text-right ${
                                row.delta !== null && row.delta !== undefined
                                  ? (row.delta > 0 ? 'text-red-600' : row.delta < 0 ? 'text-green-600' : 'text-gray-600')
                                  : 'text-gray-600'
                              }`}>
                                {formatDelta(row.delta)}
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* Bar Chart */}
              <Card>
                <CardHeader>
                  <CardTitle>Strain Index by Region</CardTitle>
                  <CardDescription>Visual representation of hospital strain across states</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={data.rows}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="region" 
                        angle={-45}
                        textAnchor="end"
                        height={100}
                      />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="strain_index" fill="#8884d8" name="Strain Index" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </>
          )}
        </>
      )}
    </div>
  )
}

export default App
