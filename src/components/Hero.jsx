import './Hero.css';

const Hero = () => {
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
        
        <button className="hero-cta">
          Start Free Prediction
        </button>
      </div>
    </section>
  );
};

export default Hero;
