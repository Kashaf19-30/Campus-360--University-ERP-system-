// src/components/AboutSection.jsx
import React from 'react';

const AboutSection = () => {
    return (
        <section id="about" className="section bg-white">
            <div className="container about-grid">
                <div className="about-content fade-in">
                    <span className="about-tag">Since 2018</span>
                    <h2>Our <span className="accent-text">University</span></h2>
                    <h4 className="mb-4" style={{ color: 'var(--primary-navy-light)' }}>With Academic Excellence And State Of The Art Facilities</h4>
                    <p style={{ color: 'var(--dark-gray)', fontSize: '1.1rem', marginBottom: '20px' }}>
                        Explore the University of Sialkot's state-of-the-art facilities, diverse academic programs, and vibrant campus life. 
                        Engaging with a dynamic community dedicated to fostering innovation and excellence. 
                        Experience a supportive environment that encourages personal and professional growth.
                    </p>
                    <ul style={{ listStyle: 'none', padding: 0 }}>
                        <li style={{ marginBottom: '10px' }}><strong className="accent-text">✓</strong> Quality Education with Global Standards</li>
                        <li style={{ marginBottom: '10px' }}><strong className="accent-text">✓</strong> Modern Research & Computer Labs</li>
                        <li style={{ marginBottom: '10px' }}><strong className="accent-text">✓</strong> Dynamic Student Societies</li>
                    </ul>
                </div>
                <div className="about-image fade-in" style={{ animationDelay: '0.3s' }}>
                    <img src="../hero background.webp" alt="University Life" />
                </div>
            </div>
        </section>
    );
};

export default AboutSection;