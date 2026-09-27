import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import ThemeToggle from '../../components/ThemeToggle';
import '../../Dashboard.css';
import { UserIcon, LogOutIcon } from '../Icons';

const DashboardLayout = ({
    roleLabel,
    navItems,
    currentPage,
    onNavigate,
    onLogout,
    onProfileClick,
    children,
    profileImage,
    sidebarSubLabel,
}) => {
    const { user } = useAuth();
    const [profileOpen, setProfileOpen] = useState(false);
    const [openMenus, setOpenMenus] = useState({});

    const userInfo = user || { username: 'User' };
    const displaySubLabel = sidebarSubLabel || userInfo.registration_number;

    const getInitials = (name) => {
        if (!name) return 'U';
        const parts = name.trim().split(/\s+/);
        if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        return name.slice(0, 2).toUpperCase();
    };
    const initials = getInitials(userInfo.username);

    const toggleMenu = (key) => {
        setOpenMenus(prev => ({ ...prev, [key]: !prev[key] }));
    };

    useEffect(() => {
        const autoOpen = {};
        navItems.forEach((item) => {
            if (item.children?.some((child) => child.id === currentPage)) {
                autoOpen[item.id] = true;
            }
        });
        if (Object.keys(autoOpen).length) {
            setOpenMenus((prev) => ({ ...prev, ...autoOpen }));
        }
    }, [currentPage, navItems]);

    const isActive = (item) => {
        if (item.id === currentPage) return true;
        if (item.children?.some(c => c.id === currentPage)) return true;
        return false;
    };

    return (
        <div className="dashboard-layout fade-in">
            <aside className="dashboard-sidebar">
                <div className="sidebar-user-card compact-card">
                    <div className="sidebar-avatar-compact avatar-initials" title={userInfo.username}>
                        {initials}
                    </div>
                    <div className="sidebar-user-info">
                        <div className="sidebar-user-id-compact">{userInfo.username}</div>
                        {displaySubLabel && (
                            <div className="sidebar-user-role-compact" style={{ fontSize: '0.75rem', opacity: 0.85 }}>
                                Reg No: {displaySubLabel}
                            </div>
                        )}
                        <div className="sidebar-user-role-compact">{roleLabel}</div>
                    </div>
                </div>

                <nav className="sidebar-nav">
                    {navItems.map((item) => (
                        <React.Fragment key={item.id}>
                            {item.children ? (
                                <>
                                    <a
                                        className={`sidebar-link dropdown-link ${isActive(item) ? 'active' : ''}`}
                                        onClick={() => toggleMenu(item.id)}
                                        style={{ cursor: 'pointer' }}
                                    >
                                        <span className="sidebar-link-icon">{item.icon}</span>
                                        <span className="sidebar-text-clamp">{item.label}</span>
                                        <span className={`sidebar-link-arrow ${openMenus[item.id] ? 'open' : ''}`}>
                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <polyline points="6 9 12 15 18 9"></polyline>
                                            </svg>
                                        </span>
                                    </a>
                                    {openMenus[item.id] && (
                                        <div className="sidebar-submenu">
                                            {item.children.map((child) => (
                                                <a
                                                    key={child.id}
                                                    className={`sidebar-sublink ${currentPage === child.id ? 'active' : ''}`}
                                                    onClick={() => onNavigate(child.id)}
                                                    style={{ cursor: 'pointer' }}
                                                >
                                                    {child.label}
                                                </a>
                                            ))}
                                        </div>
                                    )}
                                </>
                            ) : (
                                <a
                                    className={`sidebar-link ${currentPage === item.id ? 'active' : ''}`}
                                    onClick={() => onNavigate(item.id)}
                                    style={{ cursor: 'pointer' }}
                                >
                                    <span className="sidebar-link-icon">{item.icon}</span>
                                    {item.label}
                                </a>
                            )}
                        </React.Fragment>
                    ))}
                </nav>
            </aside>

            <main className="dashboard-main">
                <header className="dashboard-header">
                    <div className="header-left" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div className="header-logo-icon" style={{ display: 'flex', alignItems: 'center' }}>
                            <img src="/campus360-logo.png" alt="Campus 360" style={{ height: '36px', objectFit: 'contain', borderRadius: '5px' }} />
                        </div>
                        <div className="header-logo-text">
                            Campus 360
                        </div>
                    </div>
                    <div className="header-right" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <ThemeToggle showLabel />
                        <div className="header-profile" onClick={() => setProfileOpen(!profileOpen)}>
                            <div className="header-avatar avatar-initials" title={userInfo.username}>
                                {initials}
                            </div>
                            <div className={`dropdown-menu ${profileOpen ? 'show' : ''}`}>
                                <a href="#" className="dropdown-item" onClick={(e) => {
                                    e.preventDefault();
                                    setProfileOpen(false);
                                    if (onProfileClick) onProfileClick();
                                }}>
                                    <UserIcon /> Profile
                                </a>
                                <div className="dropdown-divider"></div>
                                <a href="#" onClick={onLogout} className="dropdown-item text-danger">
                                    <LogOutIcon /> Logout
                                </a>
                            </div>
                        </div>
                    </div>
                </header>

                <div className="dashboard-content-wrapper">
                    {children}
                </div>

                <footer className="dashboard-footer">
                    <div>2026 &copy; Campus 360. All rights reserved.</div>
                    <div>Developed by Campus 360 Group</div>
                </footer>
            </main>
        </div>
    );
};

export default DashboardLayout;
