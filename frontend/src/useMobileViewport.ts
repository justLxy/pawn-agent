import { useEffect, useState } from 'react';

/** Tracks soft-keyboard inset via Visual Viewport API (mobile browsers). */
export function useMobileViewport() {
  const [keyboardInset, setKeyboardInset] = useState(0);

  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;

    const sync = () => {
      const inset = Math.max(0, window.innerHeight - vv.height - vv.offsetTop);
      setKeyboardInset(inset);
      document.documentElement.style.setProperty('--keyboard-inset', `${inset}px`);
    };

    sync();
    vv.addEventListener('resize', sync);
    vv.addEventListener('scroll', sync);
    return () => {
      vv.removeEventListener('resize', sync);
      vv.removeEventListener('scroll', sync);
      document.documentElement.style.removeProperty('--keyboard-inset');
    };
  }, []);

  const keyboardOpen = keyboardInset > 80;

  return { keyboardInset, keyboardOpen };
}
