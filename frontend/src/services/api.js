const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8080'
  : ''

class API {
  constructor() {
    this.token = null
  }

  setToken(token) {
    this.token = token
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`

    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers
      })

      // Handle 401 Unauthorized
      if (response.status === 401) {
        this.token = null
        localStorage.removeItem('token')
        window.location.href = '/'
        throw new Error('Unauthorized')
      }

      // Handle other errors
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || error.message || 'Request failed')
      }

      return await response.json()
    } catch (error) {
      console.error('API error:', error)
      throw error
    }
  }

  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' })
  }

  post(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data)
    })
  }

  put(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data)
    })
  }

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' })
  }
}

export const api = new API()
