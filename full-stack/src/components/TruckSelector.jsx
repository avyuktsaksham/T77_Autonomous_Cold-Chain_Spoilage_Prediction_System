import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './TruckSelector.css';

function TruckSelector({ onSelectTruck, onBack }) {
  const [trucks, setTrucks] = useState([]);
  const [filteredTrucks, setFilteredTrucks] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAllTrucks();
  }, []);

  const fetchAllTrucks = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/all-data');
      
      // Group by asset_id to get unique trucks
      const uniqueTrucks = {};
      response.data.forEach(item => {
        if (!uniqueTrucks[item.asset_id]) {
          uniqueTrucks[item.asset_id] = item;
        }
      });
      
      const truckList = Object.values(uniqueTrucks);
      setTrucks(truckList);
      setFilteredTrucks(truckList);
      setError(null);
    } catch (err) {
      setError('Failed to load trucks. Please try again.');
      console.error('Error fetching trucks:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (query) => {
    setSearchQuery(query);
    if (query.trim() === '') {
      setFilteredTrucks(trucks);
    } else {
      const filtered = trucks.filter(truck =>
        truck.asset_id.toLowerCase().includes(query.toLowerCase()) ||
        truck.cargo_type.toLowerCase().includes(query.toLowerCase())
      );
      setFilteredTrucks(filtered);
    }
  };

  const getRiskColor = (riskScore) => {
    if (riskScore >= 50) return '#dc2626';
    if (riskScore >= 30) return '#f59e0b';
    if (riskScore >= 15) return '#eab308';
    return '#10b981';
  };

  return (
    <div className="truck-selector-container">
      <div className="selector-header">
        <button className="back-button" onClick={onBack}>← Back</button>
        <h1>Select a Shipment to Monitor</h1>
        <p className="selector-subtitle">Choose from {trucks.length} active shipments</p>
      </div>

      <div className="search-section">
        <input
          type="text"
          placeholder="Search by truck ID or cargo type..."
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          className="search-input"
        />
      </div>

      {loading ? (
        <div className="loading">Loading trucks...</div>
      ) : error ? (
        <div className="error-message">{error}</div>
      ) : filteredTrucks.length === 0 ? (
        <div className="no-results">No trucks found</div>
      ) : (
        <div className="trucks-grid">
          {filteredTrucks.map((truck) => (
            <div
              key={truck.asset_id}
              className="truck-card"
              onClick={() => onSelectTruck(truck.asset_id)}
            >
              <div className="truck-card-header">
                <h3>{truck.asset_id}</h3>
                <span className="cargo-badge">{truck.cargo_type}</span>
              </div>
              <div className="truck-card-body">
                <div className="truck-info">
                  <p><span className="label">Temp:</span> {truck.temperature?.toFixed(2)}°C</p>
                  <p><span className="label">Humidity:</span> {truck.humidity?.toFixed(2)}%</p>
                  <p><span className="label">Vibration:</span> {truck.vibration?.toFixed(2)}g</p>
                </div>
                <div className="truck-status">
                  <p><span className="label">Status:</span> <span className="status-badge active">Active</span></p>
                  <p><span className="label">Scenario:</span> {truck.scenario}</p>
                </div>
              </div>
              <div className="truck-card-footer">
                <button className="view-button">View Details</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default TruckSelector;
