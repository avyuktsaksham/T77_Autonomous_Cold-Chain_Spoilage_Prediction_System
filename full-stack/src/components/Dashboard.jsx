import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './Dashboard.css';

function Dashboard({ truckId, onBack }) {
  const [sensorData, setSensorData] = useState(null);
  const [riskAnalysis, setRiskAnalysis] = useState(null);
  const [summary, setSummary] = useState(null);
  const [predictions, setPredictions] = useState(null);
  const [decisions, setDecisions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [dataTick, setDataTick] = useState(0);
  const lastTimestampRef = useRef(null);

  useEffect(() => {
    fetchData();
    
    if (autoRefresh) {
      const interval = setInterval(fetchData, 3000);
      return () => clearInterval(interval);
    }
  }, [truckId, autoRefresh]);

  const fetchData = async () => {
    try {
      if (!sensorData) {
        setLoading(true);
      }

      const sensorRes = await axios.get(`/api/sensors/${truckId}`);
      const sourceTimestamp = sensorRes.data?.timestamp;
      const timestampParam = sourceTimestamp ? `?timestamp=${encodeURIComponent(sourceTimestamp)}` : '';

      const [riskRes, summaryRes, predictionsRes, decisionsRes] = await Promise.all([
        axios.get(`/api/risk/${truckId}${timestampParam}`),
        axios.get(`/api/summary/${truckId}${timestampParam}`),
        axios.get(`/api/predictions/${truckId}`),
        axios.get(`/api/decisions/${truckId}`)
      ]);

      setSensorData(sensorRes.data);
      setRiskAnalysis(riskRes.data);
      setSummary(summaryRes.data);
      setPredictions(predictionsRes.data);
      setDecisions(decisionsRes.data);
      if (sourceTimestamp && lastTimestampRef.current !== sourceTimestamp) {
        lastTimestampRef.current = sourceTimestamp;
        setDataTick((prev) => prev + 1);
      }
      setError(null);
    } catch (err) {
      setError('Failed to load data. Please try again.');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (riskLevel) => {
    switch (riskLevel) {
      case 'CRITICAL':
        return '#111111';
      case 'HIGH':
        return '#2f2f2f';
      case 'MEDIUM':
        return '#525252';
      case 'LOW':
        return '#6f6f6f';
      default:
        return '#7f7f7f';
    }
  };

  const renderCircularGauge = (value, min, max, label, unit) => {
    const percentage = ((value - min) / (max - min)) * 100;
    const circumference = 2 * Math.PI * 45;
    const offset = circumference - (percentage / 100) * circumference;

    return (
      <div className="gauge value-updated" key={`${label}-${dataTick}`}>
        <svg viewBox="0 0 100 100" className="gauge-svg">
          <circle
            cx="50"
            cy="50"
            r="45"
            className="gauge-background"
          />
          <circle
            cx="50"
            cy="50"
            r="45"
            className="gauge-progress"
            style={{
              strokeDasharray: circumference,
              strokeDashoffset: offset
            }}
          />
        </svg>
        <div className="gauge-content">
          <div className="gauge-value">{value.toFixed(1)}</div>
          <div className="gauge-unit">{unit}</div>
          <div className="gauge-label">{label}</div>
        </div>
      </div>
    );
  };

  if (loading && !sensorData) {
    return (
      <div className="dashboard-container">
        <div className="loading-state">Loading truck data...</div>
      </div>
    );
  }

  if (error && !sensorData) {
    return (
      <div className="dashboard-container">
        <div className="error-state">{error}</div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <button className="back-button" onClick={onBack}>← Back to Trucks</button>
        <div className="header-title">
          <h1>{truckId}</h1>
          <p>{sensorData?.cargo_type || 'Unknown'} | Scenario: {sensorData?.scenario || 'N/A'}</p>
        </div>
        <div className="header-actions">
          <button
            className={`refresh-button ${autoRefresh ? 'active' : ''}`}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? 'Pause' : 'Resume'}
          </button>
          <button className="refresh-button" onClick={fetchData}>
            Refresh
          </button>
        </div>
      </div>

      {/* Risk Alert Banner */}
      {riskAnalysis && (
        <div
          className="risk-banner value-updated"
          key={`risk-banner-${dataTick}`}
          style={{ backgroundColor: getRiskColor(riskAnalysis.risk_level) + '20', borderLeftColor: getRiskColor(riskAnalysis.risk_level) }}
        >
          <div className="risk-banner-content">
            <div className="risk-info">
              <h3>Risk Level: {riskAnalysis.risk_level}</h3>
              <p>Risk Score: {riskAnalysis.risk_score}/100</p>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="dashboard-content">
        {/* Sensor Data Section */}
        {sensorData && (
          <section className="dashboard-section sensor-section">
            <h2>Live Sensor Data</h2>
            <div className="sensors-grid">
              {renderCircularGauge(sensorData.temperature, -5, 15, 'Temperature', '°C')}
              {renderCircularGauge(sensorData.humidity, 0, 100, 'Humidity', '%')}
              {renderCircularGauge(sensorData.vibration, 0, 10, 'Vibration', 'g')}
            </div>

            <div className="sensor-details">
              <h3>Additional Information</h3>
              <div className="details-grid">
                <div className="detail-card">
                  <span className="detail-label">GPS Location</span>
                  <span className="detail-value">{sensorData.gps_lat?.toFixed(4)}°, {sensorData.gps_lon?.toFixed(4)}°</span>
                </div>
                <div className="detail-card">
                  <span className="detail-label">Door Status</span>
                  <span className="detail-value">{sensorData.door_open ? '🔓 Open' : '🔒 Closed'}</span>
                </div>
                <div className="detail-card">
                  <span className="detail-label">Refrigeration</span>
                  <span className="detail-value">{sensorData.refrigeration_failed ? '❌ Failed' : '✅ Working'}</span>
                </div>
                <div className="detail-card">
                  <span className="detail-label">Last Updated</span>
                  <span className="detail-value">{new Date(sensorData.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Predictions vs Actual Risk Section */}
        {predictions && riskAnalysis && (
          <section className="dashboard-section predictions-section">
            <h2>ML Predictions vs Actual Risk</h2>
            <div className="predictions-grid">
              <div className="prediction-card">
                <h4>Actual Risk</h4>
                <div className="risk-value" style={{ color: getRiskColor(riskAnalysis.risk_level) }}>
                  {(riskAnalysis.risk_score / 100).toFixed(2)}
                </div>
                <p className="risk-level">{riskAnalysis.risk_level}</p>
              </div>
              <div className="prediction-card">
                <h4>Predicted Risk</h4>
                <div className="risk-value" style={{ color: getRiskColor(predictions.predicted_risk >= 0.5 ? 'HIGH' : 'LOW') }}>
                  {predictions.predicted_risk !== null && predictions.predicted_risk !== undefined
                    ? predictions.predicted_risk.toFixed(2)
                    : 'N/A'}
                </div>
                <p className="risk-level">
                  {predictions.predicted_risk !== null && predictions.predicted_risk !== undefined
                    ? (predictions.predicted_risk >= 0.5 ? 'HIGH' : 'LOW')
                    : 'NOT AVAILABLE'}
                </p>
              </div>
              <div className="prediction-card">
                <h4>Time to Failure</h4>
                <div className="risk-value">
                  {predictions.time_to_failure_hours !== null && predictions.time_to_failure_hours !== undefined
                    ? predictions.time_to_failure_hours.toFixed(1)
                    : 'N/A'}
                </div>
                <p className="risk-level">
                  {predictions.time_to_failure_hours !== null && predictions.time_to_failure_hours !== undefined ? 'Hours' : 'NOT AVAILABLE'}
                </p>
              </div>
            </div>
            {predictions.message && <p className="prediction-note">{predictions.message}</p>}
          </section>
        )}

        {/* Nearest Centres & Navigation Section */}
        {decisions && decisions.nearest_centres && decisions.nearest_centres.length > 0 && (
          <section className="dashboard-section centres-section">
            <h2>Nearest Distribution Centres</h2>
            <div className="centres-list">
              {decisions.nearest_centres.map((centre, idx) => (
                <div key={idx} className="centre-card">
                  <div className="centre-header">
                    <h4>{centre.name}</h4>
                    <span className="centre-badge">#{idx + 1}</span>
                  </div>
                  <div className="centre-details">
                    <div className="detail">
                      <span className="label">📍 Distance:</span>
                      <span className="value">{centre.distance_km.toFixed(1)} km</span>
                    </div>
                    <div className="detail">
                      <span className="label">🕒 ETA:</span>
                      <span className="value">{centre.eta_hours.toFixed(1)} hours</span>
                    </div>
                    <div className="detail">
                      <span className="label">📦 Available Capacity:</span>
                      <span className="value">{centre.available_capacity} units</span>
                    </div>
                    <div className="detail">
                      <span className="label">📌 Location:</span>
                      <span className="value">{centre.location[0]?.toFixed(4)}°, {centre.location[1]?.toFixed(4)}°</span>
                    </div>
                  </div>
                  {idx === 0 && <div className="centre-recommended">✅ Recommended</div>}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Routing Recommendation Section */}
        {decisions && decisions.routing_recommendation && (
          <section className="dashboard-section routing-section">
            <h2>Navigation and Routing</h2>
            <div className="routing-info">
              {decisions.routing_recommendation.recommendation && (
                <div className="routing-card">
                  <h4>Route Recommendation</h4>
                  <p>{decisions.routing_recommendation.recommendation}</p>
                </div>
              )}
              {decisions.routing_recommendation.alternate_destination && (
                <div className="routing-card">
                  <h4>Alternate Route Available</h4>
                  <p>{decisions.routing_recommendation.alternate_destination}</p>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Risk Analysis Section */}
        {riskAnalysis && (
          <section className="dashboard-section risk-section">
            <h2>Risk Analysis</h2>
            <div className="risk-score-display">
              <div className="risk-score-circle" style={{ backgroundColor: getRiskColor(riskAnalysis.risk_level) + '30', borderColor: getRiskColor(riskAnalysis.risk_level) }}>
                <div className="risk-score-number">{riskAnalysis.risk_score}</div>
                <div className="risk-score-label">/ 100</div>
              </div>
              <div className="risk-details">
                <p><strong>Status:</strong> <span style={{ color: getRiskColor(riskAnalysis.risk_level), fontWeight: 'bold' }}>{riskAnalysis.risk_level}</span></p>
                <p><strong>Based on Sensor Time:</strong> {riskAnalysis.source_timestamp ? new Date(riskAnalysis.source_timestamp).toLocaleString() : 'N/A'}</p>
              </div>
            </div>

            {riskAnalysis.warnings && riskAnalysis.warnings.length > 0 && (
              <div className="warnings-section">
                <h3>⚡ Warnings</h3>
                <ul className="warnings-list">
                  {riskAnalysis.warnings.map((warning, idx) => (
                    <li key={idx}>⚠️ {warning}</li>
                  ))}
                </ul>
              </div>
            )}

            {(!riskAnalysis.warnings || riskAnalysis.warnings.length === 0) && (
              <div className="no-warnings">
                ✅ No warnings - All conditions are within acceptable ranges
              </div>
            )}
          </section>
        )}

        {/* Summary Section */}
        {summary && (
          <section className="dashboard-section summary-section">
            <h2>AI-Generated Summary</h2>
            <div className="summary-card">
              <p className="summary-text">{summary.summary}</p>
            </div>

            {summary.warnings && (
              <div className="summary-warnings">
                <h3>Key Issues</h3>
                <p>{summary.warnings || 'No issues detected'}</p>
              </div>
            )}

            {summary.recommendation && (
              <div className="recommendation-box">
                <h3>Recommendations</h3>
                <p>{summary.recommendation}</p>
              </div>
            )}
          </section>
        )}
      </div>

      {/* Footer */}
      <div className="dashboard-footer">
        <p>Last updated: {new Date().toLocaleString()}</p>
        {autoRefresh && <p>Auto-refreshing every 3 seconds</p>}
      </div>
    </div>
  );
}

export default Dashboard;
