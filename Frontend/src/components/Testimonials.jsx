// src/components/Testimonials.jsx
import React, { useState, useEffect } from 'react';

const Testimonials = () => {
    const reviews = [
        { name: "Ahmed Khan", role: "BSCS Student", text: "The faculty at USKT is incredibly supportive. The modern labs gave me the edge I needed for my career." },
        { name: "Sara Malik", role: "Alumni", text: "USKT transformed my personality. The student societies helped me build leadership skills that I use every day." },
        { name: "Dr. Usman Ali", role: "Professor", text: "A culture of creativity and innovation is what sets our university apart in the region." }
    ];
    const [active, setActive] = useState(0);

    useEffect(() => {
        const interval = setInterval(() => {
            setActive((prev) => (prev + 1) % reviews.length);
        }, 5000);
        return () => clearInterval(interval);
    }, []);

    return (
        <section className="testimonials-section">
            <div className="container">
                <h2 className="mb-5 fade-in" style={{ color: 'var(--white)', fontSize: '2.5rem' }}>Student <span className="accent-text">Voices</span></h2>
                <div className="testimonials-slider">
                    <div key={active} className="testimonial-card glass fade-in">
                        <div className="quote-icon">"</div>
                        <p className="testimonial-text">"{reviews[active].text}"</p>
                        <div className="testimonial-author">
                            <div className="author-info">
                                <h4>{reviews[active].name}</h4>
                                <p>{reviews[active].role}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default Testimonials;