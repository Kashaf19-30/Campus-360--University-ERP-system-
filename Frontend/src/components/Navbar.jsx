// src/components/Navbar.jsx
import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { dashboardPathForRole } from '../routes/paths';
import ThemeToggle from './ThemeToggle';

const Navbar = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { user } = useAuth();
    const isHistory = location.pathname === '/history';
    const [isScrolled, setIsScrolled] = useState(false);

    const dashboardPath = user?.user_type ? dashboardPathForRole(user.user_type) : null;

    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 50);
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    const goHome = () => {
        if (location.pathname === '/') {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
            navigate('/');
        }
    };

    const scrollToSection = (sectionId) => {
        if (location.pathname === '/') {
            document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth' });
        } else {
            navigate(`/#${sectionId}`);
        }
    };

    return (
        <nav className={`landing-nav${isScrolled ? ' scrolled' : ''}`}>
            <div className="container nav-container">
                <div className="logo" onClick={goHome} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <img src="../logo.png/logo.webp" alt="University of Sialkot Logo" style={{ height: '50px' }} />
                    <span className={`logo-text ${isHistory ? 'gold' : ''}`}>University of <span className="accent-text">Sialkot</span></span>
                </div>
                <ul className="nav-links">
                    <li><a href="#top" onClick={(e) => { e.preventDefault(); goHome(); }}>Home</a></li>
                    <li className="dropdown">
                        <a href="#about" onClick={(e) => { e.preventDefault(); scrollToSection('about'); }}>About <span className="arrow">▼</span></a>
                        <ul className="dropdown-menu">
                            <li><Link to="/history">History</Link></li>
                            <li><a href="#about" onClick={(e) => { e.preventDefault(); scrollToSection('about'); }}>Our University</a></li>
                        </ul>
                    </li>
                    <li className="dropdown">
                        <a href="#admission" onClick={(e) => { e.preventDefault(); scrollToSection('features'); }}>Admission <span className="arrow">▼</span></a>
                        <ul className="dropdown-menu">
                            <li><a href="#features" onClick={(e) => { e.preventDefault(); scrollToSection('features'); }}>Admission Process</a></li>
                        </ul>
                    </li>
                    <li><a href="#contact" onClick={(e) => { e.preventDefault(); scrollToSection('footer'); }}>Contact</a></li>
                </ul>
                <div className="auth-buttons">
                    <ThemeToggle showLabel />
                    {dashboardPath ? (
                        <button className="btn btn-apply" onClick={() => navigate(dashboardPath)}>
                            Go to Dashboard
                        </button>
                    ) : (
                        <button className="btn btn-apply" onClick={() => navigate('/signup')}>Apply Online</button>
                    )}
                </div>
            </div>
        </nav>
    );
};

export default Navbar;
