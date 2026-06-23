<template>
  <svg
    class="moon-scene"
    viewBox="0 0 220 170"
    role="img"
    aria-label="A small figure standing under the moon, holding a balloon, while two others drift away"
  >
    <!-- moon halo -->
    <circle cx="166" cy="40" r="48" fill="var(--moon)" opacity="0.16" />
    <circle cx="166" cy="40" r="22" fill="var(--moon)" />

    <!-- drifting balloons (tasks already let go) -->
    <g opacity="0.9">
      <line x1="44" y1="58" x2="40" y2="78" stroke="var(--ink-muted)" stroke-width="1.2" />
      <ellipse cx="44" cy="48" rx="11" ry="13" fill="var(--sage)" />
    </g>
    <g opacity="0.85">
      <line x1="88" y1="34" x2="84" y2="52" stroke="var(--ink-muted)" stroke-width="1.2" />
      <ellipse cx="88" cy="25" rx="9" ry="11" fill="var(--dusk)" />
    </g>

    <!-- birds -->
    <path d="M20 20 q4 -5 8 0 q4 -5 8 0" fill="none" stroke="var(--ink-muted)" stroke-width="1.4" stroke-linecap="round" />
    <path d="M120 12 q3 -4 6 0 q3 -4 6 0" fill="none" stroke="var(--ink-muted)" stroke-width="1.4" stroke-linecap="round" />

    <!-- ground (drawn twice, offset, for a hand-inked wobble) -->
    <path d="M6 152 H214" fill="none" stroke="var(--ink)" stroke-width="2" opacity="0.45" stroke-linecap="round" />
    <path d="M6 152.6 H214" fill="none" stroke="var(--ink)" stroke-width="1.4" opacity="0.25" stroke-linecap="round" />

    <!-- figure -->
    <g>
      <!-- held balloon -->
      <line x1="118" y1="96" x2="132" y2="68" stroke="var(--ink-muted)" stroke-width="1.3" />
      <ellipse cx="132" cy="56" rx="13" ry="16" fill="var(--blossom)" />

      <!-- body (flat silhouette, slightly doubled outline) -->
      <path
        d="M104 152 V120 q0 -10 8 -10 q8 0 8 10 v32"
        fill="var(--ink)"
      />
      <path
        d="M104 152 V120 q0 -10 8 -10 q8 0 8 10 v32"
        fill="none"
        stroke="var(--ink)"
        stroke-width="1"
        opacity="0.4"
        transform="translate(0.6,0.3)"
      />
      <!-- arm to balloon -->
      <path d="M118 122 L118 98" stroke="var(--ink)" stroke-width="4" stroke-linecap="round" />
      <!-- head -->
      <circle cx="112" cy="100" r="9" fill="var(--ink)" />
    </g>
  </svg>
</template>
