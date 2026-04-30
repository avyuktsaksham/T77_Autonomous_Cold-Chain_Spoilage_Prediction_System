import React from 'react';
import './Intro.css';

function Intro({ onGetStarted }) {
  return (
    <div className="intro-container">
      <div className="intro-content">
        <div className="intro-header">
          <h1 className="intro-title">Autonomous Cold-Chain Spoilage Prediction System</h1>
          <p className="intro-subtitle">
            Real-time monitoring and AI-powered risk assessment for pharmaceutical and food supply chains
          </p>
        </div>

        <div className="intro-features">
          <div className="feature-card">
            <div className="feature-icon">01</div>
            <h3>Live Monitoring</h3>
            <p>Real-time sensor data from 50+ active shipments</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">02</div>
            <h3>Risk Analysis</h3>
            <p>Intelligent risk scoring based on environmental conditions</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">03</div>
            <h3>AI Insights</h3>
            <p>GenAI-powered summaries and recommendations</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">04</div>
            <h3>Fleet Management</h3>
            <p>Track multiple trucks and their cargo conditions</p>
          </div>
        </div>

        <button className="cta-button" onClick={onGetStarted}>
          Get Started
        </button>

        <div className="intro-footer">
          <p>Monitor your cold chain, prevent spoilage, save lives.</p>
        </div>
      </div>
    </div>
  );
}

export default Intro;
