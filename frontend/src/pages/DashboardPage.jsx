import { useState, useEffect } from 'react'
import { api } from '../services/api'
import StatusCard from '../components/StatusCard'

// Helper function to format bytes
function formatBytes(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

// Helper function to format uptime
function formatUptime(seconds) {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  if (days > 0) {
    return `${days}d ${hours}h ${minutes}m`
  } else if (hours > 0) {
    return `${hours}h ${minutes}m`
  } else {
    return `${minutes}m`
  }
}

// Helper function to get color based on percentage
function getColorForPercent(percent) {
  if (percent < 50) return 'var(--success)'
  if (percent < 75) return 'var(--warning)'
  return 'var(--error)'
}

export default function DashboardPage() {
  const [networkStatus, setNetworkStatus] = useState(null)
  const [systemStatus, setSystemStatus] = useState(null)
  const [devices, setDevices] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  const fetchData = async () => {
    try {
      const [network, system, devicesData] = await Promise.all([
        api.get('/api/status/network'),
        api.get('/api/status/system'),
        api.get('/api/status/devices')
      ])
      setNetworkStatus(network)
      setSystemStatus(system)
      setDevices(devicesData.devices || [])
      setError('')
    } catch (err) {
      setError(err.message || 'Failed to fetch status')
    } finally {
      setIsLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleRefresh = () => {
    setRefreshing(true)
    fetchData()
  }

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
        <div className="spinner"></div>
      </div>
    )
  }

  const onlineCount = devices.filter(d => d.is_online).length
  const offlineCount = devices.filter(d => !d.is_online).length
  const wlan0Connected = networkStatus?.wlan0?.connected
  const sys = systemStatus?.system
  const cpuPercent = sys?.cpu_percent || 0
  const memPercent = sys?.memory?.percent || 0
  const diskPercent = sys?.disk?.percent || 0
  const cpuTemp = sys?.cpu_temp || 0
  const uptime = sys?.uptime || 0

  return (
    <div>
      <div className="flex justify-between items-center mb-3">
        <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Dashboard</h1>
        <button onClick={handleRefresh} className="btn btn-secondary" disabled={refreshing}>
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {/* Uplink Connection Info - Dedicated Section */}
      <div className="card" style={{
        background: wlan0Connected ? 'linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(34, 197, 94, 0.05) 100%)' : 'linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%)',
        border: wlan0Connected ? '2px solid var(--success)' : '2px solid var(--error)',
        marginBottom: '1.5rem'
      }}>
        <div className="card-header">
          <div>
            <h3 className="card-title" style={{ fontSize: '1.5rem', marginBottom: '0.25rem' }}>
              🌐 Uplink Connection (wlan0)
            </h3>
            <p className="text-muted" style={{ margin: 0 }}>
              {wlan0Connected ? 'Connected to internet via Wi-Fi' : 'No internet connection'}
            </p>
          </div>
          {wlan0Connected ? (
            <span className="badge badge-success" style={{ fontSize: '1rem', padding: '0.5rem 1rem' }}>
              ● Connected
            </span>
          ) : (
            <span className="badge badge-error" style={{ fontSize: '1rem', padding: '0.5rem 1rem' }}>
              ● Disconnected
            </span>
          )}
        </div>

        {wlan0Connected ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginTop: '1rem' }}>
            <div>
              <div className="text-muted" style={{ fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>
                Network Name (SSID)
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {networkStatus?.wlan0?.ssid || 'Unknown'}
              </div>
            </div>
            <div>
              <div className="text-muted" style={{ fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>
                IP Address
              </div>
              <div style={{
                fontSize: '1.5rem',
                fontWeight: 700,
                color: 'var(--accent)',
                fontFamily: 'monospace'
              }}>
                {networkStatus?.wlan0?.ip_address || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-muted" style={{ fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>
                Gateway
              </div>
              <div style={{ fontSize: '1.25rem', fontWeight: 600, fontFamily: 'monospace' }}>
                {networkStatus?.wlan0?.gateway || 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-muted" style={{ fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.25rem' }}>
                Signal Strength
              </div>
              <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>
                {networkStatus?.wlan0?.signal_strength || 'N/A'}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '0.5rem' }}>
            <p style={{ margin: 0, fontWeight: 500 }}>
              ⚠️ No uplink connection detected. Please configure your Wi-Fi network in the
              <a href="/network" style={{ color: 'var(--accent)', marginLeft: '0.25rem' }}>Network settings</a>.
            </p>
          </div>
        )}
      </div>

      <div className="grid grid-2">
        <StatusCard title="Access Point (wlan1)" status={networkStatus?.wlan1}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div>
              <div className="text-muted" style={{ fontSize: '0.875rem' }}>SSID</div>
              <div style={{ fontWeight: 500 }}>{networkStatus?.wlan1?.ssid || 'N/A'}</div>
            </div>
            <div>
              <div className="text-muted" style={{ fontSize: '0.875rem' }}>IP Address</div>
              <div style={{ fontWeight: 500 }}>{networkStatus?.wlan1?.ip_address || 'N/A'}</div>
            </div>
            <div>
              <div className="text-muted" style={{ fontSize: '0.875rem' }}>Channel</div>
              <div style={{ fontWeight: 500 }}>{networkStatus?.wlan1?.channel || 'N/A'}</div>
            </div>
            <div>
              <div className="text-muted" style={{ fontSize: '0.875rem' }}>Clients</div>
              <div style={{ fontWeight: 500 }}>{onlineCount} / {devices.length}</div>
            </div>
          </div>
        </StatusCard>

        {/* System Resources - htop Style */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">⚡ System Resources</h3>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              Uptime: {formatUptime(uptime)}
            </div>
          </div>

          <div style={{ marginTop: '1rem' }}>
            {/* CPU */}
            <div style={{ marginBottom: '1rem' }}>
              <div className="flex justify-between items-center mb-2">
                <div>
                  <span style={{ fontWeight: 600 }}>CPU</span>
                  {cpuTemp > 0 && (
                    <span className="text-muted" style={{ fontSize: '0.875rem', marginLeft: '1rem' }}>
                      (🌡 {cpuTemp.toFixed(1)}°C)
                    </span>
                  )}
                </div>
                <span style={{ fontWeight: 700, color: getColorForPercent(cpuPercent) }}>
                  {cpuPercent.toFixed(1)}%
                </span>
              </div>
              <div style={{
                background: 'var(--bg-tertiary)',
                borderRadius: '0.25rem',
                height: '8px',
                overflow: 'hidden'
              }}>
                <div style={{
                  background: getColorForPercent(cpuPercent),
                  width: `${cpuPercent}%`,
                  height: '100%',
                  transition: 'width 0.3s ease'
                }}></div>
              </div>
            </div>

            {/* Memory */}
            <div style={{ marginBottom: '1rem' }}>
              <div className="flex justify-between items-center mb-2">
                <span style={{ fontWeight: 600 }}>Memory</span>
                <span style={{ fontWeight: 700, color: getColorForPercent(memPercent) }}>
                  {formatBytes(sys?.memory?.used || 0)} / {formatBytes(sys?.memory?.total || 0)} ({memPercent.toFixed(1)}%)
                </span>
              </div>
              <div style={{
                background: 'var(--bg-tertiary)',
                borderRadius: '0.25rem',
                height: '8px',
                overflow: 'hidden'
              }}>
                <div style={{
                  background: getColorForPercent(memPercent),
                  width: `${memPercent}%`,
                  height: '100%',
                  transition: 'width 0.3s ease'
                }}></div>
              </div>
            </div>

            {/* Disk */}
            <div style={{ marginBottom: '1rem' }}>
              <div className="flex justify-between items-center mb-2">
                <span style={{ fontWeight: 600 }}>Disk</span>
                <span style={{ fontWeight: 700, color: getColorForPercent(diskPercent) }}>
                  {formatBytes(sys?.disk?.used || 0)} / {formatBytes(sys?.disk?.total || 0)} ({diskPercent.toFixed(1)}%)
                </span>
              </div>
              <div style={{
                background: 'var(--bg-tertiary)',
                borderRadius: '0.25rem',
                height: '8px',
                overflow: 'hidden'
              }}>
                <div style={{
                  background: getColorForPercent(diskPercent),
                  width: `${diskPercent}%`,
                  height: '100%',
                  transition: 'width 0.3s ease'
                }}></div>
              </div>
            </div>

            {/* Stats Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '1rem',
              marginTop: '1rem',
              paddingTop: '1rem',
              borderTop: '1px solid var(--border)'
            }}>
              <div style={{ textAlign: 'center' }}>
                <div className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                  Available
                </div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                  {formatBytes((sys?.memory?.available || 0))}
                </div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                  Free
                </div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                  {formatBytes((sys?.disk?.free || 0))}
                </div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
                  Uptime
                </div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                  {formatUptime(uptime)}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card mt-3">
        <div className="card-header">
          <h3 className="card-title">Connected Devices</h3>
          <div className="flex gap-2">
            <span className="badge badge-success">{onlineCount} Online</span>
            {offlineCount > 0 && (
              <span className="badge badge-error">{offlineCount} Offline</span>
            )}
          </div>
        </div>
        <p className="text-muted mb-2" style={{ fontSize: '0.875rem' }}>
          Devices offline for more than 30 minutes are automatically hidden.
        </p>
        {devices.length > 0 ? (
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Device</th>
                  <th>IP Address</th>
                  <th>MAC Address</th>
                  <th>Status</th>
                  <th>Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {devices.map((device, index) => (
                  <tr key={index}>
                    <td>
                      <div style={{ fontWeight: 500 }}>{device.hostname}</div>
                    </td>
                    <td>{device.ip || 'N/A'}</td>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>{device.mac}</td>
                    <td>
                      {device.is_online ? (
                        <span className="badge badge-success">Online</span>
                      ) : (
                        <span className="badge badge-error">Offline</span>
                      )}
                    </td>
                    <td className="text-muted" style={{ fontSize: '0.875rem' }}>{device.time_ago}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <p className="text-muted">No devices connected</p>
            <p className="text-muted" style={{ fontSize: '0.875rem' }}>
              Devices will appear here when they connect to your Access Point.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
