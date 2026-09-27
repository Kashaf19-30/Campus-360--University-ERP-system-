// src/components/Hero.jsx
import React, { useState, useEffect } from 'react';

const Hero = () => {
    const headings = [
        "Empowering Minds, Shaping Futures",
        "Learn Today, Lead Tomorrow",
        "Knowledge That Builds Your Future",
        "Where Education Meets Excellence"
    ];
    const [index, setIndex] = useState(0);

    useEffect(() => {
        const interval = setInterval(() => {
            setIndex((prev) => (prev + 1) % headings.length);
        }, 4000);
        return () => clearInterval(interval);
    }, []);

    return (
        <section id="home" className="hero">
            <div className="hero-content">
                <div className="hero-slider">
                    <h1 key={index} className="fade-in">{headings[index]}</h1>
                </div>
                <p className="fade-in">Experience the future of education at the University of Sialkot. We provide a platform for innovation, research, and academic excellence.</p>
                <div className="fade-in" style={{ display: 'flex', gap: '20px', justifyContent: 'center' }}>
                    {/* Buttons removed as per request */}
                </div>
            </div>
        </section>
    );
};

export default Hero;