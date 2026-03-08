import { useNavigate } from 'react-router-dom';
import './Rooms.css';

const Rooms = () => {
  const navigate = useNavigate();

  const rooms = [
    {
      id: 1,
      name: 'Vaccine Storage Room',
      description: 'COVID, Polio, Insulin vaccines',
      tempRange: '2°C – 8°C',
      icon: '💉',
      color: '#10b981'
    },
    {
      id: 2,
      name: 'Pharmaceutical Drug Storage',
      description: 'Temperature-controlled medicines',
      tempRange: '8°C – 15°C',
      icon: '💊',
      color: '#3b82f6'
    },
    {
      id: 3,
      name: 'Blood & Plasma Storage',
      description: 'Blood bags and plasma units',
      tempRange: '1°C – 6°C',
      icon: '🩸',
      color: '#ef4444'
    },
    {
      id: 4,
      name: 'Dairy Product Storage',
      description: 'Milk, butter, cheese, yogurt',
      tempRange: '2°C – 4°C',
      icon: '🥛',
      color: '#f59e0b'
    },
    {
      id: 5,
      name: 'Frozen Food Storage',
      description: 'Meat, vegetables, seafood',
      tempRange: '-18°C or below',
      icon: '🥩',
      color: '#8b5cf6'
    }
  ];

  return (
    <div className="rooms-page">
      <div className="rooms-header">
        <h1 className="rooms-title">Cold Storage Rooms</h1>
        <p className="rooms-subtitle">Select a room to monitor live conditions</p>
      </div>

      <div className="rooms-grid">
        {rooms.map(room => (
          <div 
            key={room.id} 
            className="room-card"
            onClick={() => navigate(`/room/${room.id}`)}
            style={{ '--room-color': room.color }}
          >
            <div className="room-icon">{room.icon}</div>
            <h3 className="room-name">{room.name}</h3>
            <p className="room-description">{room.description}</p>
            <div className="room-temp">
              <span className="temp-label">Required Temp:</span>
              <span className="temp-value">{room.tempRange}</span>
            </div>
            <div className="room-status">
              <span className="status-dot"></span>
              <span>Live Monitoring</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Rooms;
