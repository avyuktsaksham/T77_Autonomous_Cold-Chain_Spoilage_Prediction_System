import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './RoomDetail.css';

const RoomDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const roomsData = {
    1: {
      name: 'Vaccine Storage Room',
      item: 'COVID & Insulin Vaccines',
      icon: '💉',
      color: '#10b981',
      requiredTemp: { min: 2, max: 8 },
      requiredHumidity: { min: 30, max: 50 },
      unit: '°C'
    },
    2: {
      name: 'Pharmaceutical Drug Storage',
      item: 'Temperature-Controlled Medicines',
      icon: '💊',
      color: '#3b82f6',
      requiredTemp: { min: 8, max: 15 },
      requiredHumidity: { min: 40, max: 60 },
      unit: '°C'
    },
    3: {
      name: 'Blood & Plasma Storage',
      item: 'Blood Bags & Plasma Units',
      icon: '🩸',
      color: '#ef4444',
      requiredTemp: { min: 1, max: 6 },
      requiredHumidity: { min: 35, max: 55 },
      unit: '°C'
    },
    4: {
      name: 'Dairy Product Storage',
      item: 'Milk, Butter, Cheese, Yogurt',
      icon: '🥛',
      color: '#f59e0b',
      requiredTemp: { min: 2, max: 4 },
      requiredHumidity: { min: 40, max: 60 },
      unit: '°C'
    },
    5: {
      name: 'Frozen Food Storage',
      item: 'Meat, Vegetables, Seafood',
      icon: '🥩',
      color: '#8b5cf6',
      requiredTemp: { min: -20, max: -18 },
      requiredHumidity: { min: 30, max: 40 },
      unit: '°C'
    }
  };

  const room = roomsData[id];
  
  const [liveData, setLiveData] = useState({
    temperature: 0,
    humidity: 0,
    doorStatus: 'Closed',
    powerStatus: 'Active',
    duration: 0,
    lastUpdated: new Date().toLocaleTimeString()
  });

  // Simulate live data updates
  useEffect(() => {
    const interval = setInterval(() => {
      // Simulate realistic temperature fluctuations
      const baseTemp = (room.requiredTemp.min + room.requiredTemp.max) / 2;
      const tempVariation = (Math.random() - 0.5) * 3;
      const newTemp = baseTemp + tempVariation;
      
      // Simulate realistic humidity
      const baseHumidity = (room.requiredHumidity.min + room.requiredHumidity.max) / 2;
      const humidityVariation = (Math.random() - 0.5) * 10;
      const newHumidity = baseHumidity + humidityVariation;
      
      // Random door status (mostly closed)
      const doorOpen = Math.random() > 0.9;
      
      // Random power failure (very rare)
      const powerFail = Math.random() > 0.98;

      setLiveData({
        temperature: parseFloat(newTemp.toFixed(1)),
        humidity: parseFloat(newHumidity.toFixed(1)),
        doorStatus: doorOpen ? 'Open' : 'Closed',
        powerStatus: powerFail ? 'Failed' : 'Active',
        duration: Math.floor(Math.random() * 60),
        lastUpdated: new Date().toLocaleTimeString()
      });
    }, 2000); // Update every 2 seconds

    return () => clearInterval(interval);
  }, [room]);

  // Check for alerts
  const getAlerts = () => {
    const alerts = [];
    
    if (liveData.temperature < room.requiredTemp.min) {
      alerts.push({
        type: 'Temperature Too Low',
        message: `Temperature is ${liveData.temperature}°C (Required: ${room.requiredTemp.min}°C – ${room.requiredTemp.max}°C)`,
        precaution: 'Check cooling system settings. Reduce cooling power to bring temperature up to safe range.',
        severity: 'warning'
      });
    } else if (liveData.temperature > room.requiredTemp.max) {
      alerts.push({
        type: 'Temperature Too High',
        message: `Temperature is ${liveData.temperature}°C (Required: ${room.requiredTemp.min}°C – ${room.requiredTemp.max}°C)`,
        precaution: 'Increase cooling power immediately. Check for door leaks or cooling system malfunction.',
        severity: 'critical'
      });
    }
    
    if (liveData.humidity < room.requiredHumidity.min) {
      alerts.push({
        type: 'Humidity Too Low',
        message: `Humidity is ${liveData.humidity}% (Required: ${room.requiredHumidity.min}% – ${room.requiredHumidity.max}%)`,
        precaution: 'Add humidifier or check ventilation system. Low humidity can affect product quality.',
        severity: 'warning'
      });
    } else if (liveData.humidity > room.requiredHumidity.max) {
      alerts.push({
        type: 'Humidity Too High',
        message: `Humidity is ${liveData.humidity}% (Required: ${room.requiredHumidity.min}% – ${room.requiredHumidity.max}%)`,
        precaution: 'Check dehumidifier. High humidity can cause condensation and spoilage.',
        severity: 'warning'
      });
    }
    
    if (liveData.doorStatus === 'Open') {
      alerts.push({
        type: 'Door Open',
        message: 'Storage door is currently open',
        precaution: 'Close door immediately to prevent temperature loss and maintain cold chain integrity.',
        severity: 'critical'
      });
    }
    
    if (liveData.powerStatus === 'Failed') {
      alerts.push({
        type: 'Power Failure',
        message: 'Power supply to cooling system has failed',
        precaution: 'Switch to backup power immediately. Contact maintenance team urgently.',
        severity: 'critical'
      });
    }
    
    return alerts;
  };

  const alerts = getAlerts();

  if (!room) {
    return <div>Room not found</div>;
  }

  return (
    <div className="room-detail-page">
      <button className="back-button" onClick={() => navigate('/rooms')}>
        ← Back to Rooms
      </button>

      <div className="room-detail-container">
        {/* Left Section - Item Info */}
        <div className="left-section">
          <div className="item-card" style={{ '--room-color': room.color }}>
            <div className="item-icon">{room.icon}</div>
            <h2 className="item-name">{room.item}</h2>
            <div className="room-label">{room.name}</div>
            
            <div className="required-params">
              <h3>Required Conditions</h3>
              <div className="param-row">
                <span className="param-label">Temperature:</span>
                <span className="param-value">{room.requiredTemp.min}°C – {room.requiredTemp.max}°C</span>
              </div>
              <div className="param-row">
                <span className="param-label">Humidity:</span>
                <span className="param-value">{room.requiredHumidity.min}% – {room.requiredHumidity.max}%</span>
              </div>
              <div className="param-row">
                <span className="param-label">Door:</span>
                <span className="param-value">Must be Closed</span>
              </div>
              <div className="param-row">
                <span className="param-label">Power:</span>
                <span className="param-value">Must be Active</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Section - Live Data */}
        <div className="right-section">
          {/* Top - Live Parameters */}
          <div className="live-params">
            <div className="section-header">
              <h2>Live Monitoring</h2>
              <div className="live-indicator">
                <span className="live-dot"></span>
                <span>Live</span>
                <span className="update-time">Updated: {liveData.lastUpdated}</span>
              </div>
            </div>

            <div className="params-grid">
              <div className={`param-card ${liveData.temperature >= room.requiredTemp.min && liveData.temperature <= room.requiredTemp.max ? 'param-safe' : 'param-alert'}`}>
                <div className="param-icon">🌡️</div>
                <div className="param-info">
                  <div className="param-title">Temperature</div>
                  <div className="param-current">{liveData.temperature}°C</div>
                  <div className="param-required">Safe: {room.requiredTemp.min}°C – {room.requiredTemp.max}°C</div>
                </div>
              </div>

              <div className={`param-card ${liveData.humidity >= room.requiredHumidity.min && liveData.humidity <= room.requiredHumidity.max ? 'param-safe' : 'param-alert'}`}>
                <div className="param-icon">💧</div>
                <div className="param-info">
                  <div className="param-title">Humidity</div>
                  <div className="param-current">{liveData.humidity}%</div>
                  <div className="param-required">Safe: {room.requiredHumidity.min}% – {room.requiredHumidity.max}%</div>
                </div>
              </div>

              <div className={`param-card ${liveData.doorStatus === 'Closed' ? 'param-safe' : 'param-alert'}`}>
                <div className="param-icon">🚪</div>
                <div className="param-info">
                  <div className="param-title">Door Status</div>
                  <div className="param-current">{liveData.doorStatus}</div>
                  <div className="param-required">Required: Closed</div>
                </div>
              </div>

              <div className={`param-card ${liveData.powerStatus === 'Active' ? 'param-safe' : 'param-alert'}`}>
                <div className="param-icon">⚡</div>
                <div className="param-info">
                  <div className="param-title">Power Status</div>
                  <div className="param-current">{liveData.powerStatus}</div>
                  <div className="param-required">Required: Active</div>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom - Alert System */}
          <div className="alert-system">
            <h2>Alert System</h2>
            {alerts.length === 0 ? (
              <div className="no-alerts">
                <div className="success-icon">✓</div>
                <div className="success-message">All parameters are within safe range</div>
                <div className="success-sub">System operating normally</div>
              </div>
            ) : (
              <div className="alerts-list">
                {alerts.map((alert, index) => (
                  <div key={index} className={`alert-card alert-${alert.severity}`}>
                    <div className="alert-header">
                      <span className="alert-icon">⚠️</span>
                      <span className="alert-type">{alert.type}</span>
                    </div>
                    <div className="alert-message">{alert.message}</div>
                    <div className="alert-precaution">
                      <strong>Precaution:</strong> {alert.precaution}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RoomDetail;
