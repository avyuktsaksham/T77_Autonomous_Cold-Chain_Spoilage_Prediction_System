import { useNavigate } from 'react-router-dom';
import './Hero.css';

const Hero = () => {
  const navigate = useNavigate();

  return (
    <section className="hero">
      <div className="hero-container">
        <h1 className="hero-title">
          Elevate Your <span className="italic-text">Cold Chain</span>
          <br />
          <span className="italic-text">Management</span> with AI Prediction
        </h1>
        
        <p className="hero-subtitle">
          Streamline, Optimize, and Scale Your Cold Chain Management with Our Powerful AI
          Solution. Predict Spoilage, Optimize Storage, and Scale Your Operations.
        </p>
        
        <button className="hero-cta" onClick={() => navigate('/rooms')}>
          Look
        </button>
      </div>
    </section>
  );
};

export default Hero;
