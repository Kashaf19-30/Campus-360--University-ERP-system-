import { useEffect } from 'react';
import { createPortal } from 'react-dom';

/**
 * Render modals on document.body so they cover the full viewport.
 * Use `render={() => ...}` when modal content reads from nullable state —
 * children are evaluated even when isOpen is false unless you use render.
 */
export default function ModalPortal({ isOpen, children, render }) {
    useEffect(() => {
        if (!isOpen) return undefined;
        const prev = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        return () => {
            document.body.style.overflow = prev;
        };
    }, [isOpen]);

    if (!isOpen) return null;
    return createPortal(render ? render() : children, document.body);
}
