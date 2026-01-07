import { useState, useEffect } from 'react'
import { api } from '../services/api'
import StatusCard from '../components/StatusCard'

export default function NetworkPage() {
  const [config, setConfig] = useState(null)
  const [networkStatus, setNetworkStatus] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [message, setMessage] = useState({ type: '', text: '' })
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Uplink form with mode selection
  const [uplinkForm, setUplinkForm] = useState({
    mode: 'wpa',
    ssid: '',
    password: '',
    country: 'US',
    portal_url: '',
    portal_username: '',
    portal_password: '',
    auto_detect_portal: true
  })

  // Portal detection state
  const [portalDetection, setPortalDetection] = useState({
    detected: false,
    portal_url: null,
    isChecking: false,
    hasInternet: false
  })

  const [apForm, setApForm] = useState({ ssid: '', password: '', channel: 6, country: 'US', hw_mode: 'g' })
  const [dhcpForm, setDhcpForm] = useState({
    subnet: '10.42.0.0',
    netmask: '255.255.255.0',
    gateway: '10.42.0.1',
    range_start: '10.42.0.50',
    range_end: '10.42.0.200',
    lease_time: '12h'
  })

  const fetchData = async () => {
    try {
      const [configData, statusData] = await Promise.all([
        api.get('/api/config/network'),
        api.get('/api/status/network')
      ])
      setConfig(configData)
      setNetworkStatus(statusData)

      // Populate forms
      setUplinkForm(prev => ({
        ...prev,
        mode: configData.uplink.mode || 'wpa',
        ssid: configData.uplink.ssid || '',
        country: configData.uplink.country || 'US',
        portal_url: configData.uplink.portal_url || '',
        portal_username: configData.uplink.portal_username || '',
        auto_detect_portal: configData.uplink.auto_detect_portal !== false
      }))
      setApForm(prev => ({ ...prev, ssid: configData.ap.ssid, channel: configData.ap.channel, country: configData.ap.country, hw_mode: configData.ap.hw_mode }))
      setDhcpForm(configData.dhcp)
    } catch (err) {
      showMessage('error', err.message || 'Failed to load configuration')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const showMessage = (type, text) => {
    setMessage({ type, text })
    setTimeout(() => setMessage({ type: '', text: '' }), 5000)
  }

  const detectPortal = async () => {
    setPortalDetection(prev => ({ ...prev, isChecking: true }))
    try {
      const result = await api.get('/api/portal/detect')
      setPortalDetection({
        detected: result.is_captive_portal,
        portal_url: result.portal_url,
        hasInternet: result.has_internet,
        isChecking: false
      })

      if (result.is_captive_portal) {
        showMessage('warning', 'Captive portal detected! Please login to access internet.')
        if (result.portal_url) {
          setUplinkForm(prev => ({ ...prev, portal_url: result.portal_url, mode: 'portal' }))
        }
      } else if (result.has_internet) {
        showMessage('success', 'Internet connection confirmed!')
      } else {
        showMessage('warning', 'No internet connection detected.')
      }
    } catch (err) {
      showMessage('error', err.message || 'Failed to detect portal')
      setPortalDetection(prev => ({ ...prev, isChecking: false }))
    }
  }

  const handlePortalLogin = async () => {
    if (!uplinkForm.portal_url) {
      showMessage('error', 'Please enter portal URL')
      return
    }
    setIsSubmitting(true)
    try {
      const result = await api.post('/api/portal/login', {
        portal_url: uplinkForm.portal_url,
        username: uplinkForm.portal_username || undefined,
        password: uplinkForm.portal_password || undefined
      })

      if (result.success) {
        showMessage('success', 'Portal login successful!')
        // Check connectivity after login
        setTimeout(async () => {
          try {
            const checkResult = await api.post('/api/portal/check-connectivity')
            if (checkResult.has_internet) {
              showMessage('success', 'Internet access confirmed!')
            }
          } catch (err) {
            console.error('Connectivity check failed:', err)
          }
        }, 2000)
      } else {
        showMessage('warning', result.message || 'Login may have failed')
      }
    } catch (err) {
      showMessage('error', err.message || 'Failed to login to portal')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleUplinkSubmit = async (e) => {
    e.preventDefault()

    if (uplinkForm.mode === 'wpa' && !uplinkForm.password) {
      showMessage('error', 'Please enter the Wi-Fi password')
      return
    }

    if (uplinkForm.mode === 'portal' && !uplinkForm.portal_url) {
      showMessage('error', 'Please detect portal or enter portal URL')
      return
    }

    setIsSubmitting(true)
    try {
      const payload = {
        ...uplinkForm,
        password: uplinkForm.mode === 'wpa' ? uplinkForm.password : undefined
      }
      await api.post('/api/config/uplink', payload)
      showMessage('success', 'Uplink configuration updated. Reconnecting...')
      await new Promise(resolve => setTimeout(resolve, 3000))
      fetchData()
    } catch (err) {
      showMessage('error', err.message || 'Failed to update uplink')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleApSubmit = async (e) => {
    e.preventDefault()
    if (!apForm.password) {
      showMessage('error', 'Please enter the password')
      return
    }
    setIsSubmitting(true)
    try {
      await api.post('/api/config/ap', apForm)
      showMessage('success', 'AP configuration updated and restarting...')
      await new Promise(resolve => setTimeout(resolve, 3000))
      fetchData()
    } catch (err) {
      showMessage('error', err.message || 'Failed to update AP')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDhcpSubmit = async (e) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      await api.post('/api/config/dhcp', dhcpForm)
      showMessage('success', 'DHCP configuration updated and restarting...')
      await new Promise(resolve => setTimeout(resolve, 3000))
      fetchData()
    } catch (err) {
      showMessage('error', err.message || 'Failed to update DHCP')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
        <div className="spinner"></div>
      </div>
    )
  }

  return (
    <div>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '1.5rem' }}>Network Configuration</h1>

      {message.text && (
        <div className={`alert alert-${message.type}`}>
          {message.text}
        </div>
      )}

      {/* Uplink Configuration */}
      <div className="card">
        <h3 className="card-title mb-2">Uplink (wlan0) - Internet Connection</h3>
        <p className="text-muted mb-2">
          Configure the internet connection. Choose between WPA (normal Wi-Fi) or Captive Portal (hotel/airport/coffee shop).
        </p>

        {networkStatus?.wlan0?.connected && (
          <div className="alert alert-success">
            Currently connected to: <strong>{networkStatus.wlan0.ssid}</strong>
          </div>
        )}

        {/* Connection Mode Selection */}
        <div className="form-group mb-2">
          <label className="form-label">Connection Mode</label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setUplinkForm(prev => ({ ...prev, mode: 'wpa' }))}
              className={`btn ${uplinkForm.mode === 'wpa' ? 'btn-primary' : 'btn-secondary'}`}
            >
              WPA (Normal Wi-Fi)
            </button>
            <button
              type="button"
              onClick={() => setUplinkForm(prev => ({ ...prev, mode: 'portal' }))}
              className={`btn ${uplinkForm.mode === 'portal' ? 'btn-primary' : 'btn-secondary'}`}
            >
              Captive Portal
            </button>
            <button
              type="button"
              onClick={detectPortal}
              className="btn btn-secondary"
              disabled={portalDetection.isChecking}
            >
              {portalDetection.isChecking ? 'Detecting...' : 'Auto-Detect'}
            </button>
          </div>
          <div className="form-hint">
            {uplinkForm.mode === 'wpa'
              ? 'Use this for home/office Wi-Fi networks with WPA2 password'
              : 'Use this for public Wi-Fi with captive portal (hotels, airports, etc.)'}
          </div>
        </div>

        {portalDetection.detected && (
          <div className="alert alert-warning">
            <strong>Captive Portal Detected!</strong> Portal URL: {portalDetection.portal_url}
          </div>
        )}

        {portalDetection.hasInternet && (
          <div className="alert alert-success">
            <strong>Internet Access Confirmed!</strong>
          </div>
        )}

        <form onSubmit={handleUplinkSubmit}>
          {uplinkForm.mode === 'wpa' ? (
            <>
              <div className="grid grid-2">
                <div className="form-group">
                  <label className="form-label">SSID (Network Name)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={uplinkForm.ssid}
                    onChange={(e) => setUplinkForm({ ...uplinkForm, ssid: e.target.value })}
                    placeholder="Your Wi-Fi network name"
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Country Code</label>
                  <input
                    type="text"
                    className="form-input"
                    value={uplinkForm.country}
                    onChange={(e) => setUplinkForm({ ...uplinkForm, country: e.target.value.toUpperCase() })}
                    maxLength="2"
                    required
                  />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Password</label>
                <input
                  type="password"
                  className="form-input"
                  value={uplinkForm.password}
                  onChange={(e) => setUplinkForm({ ...uplinkForm, password: e.target.value })}
                  placeholder="Wi-Fi password"
                  minLength="8"
                  required
                />
                <div className="form-hint">Must be at least 8 characters</div>
              </div>
            </>
          ) : (
            <>
              <div className="form-group">
                <label className="form-label">Portal URL</label>
                <input
                  type="url"
                  className="form-input"
                  value={uplinkForm.portal_url}
                  onChange={(e) => setUplinkForm({ ...uplinkForm, portal_url: e.target.value })}
                  placeholder="https://portal.example.com or use Auto-Detect"
                  required
                />
                <div className="form-hint">Click "Auto-Detect" to find the portal automatically</div>
              </div>
              <div className="grid grid-2">
                <div className="form-group">
                  <label className="form-label">Portal Username (optional)</label>
                  <input
                    type="text"
                    className="form-input"
                    value={uplinkForm.portal_username}
                    onChange={(e) => setUplinkForm({ ...uplinkForm, portal_username: e.target.value })}
                    placeholder="Room number, email, etc."
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Portal Password (optional)</label>
                  <input
                    type="password"
                    className="form-input"
                    value={uplinkForm.portal_password}
                    onChange={(e) => setUplinkForm({ ...uplinkForm, portal_password: e.target.value })}
                    placeholder="Portal password if required"
                  />
                </div>
              </div>
              <button
                type="button"
                onClick={handlePortalLogin}
                className="btn btn-success"
                disabled={isSubmitting || !uplinkForm.portal_url}
              >
                Login to Portal
              </button>
            </>
          )}

          <button type="submit" className="btn btn-primary mt-2" disabled={isSubmitting}>
            {isSubmitting ? 'Applying...' : 'Apply Uplink Settings'}
          </button>
        </form>
      </div>

      {/* AP Configuration */}
      <div className="card mt-3">
        <h3 className="card-title mb-2">Access Point (wlan1) - Your Router's Wi-Fi</h3>
        <p className="text-muted mb-2">
          Configure the Wi-Fi network that your devices connect to.
        </p>

        {networkStatus?.wlan1?.running && (
          <div className="alert alert-success">
            AP running: <strong>{networkStatus.wlan1.ssid}</strong> on channel {networkStatus.wlan1.channel}
          </div>
        )}

        <form onSubmit={handleApSubmit}>
          <div className="grid grid-2">
            <div className="form-group">
              <label className="form-label">SSID (Network Name)</label>
              <input
                type="text"
                className="form-input"
                value={apForm.ssid}
                onChange={(e) => setApForm({ ...apForm, ssid: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Channel</label>
              <select
                className="form-select"
                value={apForm.channel}
                onChange={(e) => setApForm({ ...apForm, channel: parseInt(e.target.value) })}
                required
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13].map(ch => (
                  <option key={ch} value={ch}>{ch}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-2">
            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                type="password"
                className="form-input"
                value={apForm.password}
                onChange={(e) => setApForm({ ...apForm, password: e.target.value })}
                placeholder="Enter new password to change"
                minLength="8"
                required
              />
              <div className="form-hint">Must be at least 8 characters</div>
            </div>
            <div className="form-group">
              <label className="form-label">Hardware Mode</label>
              <select
                className="form-select"
                value={apForm.hw_mode}
                onChange={(e) => setApForm({ ...apForm, hw_mode: e.target.value })}
              >
                <option value="g">g (2.4 GHz)</option>
                <option value="n">n (2.4 GHz)</option>
                <option value="ac">ac (5 GHz)</option>
              </select>
            </div>
          </div>
          <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? 'Applying...' : 'Apply AP Settings'}
          </button>
        </form>
      </div>

      {/* DHCP Configuration */}
      <div className="card mt-3">
        <h3 className="card-title mb-2">DHCP Settings (Advanced)</h3>
        <p className="text-muted mb-2">
          Configure the IP address range for connected devices.
        </p>

        <form onSubmit={handleDhcpSubmit}>
          <div className="grid grid-3">
            <div className="form-group">
              <label className="form-label">Subnet</label>
              <input
                type="text"
                className="form-input"
                value={dhcpForm.subnet}
                onChange={(e) => setDhcpForm({ ...dhcpForm, subnet: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Netmask</label>
              <input
                type="text"
                className="form-input"
                value={dhcpForm.netmask}
                onChange={(e) => setDhcpForm({ ...dhcpForm, netmask: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Gateway (wlan1 IP)</label>
              <input
                type="text"
                className="form-input"
                value={dhcpForm.gateway}
                onChange={(e) => setDhcpForm({ ...dhcpForm, gateway: e.target.value })}
                required
              />
            </div>
          </div>
          <div className="grid grid-3">
            <div className="form-group">
              <label className="form-label">DHCP Range Start</label>
              <input
                type="text"
                className="form-input"
                value={dhcpForm.range_start}
                onChange={(e) => setDhcpForm({ ...dhcpForm, range_start: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">DHCP Range End</label>
              <input
                type="text"
                className="form-input"
                value={dhcpForm.range_end}
                onChange={(e) => setDhcpForm({ ...dhcpForm, range_end: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Lease Time</label>
              <input
                type="text"
                className="form-input"
                value={dhcpForm.lease_time}
                onChange={(e) => setDhcpForm({ ...dhcpForm, lease_time: e.target.value })}
                required
              />
            </div>
          </div>
          <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? 'Applying...' : 'Apply DHCP Settings'}
          </button>
        </form>
      </div>
    </div>
  )
}
