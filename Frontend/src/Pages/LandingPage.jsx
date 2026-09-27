import React from 'react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import Hero from '../components/Hero';
import AboutSection from '../components/AboutSection';
import Features from '../components/Features';
import Testimonials from '../components/Testimonials';

export default function LandingPage() {
    return (
        <div id="top">
            <Navbar />
            <Hero />
            <AboutSection />
            <Features />
            <Testimonials />
            <Footer />
        </div>
    );
}
