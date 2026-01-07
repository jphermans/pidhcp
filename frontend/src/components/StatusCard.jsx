import { useState } from 'react'

export default function StatusCard({ title, status, children, loading = false }) {
  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">{title}</h3>
        {status && (
          <span className={`badge ${status.connected || status.running ? 'badge-success' : 'badge-error'}`}>
            {status.connected || status.running ? 'Connected' : 'Disconnected'}
          </span>
        )}
      </div>
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}>
          <div className="spinner"></div>
        </div>
      ) : (
        children
      )}
    </div>
  )
}
