import { useCallback, useEffect, useState } from 'react';
import { useApiClient } from '../../hooks/useApiClient';

export function useEpkBuilder() {
  const { apiClient, authReady } = useApiClient();
  const [draft, setDraft] = useState(null);
  const [componentMap, setComponentMap] = useState([]);
  const [visions, setVisions] = useState([]);
  const [selectedVisionId, setSelectedVisionId] = useState('');
  const [spec, setSpec] = useState('');
  const [threadId, setThreadId] = useState(null);
  const [currentIterationId, setCurrentIterationId] = useState(null);
  const [screenshotStorageKey, setScreenshotStorageKey] = useState(null);
  const [reasoningSummary, setReasoningSummary] = useState('');
  const [critiqueSummary, setCritiqueSummary] = useState('');
  const [matchScore, setMatchScore] = useState(null);
  const [revisionCycles, setRevisionCycles] = useState(null);
  const [fontPalette, setFontPalette] = useState(null);
  const [completeness, setCompleteness] = useState(null);
  const [designHistory, setDesignHistory] = useState([]);
  const [phase, setPhase] = useState('idle');
  const [error, setError] = useState('');

  const loadVisions = useCallback(async () => {
    const res = await apiClient.get('/media/visions');
    setVisions(res.data || []);
    return res.data || [];
  }, [apiClient]);

  const loadDesignHistory = useCallback(async () => {
    const res = await apiClient.get('/manager/epk/iterations', { params: { limit: 40 } });
    const rows = res.data?.iterations || [];
    setDesignHistory(rows);
    return rows;
  }, [apiClient]);

  const loadDraft = useCallback(async () => {
    const res = await apiClient.get('/manager/epk/draft');
    setDraft(res.data);
    if (res.data?.vision_id) {
      setSelectedVisionId(res.data.vision_id);
    }
    if (res.data?.spec_snapshot) {
      setSpec(res.data.spec_snapshot);
    }
    if (res.data?.font_palette) {
      setFontPalette(res.data.font_palette);
    }
    if (res.data?.completeness) {
      setCompleteness(res.data.completeness);
    }
    const mapRes = await apiClient.get('/manager/epk/component-map');
    setComponentMap(mapRes.data?.components || []);
    return res.data;
  }, [apiClient]);

  useEffect(() => {
    if (!authReady) return;
    loadVisions().catch(() => {});
    loadDesignHistory().catch(() => {});
    loadDraft().catch((err) => {
      setError(err?.response?.data?.detail || 'Failed to load EPK draft.');
    });
  }, [authReady, loadDesignHistory, loadDraft, loadVisions]);

  const applyIterationPreview = (data) => {
    setCurrentIterationId(data.id);
    setScreenshotStorageKey(data.screenshot_storage_key || null);
    setReasoningSummary(data.reasoning_summary || '');
    setCritiqueSummary(data.critique_summary || '');
    setMatchScore(data.match_score ?? null);
    setRevisionCycles(data.revision_cycles ?? null);
    setFontPalette(data.font_palette || null);
    if (data.vision_id) {
      setSelectedVisionId(data.vision_id);
    }
    if (data.spec_snapshot) {
      setSpec(data.spec_snapshot);
    }
    setDraft({
      format: data.format || 'html_v1',
      html: data.html,
      css: data.css,
      asset_bindings: data.asset_bindings,
      vision_id: data.vision_id,
      spec_snapshot: data.spec_snapshot,
      sim_render_url: data.sim_render_url,
      design: data.design,
      site: data.site,
      tracks: data.tracks,
      photos: data.photos,
    });
  };

  const applyBuildResult = (data) => {
    setThreadId(data.thread_id);
    setCurrentIterationId(data.iteration_id);
    setScreenshotStorageKey(data.screenshot_storage_key || null);
    setReasoningSummary(data.reasoning_summary || '');
    setCritiqueSummary(data.critique_summary || '');
    setMatchScore(data.match_score ?? null);
    setRevisionCycles(data.revision_cycles ?? null);
    setDraft({
      format: data.format || 'html_v1',
      html: data.html,
      css: data.css,
      asset_bindings: data.asset_bindings,
      vision_id: data.vision_id,
      spec_snapshot: data.spec_snapshot,
      sim_render_url: data.sim_render_url,
      design: data.design,
      site: data.site,
      tracks: data.tracks,
      photos: data.photos,
    });
  };

  const buildFromVision = useCallback(
    async (visionId, specText) => {
      setPhase('generating');
      setError('');
      try {
        const res = await apiClient.post('/manager/epk/build-from-vision', {
          vision_id: visionId,
          spec: specText,
          thread_id: threadId,
        });
        applyBuildResult(res.data);
        await loadDesignHistory();
        await loadDraft();
        setPhase('preview');
        return res.data;
      } catch (err) {
        setError(err?.response?.data?.detail || err.message || 'EPK build failed.');
        setPhase('idle');
        throw err;
      }
    },
    [apiClient, loadDesignHistory, threadId],
  );

  const previewIteration = useCallback(
    async (iterationId) => {
      setPhase('generating');
      setError('');
      try {
        const res = await apiClient.get(`/manager/epk/iterations/${iterationId}`);
        applyIterationPreview(res.data);
        setPhase('preview');
        return res.data;
      } catch (err) {
        setError(err?.response?.data?.detail || err.message || 'Failed to load design.');
        setPhase('preview');
        throw err;
      }
    },
    [apiClient],
  );

  const restoreIteration = useCallback(
    async (iterationId) => {
      setPhase('generating');
      setError('');
      try {
        const res = await apiClient.post(`/manager/epk/iterations/${iterationId}/restore`);
        applyIterationPreview(res.data);
        setPhase('preview');
        return res.data;
      } catch (err) {
        setError(err?.response?.data?.detail || err.message || 'Failed to restore design.');
        setPhase('preview');
        throw err;
      }
    },
    [apiClient],
  );

  const captureAndUploadScreenshot = async (rootEl, uploadUrl) => {
    if (!rootEl || !uploadUrl) return;
    try {
      const html2canvas = (await import('html2canvas')).default;
      const canvas = await html2canvas(rootEl, { useCORS: true, scale: 1 });
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
      if (!blob) return;
      await fetch(uploadUrl, {
        method: 'PUT',
        body: blob,
        headers: { 'Content-Type': 'image/png' },
      });
    } catch {
      /* screenshot optional */
    }
  };

  const iterate = useCallback(
    async (prompt, previewRootRef) => {
      setPhase('generating');
      setError('');
      try {
        const res = await apiClient.post('/manager/epk/iterate', {
          prompt,
          thread_id: threadId,
        });
        const data = res.data;
        setThreadId(data.thread_id);
        setCurrentIterationId(data.iteration_id);
        setScreenshotStorageKey(data.screenshot_storage_key || null);
        setReasoningSummary(data.reasoning_summary || '');
        setDraft({
          format: 'layout',
          design: data.design,
          site: data.site,
          tracks: data.tracks,
          photos: data.photos,
        });
        setPhase('preview');
        await loadDesignHistory();
        if (previewRootRef?.current && data.screenshot_upload_url) {
          await captureAndUploadScreenshot(previewRootRef.current, data.screenshot_upload_url);
        }
        return data;
      } catch (err) {
        setError(err?.response?.data?.detail || err.message || 'EPK iteration failed.');
        setPhase('idle');
        throw err;
      }
    },
    [apiClient, loadDesignHistory, threadId],
  );

  const submitAnnotations = useCallback(
    async (annotations) => {
      if (!currentIterationId) return;
      setPhase('annotating');
      setError('');
      try {
        const res = await apiClient.post(`/manager/epk/iterations/${currentIterationId}/annotate`, {
          annotations,
          screenshot_storage_key: screenshotStorageKey,
        });
        setPhase('preview');
        return res.data;
      } catch (err) {
        setError(err?.response?.data?.detail || 'Failed to save annotations.');
        setPhase('preview');
        throw err;
      }
    },
    [apiClient, currentIterationId, screenshotStorageKey],
  );

  const refine = useCallback(
    async (previewRootRef) => {
      if (!currentIterationId) return;
      setPhase('refining');
      setError('');
      try {
        const res = await apiClient.post(`/manager/epk/iterations/${currentIterationId}/refine`);
        const data = res.data;
        setCurrentIterationId(data.iteration_id);
        setScreenshotStorageKey(data.screenshot_storage_key || null);
        setReasoningSummary(data.reasoning_summary || '');
        if (data.format === 'html_v1') {
          setDraft({
            format: 'html_v1',
            html: data.html,
            css: data.css,
            asset_bindings: data.asset_bindings,
            sim_render_url: data.sim_render_url,
            design: {},
            site: {},
            tracks: [],
            photos: [],
          });
        } else {
          setDraft({
            format: 'layout',
            design: data.design,
            site: data.site,
            tracks: data.tracks,
            photos: data.photos,
          });
        }
        setPhase('preview');
        await loadDesignHistory();
        if (previewRootRef?.current && data.screenshot_upload_url) {
          await captureAndUploadScreenshot(previewRootRef.current, data.screenshot_upload_url);
        }
        return data;
      } catch (err) {
        setError(err?.response?.data?.detail || 'Refine failed.');
        setPhase('preview');
        throw err;
      }
    },
    [apiClient, currentIterationId, loadDesignHistory],
  );

  const accept = useCallback(
    async (consentForTraining = false) => {
      if (!currentIterationId) return;
      await apiClient.post(`/manager/epk/iterations/${currentIterationId}/accept`, {
        consent_for_training: consentForTraining,
      });
      setPhase('accepted');
    },
    [apiClient, currentIterationId],
  );

  const publish = useCallback(async () => {
    await apiClient.post('/manager/epk/draft/publish');
  }, [apiClient]);

  const saveCustomHtml = useCallback(
    async ({ html, css, assetBindings, googleFontsHref }) => {
      setError('');
      const res = await apiClient.post('/manager/epk/draft/custom', {
        html,
        css,
        asset_bindings: assetBindings || draft?.asset_bindings || {},
        google_fonts_href: googleFontsHref || draft?.google_fonts_href || null,
      });
      setDraft(res.data);
      if (res.data?.completeness) {
        setCompleteness(res.data.completeness);
      }
      setPhase('preview');
      return res.data;
    },
    [apiClient, draft],
  );

  return {
    draft,
    componentMap,
    visions,
    selectedVisionId,
    setSelectedVisionId,
    spec,
    setSpec,
    threadId,
    setThreadId,
    currentIterationId,
    reasoningSummary,
    setReasoningSummary,
    critiqueSummary,
    matchScore,
    revisionCycles,
    fontPalette,
    completeness,
    designHistory,
    loadDesignHistory,
    previewIteration,
    restoreIteration,
    phase,
    setPhase,
    error,
    setError,
    loadDraft,
    buildFromVision,
    iterate,
    submitAnnotations,
    refine,
    accept,
    publish,
    saveCustomHtml,
    captureAndUploadScreenshot,
  };
}
