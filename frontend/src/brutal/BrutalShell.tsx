import React, { useEffect, useRef } from 'react';

type BrutalShellProps = {
  children: React.ReactNode;
};

export const BrutalShell: React.FC<BrutalShellProps> = ({ children }) => {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const cursorRef = useRef<HTMLDivElement | null>(null);
  const matrixRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const root = rootRef.current;
    const cursor = cursorRef.current;
    if (!root || !cursor) return;
    const rootEl = root;

    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

    let mouseX = 0;
    let mouseY = 0;
    let cursorX = 0;
    let cursorY = 0;

    const lerp = (start: number, end: number, factor: number) => start + (end - start) * factor;
    const clamp = (num: number, min: number, max: number) => Math.min(Math.max(num, min), max);

    const onMouseMove = (e: MouseEvent) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    };
    window.addEventListener('mousemove', onMouseMove, { passive: true });

    let cursorRaf = 0;
    const animateCursor = () => {
      if (!reduceMotion) {
        cursorX = lerp(cursorX, mouseX, 0.45);
        cursorY = lerp(cursorY, mouseY, 0.45);
      } else {
        cursorX = mouseX;
        cursorY = mouseY;
      }

      cursor.style.transform = `translate(${cursorX}px, ${cursorY}px) translate(-50%, -50%)`;
      cursorRaf = window.requestAnimationFrame(animateCursor);
    };
    cursorRaf = window.requestAnimationFrame(animateCursor);

    let lastMagnetic: HTMLElement | null = null;
    const onMagneticMove = (e: PointerEvent) => {
      const target = e.target instanceof Element ? (e.target as Element) : null;
      const el = target?.closest?.('.magnetic') as HTMLElement | null;

      if (lastMagnetic && lastMagnetic !== el) {
        lastMagnetic.style.transform = '';
        cursor.classList.remove('magnet');
        lastMagnetic = null;
      }

      if (!el) return;
      const tag = el.tagName;
      if (tag === 'FORM' || tag === 'INPUT' || tag === 'LABEL' || tag === 'TEXTAREA' || el.classList.contains('auth-box')) {
        cursor.classList.remove('magnet');
        return;
      }

      const rect = el.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const dist = 0.22;

      const moveX = (e.clientX - centerX) * dist;
      const moveY = (e.clientY - centerY) * dist;

      el.style.transform = `translate(${moveX}px, ${moveY}px)`;
      cursor.classList.add('magnet');
      lastMagnetic = el;
    };

    const onMagneticLeaveWindow = () => {
      if (lastMagnetic) lastMagnetic.style.transform = '';
      cursor.classList.remove('magnet');
      lastMagnetic = null;
    };

    document.addEventListener('pointermove', onMagneticMove, { passive: true });
    window.addEventListener('blur', onMagneticLeaveWindow);

    const alpha = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    const intervals = new WeakMap<HTMLElement, number>();

    const startHacker = (el: HTMLElement) => {
      const original = el.dataset.text ?? el.textContent ?? '';
      if (!original) return;

      const existing = intervals.get(el);
      if (existing) window.clearInterval(existing);

      let iter = 0;
      const id = window.setInterval(() => {
        const next = original
          .split('')
          .map((ch, i) => {
            if (i < iter) return original[i] ?? ch;
            return alpha[Math.floor(Math.random() * 26)] ?? ch;
          })
          .join('');
        el.textContent = next;
        if (iter >= original.length) window.clearInterval(id);
        iter += 1;
      }, 20);

      intervals.set(el, id);
    };

    const stopHacker = (el: HTMLElement) => {
      const existing = intervals.get(el);
      if (existing) window.clearInterval(existing);
      const original = el.dataset.text ?? '';
      if (original) el.textContent = original;
    };

    const onPointerOver = (e: PointerEvent) => {
      const target = e.target instanceof Element ? (e.target as Element) : null;
      const el = target?.closest?.('[data-text]') as HTMLElement | null;
      if (!el) return;
      startHacker(el);
    };

    const onPointerOut = (e: PointerEvent) => {
      const target = e.target instanceof Element ? (e.target as Element) : null;
      const el = target?.closest?.('[data-text]') as HTMLElement | null;
      if (!el) return;
      stopHacker(el);
    };

    root.addEventListener('pointerover', onPointerOver, { passive: true });
    root.addEventListener('pointerout', onPointerOut, { passive: true });

    let isNavScrolled = false;
    const setNavScrolled = (value: boolean) => {
      if (isNavScrolled === value) return;
      isNavScrolled = value;
      const navs = Array.from(document.querySelectorAll<HTMLElement>('.brutal-nav'));
      for (const nav of navs) {
        if (value) nav.classList.add('scrolled');
        else {
          nav.classList.remove('scrolled');
          nav.style.transform = '';
        }
      }
    };

    const onNavTiltMove = (e: MouseEvent) => {
      if (!isNavScrolled) return;
      const navs = Array.from(document.querySelectorAll<HTMLElement>('.brutal-nav.scrolled'));
      if (navs.length === 0) return;

      const cx = window.innerWidth / 2;
      const cy = 100;
      const rx = (e.clientY - cy) * 0.02;
      const ry = (e.clientX - cx) * 0.02;
      const next = `translateX(-50%) perspective(1000px) rotateX(${-clamp(rx, -10, 10)}deg) rotateY(${clamp(ry, -10, 10)}deg)`;
      for (const nav of navs) nav.style.transform = next;
    };
    document.addEventListener('mousemove', onNavTiltMove, { passive: true });

    let lastScrollTop = window.scrollY;
    let skew = 0;
    let scrollRaf = 0;
    let scrollEl: HTMLElement | null = null;
    let lastScrollActivity = performance.now();
    function scrollLoop() {
      scrollRaf = 0;
      if (!reduceMotion) {
        if (scrollEl && !rootEl.contains(scrollEl)) scrollEl = null;
        if (!scrollEl) scrollEl = rootEl.querySelector<HTMLElement>('.brutal-scroll');

        const disableSkew = window.location.pathname === '/';
        if (disableSkew) {
          skew = 0;
          lastScrollTop = window.scrollY;
          if (scrollEl) scrollEl.style.transform = 'skewY(0deg)';
          return;
        }

        const scrollTop = window.scrollY;
        const velocity = scrollTop - lastScrollTop;
        lastScrollTop = scrollTop;

        const maxSkew = 5.0;
        const speed = clamp(velocity * 0.1, -maxSkew, maxSkew);
        skew = lerp(skew, speed, 0.1);

        if (scrollEl) {
          scrollEl.style.transform = Math.abs(skew) > 0.01 ? `skewY(${skew}deg)` : 'skewY(0deg)';
        }

        if (Math.abs(velocity) > 0.5 || Math.abs(skew) > 0.05) {
          lastScrollActivity = performance.now();
        }

        const shouldStop = Math.abs(skew) < 0.02 && performance.now() - lastScrollActivity > 140;
        if (shouldStop) {
          skew = 0;
          if (scrollEl) scrollEl.style.transform = 'skewY(0deg)';
          return;
        }
      }
      scrollRaf = window.requestAnimationFrame(scrollLoop);
    }
    function ensureScrollLoop() {
      lastScrollActivity = performance.now();
      if (scrollRaf) return;
      scrollRaf = window.requestAnimationFrame(scrollLoop);
    }

    const onScroll = () => {
      setNavScrolled(window.scrollY > 100);
      ensureScrollLoop();
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('pointermove', onMagneticMove);
      window.removeEventListener('blur', onMagneticLeaveWindow);
      root.removeEventListener('pointerover', onPointerOver);
      root.removeEventListener('pointerout', onPointerOut);
      window.removeEventListener('scroll', onScroll);
      document.removeEventListener('mousemove', onNavTiltMove);
      window.cancelAnimationFrame(cursorRaf);
      window.cancelAnimationFrame(scrollRaf);

      if (lastMagnetic) lastMagnetic.style.transform = '';
      cursor.classList.remove('magnet');
      if (scrollEl) scrollEl.style.transform = '';

      const navs = Array.from(document.querySelectorAll<HTMLElement>('.brutal-nav'));
      for (const nav of navs) nav.style.transform = '';
    };
  }, []);

  useEffect(() => {
    const canvas = matrixRef.current;
    if (!canvas) return;

    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    if (reduceMotion) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    const dpr = Math.min(1.1, Math.max(1, window.devicePixelRatio || 1));
    const density = 0.52;

    let columns = 0;
    let drops: number[] = [];
    let speeds: number[] = [];
    let enabledCols: boolean[] = [];
    let raf = 0;
    let width = 0;
    let height = 0;
    let fontSize = 16;
    let lastTs = 0;
    let lastDraw = 0;

    const resize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      fontSize = width < 480 ? 13 : width < 900 ? 15 : 16;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      columns = Math.ceil(width / fontSize);
      drops = new Array(columns).fill(0).map(() => Math.floor(Math.random() * -80));
      speeds = new Array(columns).fill(0).map(() => 0.12 + Math.random() * 0.22);
      enabledCols = new Array(columns).fill(false).map(() => Math.random() < density);
      ctx.font = `${fontSize}px Space Grotesk, system-ui, sans-serif`;
      ctx.textBaseline = 'top';
    };

    const frame = (ts: number) => {
      if (ts - lastDraw < 33) {
        raf = window.requestAnimationFrame(frame);
        return;
      }
      lastDraw = ts;
      const dt = lastTs > 0 ? Math.min(40, ts - lastTs) : 16.67;
      lastTs = ts;
      const step = dt / 16.67;

      ctx.fillStyle = 'rgb(3, 3, 3)';
      ctx.fillRect(0, 0, width, height);

      ctx.fillStyle = 'rgba(168, 217, 0, 0.5)';

      for (let i = 0; i < columns; i += 1) {
        if (!enabledCols[i]) continue;
        const x = i * fontSize;
        const y = drops[i] * fontSize;
        const ch = chars[Math.floor(Math.random() * chars.length)] ?? 'A';
        ctx.fillText(ch, x, y);
        drops[i] += speeds[i] * step;

        if (y > height + fontSize * 2) {
          drops[i] = Math.floor(Math.random() * -60);
          speeds[i] = 0.12 + Math.random() * 0.22;
          enabledCols[i] = Math.random() < density;
        }
      }

      raf = window.requestAnimationFrame(frame);
    };

    const onVisibilityChange = () => {
      if (document.hidden) return;
      lastTs = 0;
      window.cancelAnimationFrame(raf);
      raf = window.requestAnimationFrame(frame);
    };

    resize();
    window.addEventListener('resize', resize, { passive: true });
    document.addEventListener('visibilitychange', onVisibilityChange);
    raf = window.requestAnimationFrame(frame);

    return () => {
      window.cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, []);

  return (
    <div className="brutal-shell" ref={rootRef}>
      <div className="noise" />
      <div className="neural-bg" />
      <canvas className="matrix-rain" ref={matrixRef} />
      <div id="cursor" ref={cursorRef} />
      {children}
    </div>
  );
};
