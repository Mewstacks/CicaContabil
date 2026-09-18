(() => {
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  if (!('IntersectionObserver' in window) || preference.matches) return;
  const animations = new Set();
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      observer.unobserve(entry.target);
      if (preference.matches) continue;
      const animation = entry.target.animate(
        [{opacity: 0, transform: 'translateY(12px)'}, {opacity: 1, transform: 'none'}],
        {duration: 450, easing: 'cubic-bezier(.2,.7,.3,1)'},
      );
      animations.add(animation);
      animation.finished.then(() => animations.delete(animation)).catch(() => {});
    }
  }, {threshold: .12});
  document.querySelectorAll('[data-reveal]:not(.cica-hero-copy)').forEach(el => observer.observe(el));
  preference.addEventListener('change', () => {
    if (preference.matches) animations.forEach(animation => animation.cancel());
  });
})();
