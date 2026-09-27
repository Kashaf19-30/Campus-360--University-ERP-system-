import React, { createContext, useContext, useEffect, useState } from 'react';

const ThemeContext = createContext(null);

export const ThemeProvider = ({ children }) => {
    const [isNightMode, setIsNightMode] = useState(() => {
        const stored = localStorage.getItem('campus360_night_mode');
        const night = stored === 'true';
        document.documentElement.setAttribute('data-theme', night ? 'dark' : 'light');
        return night;
    });

    useEffect(() => {
        document.documentElement.setAttribute('data-theme', isNightMode ? 'dark' : 'light');
        localStorage.setItem('campus360_night_mode', isNightMode ? 'true' : 'false');
    }, [isNightMode]);

    const toggleTheme = () => setIsNightMode(prev => !prev);

    return (
        <ThemeContext.Provider value={{ isNightMode, toggleTheme }}>
            {children}
        </ThemeContext.Provider>
    );
};

export const useTheme = () => {
    const ctx = useContext(ThemeContext);
    if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
    return ctx;
};

export default ThemeContext;
