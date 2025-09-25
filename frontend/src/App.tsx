import { useState, useEffect } from 'react'
import axios from 'axios'

interface HealthResponse {
  status: string
  timestamp: string
  service: string
  version: string
}

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    checkHealth()
  }, [])

  const checkHealth = async () => {
    try {
      const response = await axios.get<HealthResponse>('/api/health')
      setHealth(response.data)
      setError(null)
    } catch (err) {
      setError('Failed to connect to backend')
      setHealth(null)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-gray-800 mb-8">
          Hero of Kindness CPRA Filter
        </h1>

        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-4">System Status</h2>
          {health ? (
            <div className="space-y-2">
              <div className="flex items-center">
                <span className="w-3 h-3 bg-green-500 rounded-full mr-2"></span>
                <span className="text-green-600 font-medium">Backend Connected</span>
              </div>
              <div className="text-gray-600">
                <p>Service: {health.service}</p>
                <p>Version: {health.version}</p>
                <p>Status: {health.status}</p>
                <p>Last Check: {new Date(health.timestamp).toLocaleTimeString()}</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex items-center">
              <span className="w-3 h-3 bg-red-500 rounded-full mr-2"></span>
              <span className="text-red-600">{error}</span>
            </div>
          ) : (
            <div>Checking connection...</div>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-semibold mb-4">Quick Start</h2>
          <ol className="list-decimal list-inside space-y-2 text-gray-600">
            <li>Ensure Ollama is running with at least one model installed</li>
            <li>Navigate to the Process page to upload email files</li>
            <li>Select an LLM model and start classification</li>
            <li>Review classified documents in the Review page</li>
            <li>Export results when complete</li>
          </ol>
        </div>
      </div>
    </div>
  )
}

export default App