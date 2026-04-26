export function IcosahedronFallback() {
  return (
    <svg
      viewBox="-100 -100 200 200"
      width="100%"
      height="100%"
      style={{ position: "absolute", inset: 0 }}
      aria-hidden
    >
      <defs>
        <radialGradient id="halo" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#00D26A" stopOpacity="0.3" />
          <stop offset="1" stopColor="#00D26A" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="0" cy="0" r="80" fill="url(#halo)" />
      <g fill="none" stroke="#F2F1EA" strokeWidth="0.6" strokeOpacity="0.7">
        <polygon points="0,-70 60,-22 38,58 -38,58 -60,-22" />
        <polygon points="0,-70 -60,-22 -38,58 38,58 60,-22" />
        <line x1="0" y1="-70" x2="0" y2="0" />
        <line x1="60" y1="-22" x2="0" y2="0" />
        <line x1="38" y1="58" x2="0" y2="0" />
        <line x1="-38" y1="58" x2="0" y2="0" />
        <line x1="-60" y1="-22" x2="0" y2="0" />
        <circle cx="0" cy="-70" r="2" fill="#00D26A" stroke="none" />
        <circle cx="60" cy="-22" r="1.4" fill="#F2F1EA" stroke="none" />
        <circle cx="38" cy="58" r="1.4" fill="#F2F1EA" stroke="none" />
        <circle cx="-38" cy="58" r="1.4" fill="#00D26A" stroke="none" />
        <circle cx="-60" cy="-22" r="1.4" fill="#F2F1EA" stroke="none" />
      </g>
    </svg>
  );
}
