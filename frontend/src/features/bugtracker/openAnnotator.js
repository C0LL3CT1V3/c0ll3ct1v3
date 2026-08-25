import * as markerjs2 from 'markerjs2';

export function openAnnotator(dataUrl) {
  return new Promise((resolve, reject) => {
    const img = document.createElement('img');
    img.alt = 'Screenshot to annotate';
    img.src = dataUrl;
    img.style.position = 'fixed';
    img.style.left = '-12000px';
    img.style.top = '0';
    img.style.maxWidth = 'none';
    document.body.appendChild(img);

    let settled = false;
    const finish = (fn) => (value) => {
      if (settled) return;
      settled = true;
      try {
        img.remove();
      } catch {
        /* already gone */
      }
      fn(value);
    };

    const succeed = finish(resolve);
    const fail = finish(reject);

    img.onerror = () => fail(new Error('Could not load screenshot for annotation'));
    img.onload = () => {
      const markerArea = new markerjs2.MarkerArea(img);
      markerArea.settings.displayMode = 'popup';
      markerArea.addEventListener('render', (event) => {
        succeed(event.dataUrl);
      });
      markerArea.addEventListener('close', () => {
        fail(Object.assign(new Error('cancelled'), { cancelled: true }));
      });
      markerArea.show();
    };
  });
}
