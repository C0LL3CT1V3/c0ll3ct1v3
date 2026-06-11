/** Client-side preview document for pasted HTML/CSS (scripts stripped). */

const SCRIPT_RE = /<\s*script\b[^>]*>[\s\S]*?<\/\s*script\s*>/gi;
const SCRIPT_VOID_RE = /<\s*script\b[^>]*\/?>/gi;

export function stripUnsafeHtml(html) {
  return (html || '')
    .replace(SCRIPT_RE, '')
    .replace(SCRIPT_VOID_RE, '')
    .replace(/\s+on[a-z]+\s*=\s*(["']).*?\1/gi, '');
}

export function buildPreviewDocument({ html, css, googleFontsHref, title = 'Profile preview' }) {
  const safeHtml = stripUnsafeHtml(html);
  const safeCss = (css || '').replace(/@import/gi, '/* blocked */').replace(/javascript:/gi, '');
  let fonts = '';
  if (googleFontsHref && googleFontsHref.startsWith('https://fonts.googleapis.com/css2?')) {
    fonts = `<link rel="stylesheet" href="${googleFontsHref}" crossorigin="anonymous" />`;
  }
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${title}</title>
  ${fonts}
  <style>${safeCss}</style>
</head>
<body>
${safeHtml}
</body>
</html>`;
}

export const DEFAULT_PROFILE_HTML = `<main class="profile">
  <header class="profile-hero">
    <h1>Your name</h1>
    <p>Your tagline goes here.</p>
  </header>
  <section class="profile-about">
    <h2>About</h2>
    <p>Write about your sound, your city, your vibe.</p>
  </section>
  <section class="profile-music">
    <h2>Music</h2>
    <p>Embed tracks or link streaming — use <code>{{binding_key}}</code> for workbench media.</p>
  </section>
</main>`;

export const DEFAULT_PROFILE_CSS = `body {
  margin: 0;
  font-family: system-ui, sans-serif;
  background: #0a0a0c;
  color: #e8e8ec;
}

.profile {
  max-width: 720px;
  margin: 0 auto;
  padding: 2rem 1.25rem 4rem;
}

.profile-hero h1 {
  font-size: 2.5rem;
  margin: 0 0 0.5rem;
}

.profile-hero p {
  color: #a8a8b8;
  margin: 0;
}

section {
  margin-top: 2rem;
}

h2 {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #888;
}
`;
