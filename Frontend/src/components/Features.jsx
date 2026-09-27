// src/components/Features.jsx
import React from 'react';

const Features = () => {
    const commitments = [
        { 
            title: "Personality Development", 
            img: "/personality.png",
            desc: "Focusing on holistic growth through professional mentorship, soft skills training, and leadership workshops.",
            icon: (
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                </svg>
            )
        },
        { 
            title: "Quality Education", 
            img: "/education.png",
            desc: "Providing globally accredited academic programs designed to meet the demands of the modern industry.",
            icon: (
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 10v6M2 10l10-5 10 5-10 5z"></path>
                    <path d="M6 12v5c3 3 9 3 12 0v-5"></path>
                </svg>
            )
        },
        { 
            title: "Modern Labs", 
            img: "/labs.png",
            desc: "State-of-the-art computer and research labs equipped with the latest technology for practical learning.",
            icon: (
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                    <line x1="8" y1 = "21" x2="16" y2="21"></line>
                    <line x1="12" y1="17" x2="12" y2="21"></line>
                </svg>
            )
        },
        { 
            title: "Student Societies", 
            img: "../hero background.webp", 
            desc: "A vibrant campus life with diverse societies and clubs that encourage creativity, teamwork, and social impact.",
            icon: (
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17 21v-2a4 4 0 0 0-3-3.87"></path>
                    <path d="M7 21v-2a4 4 0 0 1 3-3.87"></path>
                    <path d="M9 3.51a9 9 0 0 1 6 0"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                </svg>
            )
        }
    ];

    return (
        <section id="features" className="section" style={{ background: 'var(--light-gray)' }}>
            <div className="container">
                <div className="text-center mb-5 fade-in">
                    <h2 style={{ fontSize: '2.5rem', marginBottom: '15px' }}>Core <span className="accent-text">Commitments</span></h2>
                    <p style={{ maxWidth: '600px', margin: '0 auto', color: 'var(--dark-gray)' }}>Fostering an environment of excellence, innovation, and holistic development for the leaders of tomorrow.</p>
                </div>
                <div className="features-grid">
                    {commitments.map((c, i) => (
                        <div key={i} className="commitment-card fade-in" style={{ animationDelay: `${i * 0.1}s` }}>
                            <div className="commitment-image">
                                <img src={c.img} alt={c.title} />
                            </div>
                            <div className="commitment-info">
                                <div className="commitment-icon-wrapper">
                                    {c.icon}
                                </div>
                                <h3>{c.title}</h3>
                                <p>{c.desc}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default Features;