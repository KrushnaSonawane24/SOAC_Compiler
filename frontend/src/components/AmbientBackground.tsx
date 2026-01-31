import React from 'react';

export const AmbientBackground: React.FC = () => {
    return (
        <div className="soac-ambient" aria-hidden="true">
            <div className="soac-stars" />
            <div className="soac-blob soac-blob--indigo" />
            <div className="soac-blob soac-blob--cyan" />
            <div className="soac-blob soac-blob--green" />
            <div className="soac-vignette" />
        </div>
    );
};
