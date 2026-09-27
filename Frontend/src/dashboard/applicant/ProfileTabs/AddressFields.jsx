// src/dashboard/applicant/ProfileTabs/AddressFields.jsx
import React, { useState, useEffect } from 'react';

// Country data with states and cities
const countryData = {
    pakistan: {
        label: 'Pakistan',
        states: {
            punjab: {
                label: 'Punjab',
                cities: ['Lahore', 'Sialkot', 'Gujranwala', 'Faisalabad', 'Rawalpindi', 'Multan', 'Islamabad']
            },
            sindh: {
                label: 'Sindh',
                cities: ['Karachi', 'Hyderabad', 'Sukkur', 'Larkana']
            },
            kpk: {
                label: 'Khyber Pakhtunkhwa',
                cities: ['Peshawar', 'Abbottabad', 'Mardan', 'Swat']
            },
            balochistan: {
                label: 'Balochistan',
                cities: ['Quetta', 'Gwadar', 'Turbat']
            },
            'islamabad-capital-territory': {
                label: 'Islamabad',
                cities: ['Islamabad']
            }
        }
    },
    uae: {
        label: 'United Arab Emirates',
        states: {
            'abu-dhabi': {
                label: 'Abu Dhabi',
                cities: ['Abu Dhabi', 'Al Ain']
            },
            dubai: {
                label: 'Dubai',
                cities: ['Dubai', 'Jumeirah', 'Deira']
            },
            sharjah: {
                label: 'Sharjah',
                cities: ['Sharjah', 'Khor Fakkan']
            },
            ajman: {
                label: 'Ajman',
                cities: ['Ajman']
            },
            'ras-al-khaimah': {
                label: 'Ras Al Khaimah',
                cities: ['Ras Al Khaimah']
            },
            fujairah: {
                label: 'Fujairah',
                cities: ['Fujairah']
            },
            'umm-al-quwain': {
                label: 'Umm Al Quwain',
                cities: ['Umm Al Quwain']
            }
        }
    },
    uk: {
        label: 'United Kingdom',
        states: {
            england: {
                label: 'England',
                cities: ['London', 'Manchester', 'Birmingham', 'Liverpool']
            },
            scotland: {
                label: 'Scotland',
                cities: ['Edinburgh', 'Glasgow']
            },
            wales: {
                label: 'Wales',
                cities: ['Cardiff', 'Swansea']
            },
            'northern-ireland': {
                label: 'Northern Ireland',
                cities: ['Belfast']
            }
        }
    },
    usa: {
        label: 'United States',
        states: {
            california: {
                label: 'California',
                cities: ['Los Angeles', 'San Francisco', 'San Diego']
            },
            texas: {
                label: 'Texas',
                cities: ['Houston', 'Dallas', 'Austin']
            },
            'new-york': {
                label: 'New York',
                cities: ['New York City', 'Buffalo', 'Albany']
            },
            florida: {
                label: 'Florida',
                cities: ['Miami', 'Orlando', 'Tampa']
            },
            illinois: {
                label: 'Illinois',
                cities: ['Chicago']
            }
        }
    },
    canada: {
        label: 'Canada',
        states: {
            ontario: {
                label: 'Ontario',
                cities: ['Toronto', 'Ottawa', 'Mississauga']
            },
            'british-columbia': {
                label: 'British Columbia',
                cities: ['Vancouver', 'Victoria']
            },
            quebec: {
                label: 'Quebec',
                cities: ['Montreal', 'Quebec City']
            },
            alberta: {
                label: 'Alberta',
                cities: ['Calgary', 'Edmonton']
            }
        }
    },
    australia: {
        label: 'Australia',
        states: {
            'new-south-wales': {
                label: 'New South Wales',
                cities: ['Sydney', 'Newcastle']
            },
            victoria: {
                label: 'Victoria',
                cities: ['Melbourne']
            },
            queensland: {
                label: 'Queensland',
                cities: ['Brisbane']
            },
            'western-australia': {
                label: 'Western Australia',
                cities: ['Perth']
            }
        }
    },
    other: {
        label: 'Other',
        states: {
            other: {
                label: 'Other',
                cities: ['Other']
            }
        }
    }
};

// Get display label for country
const getCountryLabel = (countryKey) => {
    return countryData[countryKey]?.label || countryKey;
};

// Get display label for state
const getStateLabel = (countryKey, stateKey) => {
    return countryData[countryKey]?.states[stateKey]?.label || stateKey;
};

const AddressFields = ({ 
    prefix = '', 
    data = {}, 
    onChange, 
    onBlur, 
    errors = {}, 
    touched = {},
    showLabels = true 
}) => {
    const [availableStates, setAvailableStates] = useState([]);
    const [availableCities, setAvailableCities] = useState([]);
    const [localTouched, setLocalTouched] = useState({});
    
    const selectedCountry = data[prefix + 'country'] || '';
    const selectedState = data[prefix + 'state'] || '';
    const selectedCity = data[prefix + 'city'] || '';
    const address = data[prefix + 'address'] || '';

    const mergedTouched = { ...localTouched, ...touched };

    // Update available states when country changes
    useEffect(() => {
        if (selectedCountry && countryData[selectedCountry]) {
            const states = Object.keys(countryData[selectedCountry].states);
            setAvailableStates(states);
            
            // If current state is not in available states, clear it
            if (!states.includes(selectedState)) {
                onChange(prefix + 'state', '');
                onChange(prefix + 'city', '');
                setAvailableCities([]);
            } else {
                const cities = countryData[selectedCountry].states[selectedState]?.cities || [];
                setAvailableCities(cities);
                if (!cities.includes(selectedCity)) {
                    onChange(prefix + 'city', '');
                }
            }
        } else {
            setAvailableStates([]);
            setAvailableCities([]);
        }
    }, [selectedCountry]);

    // Update available cities when state changes
    useEffect(() => {
        if (selectedCountry && selectedState && countryData[selectedCountry]) {
            const cities = countryData[selectedCountry].states[selectedState]?.cities || [];
            setAvailableCities(cities);
            if (!cities.includes(selectedCity)) {
                onChange(prefix + 'city', '');
            }
        } else {
            setAvailableCities([]);
        }
    }, [selectedState]);

    const handleFieldChange = (field, value) => {
        onChange(field, value);
        // Mark as touched on change
        setLocalTouched(prev => ({ ...prev, [field]: true }));
    };

    const handleFieldBlur = (field) => {
        setLocalTouched(prev => ({ ...prev, [field]: true }));
        if (onBlur) onBlur(field);
    };

    const getFieldError = (field) => {
        return mergedTouched[field] && errors[field] ? errors[field] : '';
    };

    const getFieldStatus = (field) => {
        if (!mergedTouched[field]) return null;
        if (errors[field]) return 'error';
        if (data[field]) return 'success';
        return null;
    };

    const getInputClass = (field) => {
        const status = getFieldStatus(field);
        if (status === 'error') return 'field-input error';
        if (status === 'success') return 'field-input success';
        return 'field-input';
    };

    const getSelectClass = (field) => {
        const status = getFieldStatus(field);
        if (status === 'error') return 'field-input field-select error';
        if (status === 'success') return 'field-input field-select success';
        return 'field-input field-select';
    };

    return (
        <>
            <div className="address-fields-container">
                {/* Country Selection */}
                <div className="field-group">
                    <label className="field-label">
                        Country <span className="required">*</span>
                    </label>
                    <select 
                        data-field="country"
                        className={getSelectClass(prefix + 'country')}
                        value={selectedCountry}
                        onChange={(e) => handleFieldChange(prefix + 'country', e.target.value)}
                        onBlur={() => handleFieldBlur(prefix + 'country')}
                    >
                        <option value="">Select Country</option>
                        {Object.keys(countryData).map(countryKey => (
                            <option key={countryKey} value={countryKey}>
                                {getCountryLabel(countryKey)}
                            </option>
                        ))}
                    </select>
                    {getFieldError(prefix + 'country') && (
                        <div className="error-message">{getFieldError(prefix + 'country')}</div>
                    )}
                </div>

                {/* State/Province Selection */}
                <div className="field-group">
                    <label className="field-label">
                        State / Province <span className="required">*</span>
                    </label>
                    <select 
                        data-field="state"
                        className={getSelectClass(prefix + 'state')}
                        value={selectedState}
                        onChange={(e) => handleFieldChange(prefix + 'state', e.target.value)}
                        onBlur={() => handleFieldBlur(prefix + 'state')}
                        disabled={!selectedCountry}
                    >
                        <option value="">Select State</option>
                        {availableStates.map(stateKey => (
                            <option key={stateKey} value={stateKey}>
                                {getStateLabel(selectedCountry, stateKey)}
                            </option>
                        ))}
                    </select>
                    {getFieldError(prefix + 'state') && (
                        <div className="error-message">{getFieldError(prefix + 'state')}</div>
                    )}
                    {selectedCountry && !selectedState && mergedTouched[prefix + 'state'] && (
                        <div className="helper-text">Please select a state/province</div>
                    )}
                </div>

                {/* City Selection */}
                <div className="field-group">
                    <label className="field-label">
                        City <span className="required">*</span>
                    </label>
                    <select 
                        data-field="city"
                        className={getSelectClass(prefix + 'city')}
                        value={selectedCity}
                        onChange={(e) => handleFieldChange(prefix + 'city', e.target.value)}
                        onBlur={() => handleFieldBlur(prefix + 'city')}
                        disabled={!selectedState}
                    >
                        <option value="">Select City</option>
                        {availableCities.map(city => (
                            <option key={city} value={city}>
                                {city}
                            </option>
                        ))}
                    </select>
                    {getFieldError(prefix + 'city') && (
                        <div className="error-message">{getFieldError(prefix + 'city')}</div>
                    )}
                    {selectedState && !selectedCity && mergedTouched[prefix + 'city'] && (
                        <div className="helper-text">Please select a city</div>
                    )}
                </div>

                {/* Address Textarea */}
                <div className="field-group">
                    <label className="field-label">
                        Street Address <span className="required">*</span>
                    </label>
                    <textarea 
                        data-field="address"
                        className={`field-input field-textarea ${getFieldStatus(prefix + 'address') === 'error' ? 'error' : ''} ${getFieldStatus(prefix + 'address') === 'success' ? 'success' : ''}`}
                        placeholder="House No., Street Name, Area, Landmark (if any)" 
                        rows="3" 
                        value={address}
                        onChange={(e) => handleFieldChange(prefix + 'address', e.target.value)}
                        onBlur={() => handleFieldBlur(prefix + 'address')}
                    />
                    {getFieldError(prefix + 'address') && (
                        <div className="error-message">{getFieldError(prefix + 'address')}</div>
                    )}
                    {!getFieldError(prefix + 'address') && address && address.length >= 10 && (
                        <div className="success-hint">
                            <span>✓</span> Address looks complete
                        </div>
                    )}
                    {address && address.length < 10 && address.length > 0 && (
                        <div className="helper-text">Please provide a more detailed address (at least 10 characters)</div>
                    )}
                </div>
            </div>

            {/* Address Preview (optional) */}
            {selectedCountry && selectedState && selectedCity && address && (
                <div className="address-preview">
                    <div className="address-preview-header">
                        <span>📍</span>
                        <strong>Address Preview</strong>
                    </div>
                    <div className="address-preview-content">
                        {address}, {selectedCity}, {getStateLabel(selectedCountry, selectedState)}, {getCountryLabel(selectedCountry)}
                    </div>
                </div>
            )}
        </>
    );
};

export default AddressFields;