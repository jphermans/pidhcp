import { useState, useEffect } from 'react'
import { api } from '../services/api'

export default function BackupPage() {
  const [backups, setBackups] = useState([])
  const [settings, setSettings] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('local')
  const [syncProvider, setSyncProvider] = useState('s3')

  // Form states
  const [backupName, setBackupName] = useState('')
  const [showSyncForm, setShowSyncForm] = useState(false)
  const [selectedBackup, setSelectedBackup] = useState(null)

  // Sync form states
  const [s3Config, setS3Config] = useState({ access_key: '', secret_key: '', bucket: '', region: 'us-east-1' })
  const [rsyncConfig, setRsyncConfig] = useState({ host: '', user: 'pi', path: '~/backups', port: 22 })
  const [ftpConfig, setFtpConfig] = useState({ host: '', port: 21, user: '', password: '', path: '/' })
  const [webdavConfig, setWebdavConfig] = useState({
    url: '',
    username: '',
    password: '',
    path: '/pi-router-backups',
    verify_ssl: true
  })

  const fetchBackups = async () => {
    try {
      const data = await api.get('/api/backup/list')
      setBackups(data.backups || [])
      setError('')
    } catch (err) {
      setError(err.message || 'Failed to fetch backups')
    } finally {
      setIsLoading(false)
    }
  }

  const exportSettings = async () => {
    try {
      const data = await api.get('/api/backup/export')
      const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `pi-router-settings-${new Date().toISOString().split('T')[0]}.json`
      a.click()
      URL.revokeObjectURL(url)
      alert('Settings exported successfully!')
    } catch (err) {
      setError(err.message || 'Failed to export settings')
    }
  }

  const importSettings = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    try {
      const text = await file.text()
      const data = JSON.parse(text)
      await api.post('/api/backup/import', { settings: data.settings })
      alert('Settings imported successfully! Please reload the page.')
      window.location.reload()
    } catch (err) {
      setError(err.message || 'Failed to import settings')
    }
  }

  const createBackup = async () => {
    try {
      await api.post('/api/backup/create', { name: backupName || null })
      setBackupName('')
      fetchBackups()
      alert('Backup created successfully!')
    } catch (err) {
      setError(err.message || 'Failed to create backup')
    }
  }

  const restoreBackup = async (name) => {
    if (!confirm(`Are you sure you want to restore backup "${name}"? This will replace current settings.`)) {
      return
    }

    try {
      await api.post('/api/backup/restore', { name })
      alert('Backup restored successfully! Please reload the page.')
      window.location.reload()
    } catch (err) {
      setError(err.message || 'Failed to restore backup')
    }
  }

  const deleteBackup = async (name) => {
    if (!confirm(`Are you sure you want to delete backup "${name}"?`)) {
      return
    }

    try {
      await api.delete(`/api/backup/${name}`)
      fetchBackups()
      alert('Backup deleted successfully!')
    } catch (err) {
      setError(err.message || 'Failed to delete backup')
    }
  }

  const syncBackup = async () => {
    if (!selectedBackup) {
      alert('Please select a backup to sync')
      return
    }

    try {
      let endpoint = '/api/backup/sync/'
      let config = {}

      switch (syncProvider) {
        case 's3':
          endpoint += 's3'
          config = { ...s3Config, backup_name: selectedBackup }
          break
        case 'rsync':
          endpoint += 'rsync'
          config = { ...rsyncConfig, backup_name: selectedBackup }
          break
        case 'ftp':
          endpoint += 'ftp'
          config = { ...ftpConfig, backup_name: selectedBackup }
          break
        case 'webdav':
          endpoint += 'webdav'
          config = { ...webdavConfig, backup_name: selectedBackup }
          break
      }

      const result = await api.post(endpoint, config)
      alert(`Backup synced to ${syncProvider.toUpperCase()}!\nLocation: ${result.location}`)
      setShowSyncForm(false)
    } catch (err) {
      setError(err.message || 'Failed to sync backup')
    }
  }

  useEffect(() => {
    fetchBackups()
  }, [])

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
        <div className="spinner"></div>
      </div>
    )
  }

  return (
    <div>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '1.5rem' }}>💾 Backup & Sync</h1>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <button
          className={`btn ${activeTab === 'local' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('local')}
        >
          📁 Local Backups
        </button>
        <button
          className={`btn ${activeTab === 'sync' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('sync')}
        >
          🔄 Cloud Sync
        </button>
        <button
          className={`btn ${activeTab === 'settings' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('settings')}
        >
          ⚙️ Import/Export
        </button>
      </div>

      {/* Local Backups Tab */}
      {activeTab === 'local' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Local Backups</h3>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                placeholder="Backup name (optional)"
                value={backupName}
                onChange={(e) => setBackupName(e.target.value)}
                style={{ padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid var(--border)', background: 'var(--bg-tertiary)', color: 'var(--text-primary)' }}
              />
              <button className="btn btn-primary" onClick={createBackup}>
                ➕ Create Backup
              </button>
            </div>
          </div>

          {backups.length > 0 ? (
            <div className="table-responsive">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Created</th>
                    <th>Size</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {backups.map((backup, index) => (
                    <tr key={index}>
                      <td>
                        <div style={{ fontWeight: 500 }}>{backup.name}</div>
                      </td>
                      <td>{new Date(backup.created_at).toLocaleString()}</td>
                      <td>{backup.size_mb?.toFixed(2)} MB</td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                          <button
                            className="btn btn-sm btn-success"
                            onClick={() => restoreBackup(backup.name)}
                          >
                            ↩️ Restore
                          </button>
                          <button
                            className="btn btn-sm btn-secondary"
                            onClick={() => {
                              setSelectedBackup(backup.name)
                              setShowSyncForm(true)
                              setActiveTab('sync')
                            }}
                          >
                            🔄 Sync
                          </button>
                          <button
                            className="btn btn-sm btn-error"
                            onClick={() => deleteBackup(backup.name)}
                          >
                            🗑️ Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '2rem' }}>
              <p className="text-muted">No backups found</p>
              <p className="text-muted" style={{ fontSize: '0.875rem' }}>
                Create a backup to get started
              </p>
            </div>
          )}
        </div>
      )}

      {/* Cloud Sync Tab */}
      {activeTab === 'sync' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Cloud Sync</h3>
            {selectedBackup && (
              <span className="badge badge-success">Selected: {selectedBackup}</span>
            )}
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label className="form-label">Select Backup to Sync</label>
            <select
              className="form-select"
              value={selectedBackup || ''}
              onChange={(e) => setSelectedBackup(e.target.value)}
            >
              <option value="">-- Select a backup --</option>
              {backups.map((backup) => (
                <option key={backup.name} value={backup.name}>
                  {backup.name} ({backup.size_mb?.toFixed(2)} MB)
                </option>
              ))}
            </select>
          </div>

          {/* Sync Provider Selection */}
          <div style={{ marginBottom: '1rem' }}>
            <label className="form-label">Sync Provider</label>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button
                className={`btn ${syncProvider === 's3' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setSyncProvider('s3')}
              >
                📦 AWS S3
              </button>
              <button
                className={`btn ${syncProvider === 'rsync' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setSyncProvider('rsync')}
              >
                🔄 Rsync
              </button>
              <button
                className={`btn ${syncProvider === 'ftp' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setSyncProvider('ftp')}
              >
                🌐 FTP
              </button>
              <button
                className={`btn ${syncProvider === 'webdav' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setSyncProvider('webdav')}
              >
                ☁️ WebDAV
              </button>
            </div>
          </div>

          {/* Sync Configuration Forms */}
          {syncProvider === 's3' && (
            <div className="grid grid-2">
              <div>
                <label className="form-label">Access Key</label>
                <input
                  type="text"
                  className="form-input"
                  value={s3Config.access_key}
                  onChange={(e) => setS3Config({ ...s3Config, access_key: e.target.value })}
                  placeholder="AWS Access Key ID"
                />
              </div>
              <div>
                <label className="form-label">Secret Key</label>
                <input
                  type="password"
                  className="form-input"
                  value={s3Config.secret_key}
                  onChange={(e) => setS3Config({ ...s3Config, secret_key: e.target.value })}
                  placeholder="AWS Secret Access Key"
                />
              </div>
              <div>
                <label className="form-label">Bucket</label>
                <input
                  type="text"
                  className="form-input"
                  value={s3Config.bucket}
                  onChange={(e) => setS3Config({ ...s3Config, bucket: e.target.value })}
                  placeholder="my-backup-bucket"
                />
              </div>
              <div>
                <label className="form-label">Region</label>
                <input
                  type="text"
                  className="form-input"
                  value={s3Config.region}
                  onChange={(e) => setS3Config({ ...s3Config, region: e.target.value })}
                  placeholder="us-east-1"
                />
              </div>
            </div>
          )}

          {syncProvider === 'rsync' && (
            <div className="grid grid-2">
              <div>
                <label className="form-label">Host</label>
                <input
                  type="text"
                  className="form-input"
                  value={rsyncConfig.host}
                  onChange={(e) => setRsyncConfig({ ...rsyncConfig, host: e.target.value })}
                  placeholder="backup.example.com"
                />
              </div>
              <div>
                <label className="form-label">User</label>
                <input
                  type="text"
                  className="form-input"
                  value={rsyncConfig.user}
                  onChange={(e) => setRsyncConfig({ ...rsyncConfig, user: e.target.value })}
                  placeholder="pi"
                />
              </div>
              <div>
                <label className="form-label">Path</label>
                <input
                  type="text"
                  className="form-input"
                  value={rsyncConfig.path}
                  onChange={(e) => setRsyncConfig({ ...rsyncConfig, path: e.target.value })}
                  placeholder="~/backups"
                />
              </div>
              <div>
                <label className="form-label">Port</label>
                <input
                  type="number"
                  className="form-input"
                  value={rsyncConfig.port}
                  onChange={(e) => setRsyncConfig({ ...rsyncConfig, port: parseInt(e.target.value) })}
                  placeholder="22"
                />
              </div>
            </div>
          )}

          {syncProvider === 'ftp' && (
            <div className="grid grid-2">
              <div>
                <label className="form-label">Host</label>
                <input
                  type="text"
                  className="form-input"
                  value={ftpConfig.host}
                  onChange={(e) => setFtpConfig({ ...ftpConfig, host: e.target.value })}
                  placeholder="ftp.example.com"
                />
              </div>
              <div>
                <label className="form-label">Port</label>
                <input
                  type="number"
                  className="form-input"
                  value={ftpConfig.port}
                  onChange={(e) => setFtpConfig({ ...ftpConfig, port: parseInt(e.target.value) })}
                  placeholder="21"
                />
              </div>
              <div>
                <label className="form-label">Username</label>
                <input
                  type="text"
                  className="form-input"
                  value={ftpConfig.user}
                  onChange={(e) => setFtpConfig({ ...ftpConfig, user: e.target.value })}
                  placeholder="ftpuser"
                />
              </div>
              <div>
                <label className="form-label">Password</label>
                <input
                  type="password"
                  className="form-input"
                  value={ftpConfig.password}
                  onChange={(e) => setFtpConfig({ ...ftpConfig, password: e.target.value })}
                  placeholder="password"
                />
              </div>
              <div>
                <label className="form-label">Path</label>
                <input
                  type="text"
                  className="form-input"
                  value={ftpConfig.path}
                  onChange={(e) => setFtpConfig({ ...ftpConfig, path: e.target.value })}
                  placeholder="/"
                />
              </div>
            </div>
          )}

          {syncProvider === 'webdav' && (
            <div className="grid grid-2">
              <div style={{ gridColumn: 'span 2' }}>
                <label className="form-label">WebDAV URL</label>
                <input
                  type="text"
                  className="form-input"
                  value={webdavConfig.url}
                  onChange={(e) => setWebdavConfig({ ...webdavConfig, url: e.target.value })}
                  placeholder="https://cloud.example.com/remote.php/webdav/"
                />
              </div>
              <div>
                <label className="form-label">Username</label>
                <input
                  type="text"
                  className="form-input"
                  value={webdavConfig.username}
                  onChange={(e) => setWebdavConfig({ ...webdavConfig, username: e.target.value })}
                  placeholder="username"
                />
              </div>
              <div>
                <label className="form-label">Password</label>
                <input
                  type="password"
                  className="form-input"
                  value={webdavConfig.password}
                  onChange={(e) => setWebdavConfig({ ...webdavConfig, password: e.target.value })}
                  placeholder="password"
                />
              </div>
              <div>
                <label className="form-label">Path</label>
                <input
                  type="text"
                  className="form-input"
                  value={webdavConfig.path}
                  onChange={(e) => setWebdavConfig({ ...webdavConfig, path: e.target.value })}
                  placeholder="/pi-router-backups"
                />
              </div>
              <div>
                <label className="form-label">Verify SSL</label>
                <select
                  className="form-select"
                  value={webdavConfig.verify_ssl}
                  onChange={(e) => setWebdavConfig({ ...webdavConfig, verify_ssl: e.target.value === 'true' })}
                >
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </div>
            </div>
          )}

          <div style={{ marginTop: '1rem' }}>
            <button
              className="btn btn-primary"
              onClick={syncBackup}
              disabled={!selectedBackup}
            >
              🚀 Sync to {syncProvider.toUpperCase()}
            </button>
          </div>
        </div>
      )}

      {/* Import/Export Tab */}
      {activeTab === 'settings' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Import/Export Settings</h3>
          </div>

          <div style={{ marginBottom: '2rem' }}>
            <h4 style={{ marginBottom: '1rem' }}>📤 Export Settings</h4>
            <p className="text-muted" style={{ marginBottom: '1rem' }}>
              Download your settings as a JSON file for manual backup or migration.
            </p>
            <button className="btn btn-primary" onClick={exportSettings}>
              📥 Export Settings
            </button>
          </div>

          <div>
            <h4 style={{ marginBottom: '1rem' }}>📥 Import Settings</h4>
            <p className="text-muted" style={{ marginBottom: '1rem' }}>
              Upload a previously exported settings JSON file to restore your configuration.
            </p>
            <input
              type="file"
              accept=".json"
              onChange={importSettings}
              style={{ display: 'none' }}
              id="import-file"
            />
            <label htmlFor="import-file" className="btn btn-secondary">
              📤 Import Settings
            </label>
          </div>
        </div>
      )}
    </div>
  )
}
