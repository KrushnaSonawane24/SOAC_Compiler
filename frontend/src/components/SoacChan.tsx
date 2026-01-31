import React, { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { useMascot } from '../mascot/MascotContext';

function useDefaultMessage(mode: string): string | undefined {
    return useMemo(() => {
        if (mode === 'thinking') return 'optimizing… please wait';
        if (mode === 'benchmarking') return 'benchmarking… collecting stable numbers';
        if (mode === 'success') return 'done. artifacts should be ready now';
        if (mode === 'failure') return 'something failed. check logs for the exact stage';
        return undefined;
    }, [mode]);
}

export const SoacChan: React.FC = () => {
    const { pathname } = useLocation();
    const { state, muted, toggleMuted } = useMascot();
    const defaultMessage = useDefaultMessage(state.mode);

    if (pathname.startsWith('/login') || pathname.startsWith('/register')) return null;

    const message = state.message ?? defaultMessage;

    return (
        <div className="soac-chan-root hidden sm:block">
            {!muted && message ? (
                <div className="soac-chan-bubble">
                    <div className="soac-chan-bubble-text">{message}</div>
                    <button type="button" className="soac-chan-mute" onClick={toggleMuted} title="Mute tips">
                        mute
                    </button>
                </div>
            ) : (
                <button type="button" className="soac-chan-unmute" onClick={toggleMuted} title="Unmute tips">
                    tips
                </button>
            )}

            <div className={`soac-chan ${state.mode}`}>
                <div className="soac-chan-face">
                    <div className="soac-chan-eye" />
                    <div className="soac-chan-eye" />
                </div>
            </div>
        </div>
    );
};
