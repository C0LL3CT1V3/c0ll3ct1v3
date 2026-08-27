import { getConsoleErrors, installConsoleBuffer, resetConsoleBufferForTests } from './consoleBuffer';
import { buildReportPayload, FIXTURE_JPEG } from './submitReport';
import { MAX_EDGE, scaledSize, toJpegDataUrl } from './toJpegDataUrl';

describe('consoleBuffer', () => {
  beforeEach(() => {
    resetConsoleBufferForTests();
    installConsoleBuffer();
  });

  afterEach(() => {
    resetConsoleBufferForTests();
  });

  test('keeps a rolling list of console.error messages', () => {
    console.error('alpha');
    console.error('beta');
    const entries = getConsoleErrors();
    expect(entries.map((e) => e.msg)).toEqual(expect.arrayContaining(['alpha', 'beta']));
    expect(entries[0].t).toEqual(expect.any(Number));
  });
});

describe('buildReportPayload', () => {
  test('shapes the Lambda contract', () => {
    const payload = buildReportPayload({
      imageDataUrl: FIXTURE_JPEG,
      summary: '  Vault upload hangs  ',
      type: 'feature',
    });
    expect(payload.summary).toBe('Vault upload hangs');
    expect(payload.type).toBe('feature');
    expect(payload.image_data_url).toMatch(/^data:image\/jpeg;base64,/);
    expect(payload.page_url).toEqual(expect.any(String));
    expect(payload.viewport.w).toEqual(expect.any(Number));
    expect(payload.user_agent).toEqual(expect.any(String));
    expect(Array.isArray(payload.console_errors)).toBe(true);
  });
});

describe('toJpegDataUrl', () => {
  test('scaledSize leaves small frames alone', () => {
    expect(scaledSize(800, 600)).toEqual({ width: 800, height: 600 });
  });

  test('scaledSize caps the long edge', () => {
    expect(scaledSize(3840, 2160)).toEqual({ width: MAX_EDGE, height: 1080 });
  });

  test('rejects empty input', async () => {
    await expect(toJpegDataUrl('')).rejects.toThrow(/empty/i);
  });
});
