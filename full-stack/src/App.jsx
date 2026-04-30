import React, { useState } from 'react';
import Intro from './components/Intro';
import TruckSelector from './components/TruckSelector';
import Dashboard from './components/Dashboard';
import './App.css';

function App() {
  const [currentPage, setCurrentPage] = useState('intro'); // 'intro', 'selector', 'dashboard'
  const [selectedTruck, setSelectedTruck] = useState(null);

  const handleGetStarted = () => {
    setCurrentPage('selector');
  };

  const handleSelectTruck = (truckId) => {
    setSelectedTruck(truckId);
    setCurrentPage('dashboard');
  };

  const handleBack = () => {
    if (currentPage === 'dashboard') {
      setCurrentPage('selector');
    } else if (currentPage === 'selector') {
      setCurrentPage('intro');
    }
  };

  return (
    <div className="App">
      {currentPage === 'intro' && <Intro onGetStarted={handleGetStarted} />}
      {currentPage === 'selector' && (
        <TruckSelector onSelectTruck={handleSelectTruck} onBack={handleBack} />
      )}
      {currentPage === 'dashboard' && selectedTruck && (
        <Dashboard truckId={selectedTruck} onBack={handleBack} />
      )}
    </div>
  );
}

export default App;
