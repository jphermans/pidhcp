import { useState, useEffect } from 'react'
import { api } from '../services/api'

export default function SettingsPage() {
  const [services, setServices] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [message, setMessage] = useState({ type: '', text: '' })
  const [showPasswordForm, setShowPasswordForm] = useState(false)
  const [passwordForm, setPasswordForm] = useState({ current: '', new: '' })
  const [showFactoryReset, setShowFactoryReset] = useState(false)
  const [showPowerControls, setShowPowerControls] = useState(false)

  const fetchData = async () => {
    try {
      const statusData = await api.get('/api/status/system')
      setServices(statusData.services)
    } catch (err) {
      showMessage('error', err.message || 'Failed to load services status')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [])

  const showMessage = (type, text) => {
    setMessage({ type, text })
    setTimeout(() => setMessage({ type: '', text: '' }), 5000)
  }

  const handleServiceAction = async (service, action) => {
    try {
      await api.post('/api/services/control', { service, action })
      showMessage('success', `Service ${service} ${action}ed`)
      await new Promise(resolve => setTimeout(resolve, 2000))
      fetchData()
    } catch (err) {
      showMessage('error', err.message || `Failed to ${action} ${service}`)
    }
  }

  const handleSetupNat = async () => {
    try {
      await api.post('/api/services/setup-nat')
      showMessage('success', 'NAT and IP forwarding configured')
    } catch (err) {
      showMessage('error', err.message || 'Failed to setup NAT')
    }
  }

  const handlePasswordChange = async (e) => {
    e.preventDefault()
    try {
      await api.post('/api/auth/change-password', {
        current_password: passwordForm.current,
        new_password: passwordForm.new
      })
      showMessage('success', 'Password changed successfully')
      setShowPasswordForm(false)
      setPasswordForm({ current: '', new: '' })
    } catch (err) {
      showMessage('error', err.message || 'Failed to change password')
    }
  }

  const handleFactoryReset = async () => {
    if (!confirm('Are you sure? This will reset all configuration to factory defaults.')) {
      return
    }
    try {
      await api.post('/api/config/reset')
      showMessage('success', 'Configuration reset. Please refresh the page.')
      setTimeout(() => window.location.reload(), 3000)
    } catch (err) {
      showMessage('error', err.message || 'Failed to reset configuration')
    }
  }

  const handleReboot = async () => {
    if (!confirm('Are you sure you want to reboot the system?\n\nThe web UI will be unavailable during reboot.')) {
      return
    }
    try {
      await api.post('/api/services/reboot')
      showMessage('warning', 'System is rebooting... Connection will be lost.')
      setShowPowerControls(false)
    } catch (err) {
      showMessage('error', err.message || 'Failed to reboot system')
    }
  }

  const handleShutdown = async () => {
    if (!confirm('⚠️ WARNING: Are you sure you want to shutdown the system?\n\nYou will need to physically power on the Pi again.\n\nThis is a travel Pi - make sure you\'ve saved your work!')) {
      return
    }
    try {
      await api.post('/api/services/shutdown')
      showMessage('warning', 'System is shutting down... Goodbye!')
      setShowPowerControls(false)
    } catch (err) {
      showMessage('error', err.message || 'Failed to shutdown system')
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
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '1.5rem' }}>Settings</h1>

      {message.text && (
        <div className={`alert alert-${message.type}`}>
          {message.text}
        </div>
      )}

      {/* Service Control */}
      <div className="card">
        <h3 className="card-title mb-2">Service Control</h3>
        <p className="text-muted mb-2">
          Start, stop, or restart router services.
        </p>

        <div className="grid grid-3">
          {services && Object.entries(services).map(([name, service]) => (
            <div key={name} style={{ padding: '1rem', border: '1px solid var(--border)', borderRadius: '0.5rem' }}>
              <div className="flex justify-between items-center mb-2">
                <strong style={{ textTransform: 'capitalize' }}>{name.replace('wpa_supplicant', 'WPA')}</strong>
                <span className={`badge ${service.active ? 'badge-success' : 'badge-error'}`}>
                  {service.active ? 'Running' : 'Stopped'}
                </span>
              </div>
              <div className="flex gap-2">
                <button onClick={() => handleServiceAction(name, 'restart')} className="btn btn-secondary btn-sm w-full">
                  Restart
                </button>
                <button onClick={() => handleServiceAction(name, service.active ? 'stop' : 'start')}
                  className={`btn ${service.active ? 'btn-warning' : 'btn-success'} btn-sm w-full`}>
                  {service.active ? 'Stop' : 'Start'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* NAT Setup */}
      <div className="card mt-3">
        <h3 className="card-title mb-2">Network Setup</h3>
        <p className="text-muted mb-2">
          Configure NAT and IP forwarding for internet access.
        </p>
        <button onClick={handleSetupNat} className="btn btn-primary">
          Enable NAT & IP Forwarding
        </button>
      </div>

      {/* Password Change */}
      <div className="card mt-3">
        <h3 className="card-title mb-2">Change Password</h3>
        <p className="text-muted mb-2">
          Change your admin password.
        </p>

        {!showPasswordForm ? (
          <button onClick={() => setShowPasswordForm(true)} className="btn btn-secondary">
            Change Password
          </button>
        ) : (
          <form onSubmit={handlePasswordChange}>
            <div className="form-group">
              <label className="form-label">Current Password</label>
              <input
                type="password"
                className="form-input"
                value={passwordForm.current}
                onChange={(e) => setPasswordForm({ ...passwordForm, current: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">New Password</label>
              <input
                type="password"
                className="form-input"
                value={passwordForm.new}
                onChange={(e) => setPasswordForm({ ...passwordForm, new: e.target.value })}
                minLength="8"
                required
              />
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn btn-primary">
                Update Password
              </button>
              <button type="button" onClick={() => { setShowPasswordForm(false); setPasswordForm({ current: '', new: '' }) }}
                className="btn btn-secondary">
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>

      {/* System Power Control - For Travel Pi */}
      <div className="card mt-3" style={{
        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(59, 130, 246, 0.05) 100%)',
        border: '2px solid var(--accent)'
      }}>
        <div className="card-header">
          <div>
            <h3 className="card-title" style={{ marginBottom: '0.25rem' }}>
              🔌 System Power Control
            </h3>
            <p className="text-muted" style={{ margin: 0, fontSize: '0.875rem' }}>
              Safe shutdown or reboot your travel Pi
            </p>
          </div>
        </div>

        {!showPowerControls ? (
          <div className="flex gap-2">
            <button onClick={() => setShowPowerControls(true)} className="btn btn-warning">
              Show Power Options
            </button>
          </div>
        ) : (
          <div>
            <div className="alert alert-warning mb-2">
              <strong>⚠️ Warning:</strong> Rebooting or shutting down will disconnect all clients and make the web UI unavailable.
            </div>
            <div className="grid grid-2 gap-2">
              <button onClick={handleReboot} className="btn btn-warning">
                🔄 Reboot System
              </button>
              <button onClick={handleShutdown} className="btn btn-error">
                ⏻ Shutdown System
              </button>
            </div>
            <button onClick={() => setShowPowerControls(false)} className="btn btn-secondary w-full mt-2">
              Cancel
            </button>
          </div>
        )}
      </div>

      {/* Factory Reset */}
      <div className="card mt-3" style={{ borderColor: 'var(--error)' }}>
        <h3 className="card-title mb-2" style={{ color: 'var(--error)' }}>Danger Zone</h3>
        <p className="text-muted mb-2">
          Reset all configuration to factory defaults. You will need to reconfigure everything.
        </p>

        {!showFactoryReset ? (
          <button onClick={() => setShowFactoryReset(true)} className="btn btn-error">
            Factory Reset
          </button>
        ) : (
          <div className="flex gap-2">
            <button onClick={handleFactoryReset} className="btn btn-error">
              Confirm Factory Reset
            </button>
            <button onClick={() => setShowFactoryReset(false)} className="btn btn-secondary">
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
