import { Link } from 'react-router-dom';
import './Navbar.css';

const Navbar = () => {
  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-logo">
          <div className="logo-icon">C</div>
          <span className="logo-text">ColdChain</span>
        </div>
        
        <div className="navbar-links">
          <Link to="/" className="nav-link">Home</Link>
          <Link to="/resources" className="nav-link">Resources</Link>
          <Link to="/pricing" className="nav-link">Pricing</Link>
        </div>
        
        <div className="navbar-actions">
          <Link to="/login" className="btn-login">Login</Link>
          <Link to="/signup" className="btn-signup">Open Account</Link>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
