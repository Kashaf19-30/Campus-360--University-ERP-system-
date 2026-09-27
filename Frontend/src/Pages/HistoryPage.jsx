// src/pages/HistoryPage.jsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const HistoryPage = () => {
    const navigate = useNavigate();

    return (
        <div style={{ background: 'var(--white)', minHeight: '100vh', paddingTop: '100px' }}>
            <Navbar />
            <section className="section">
                <div className="container" style={{ maxWidth: '900px' }}>
                    <div className="fade-in">
                        <h1 className="mb-5" style={{ color: 'var(--primary-navy)', fontSize: '3rem' }}>University <span className="accent-text">History</span></h1>
                        <div style={{ textAlign: 'left', lineHeight: '1.8', fontSize: '1.1rem' }}>
                            <h3 className="mb-3" style={{ color: 'var(--primary-navy)', fontSize: '1.8rem' }}>A Remarkable Beginning: Establishment as a Sub-Campus</h3>
                            <p className="mb-4">
                                The University of Sialkot (USKT) traces its origins to 2013, when it was established as a sub-campus of the University of Gujrat under the Public-Private Partnership (PPP) model. This initiative laid the groundwork for creating a transformative academic institution committed to fostering intellectual and professional growth at a wider scale.
                            </p>
                            
                            <h3 className="mb-3" style={{ color: 'var(--primary-navy)', fontSize: '1.8rem' }}>The University of Sialkot Act (IX) 2018: A New Era of Independence</h3>
                            <p className="mb-3">
                                In 2018, a significant milestone was achieved when the sub-campus transitioned into a full-fledged private university under the University of Sialkot Act (IX) of 2018. This transition marked the emergence of USKT as a leading academic institution, offering diverse academic disciplines and advancing opportunities in higher education.
                            </p>
                            <p className="mb-5">
                                The university's evolution is intricately tied to Sialkot's cultural and industrial significance. Known for its innovation, creativity, and as the birthplace of the great poet-philosopher Muhammad Iqbal, Sialkot provided a fertile environment for USKT to flourish. The university's development complements the city's dynamic character, serving as an educational beacon for students and professionals from across the country and beyond.
                            </p>
                            
                            <button onClick={() => navigate('/')} className="btn btn-primary">Back to Home</button>
                        </div>
                    </div>
                </div>
            </section>
            <Footer />
        </div>
    );
};

export default HistoryPage;