/**
 * YouTube Video Language Converter - Frontend Dashboard Application
 */

document.addEventListener("DOMContentLoaded", () => {
  // App State
  const state = {
    currentVideo: null,
    currentJobId: null,
    pollInterval: null,
    languages: [],
    selectedDuration: 600, // seconds
    customStartTime: 0,
    customEndTime: 300,
  };

  // DOM Elements
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("video-file-input");
  const ytInput = document.getElementById("youtube-url-input");
  const btnLoadYt = document.getElementById("btn-load-youtube");
  const ytLoader = document.getElementById("yt-loader");
  
  const videoMetaBox = document.getElementById("video-meta-box");
  const metaFilename = document.getElementById("meta-filename");
  const metaDuration = document.getElementById("meta-duration");
  const metaResolution = document.getElementById("meta-resolution");
  const metaFps = document.getElementById("meta-fps");
  const metaFilesize = document.getElementById("meta-filesize");
  const metaAudioCodec = document.getElementById("meta-audio-codec");
  const metaChannels = document.getElementById("meta-channels");

  const origLangSelect = document.getElementById("orig-language-select");
  const targetLangSelect = document.getElementById("target-language-select");
  const btnSwapLang = document.getElementById("btn-swap-languages");
  const langError = document.getElementById("language-error");

  const durationPills = document.querySelectorAll(".duration-pill input");
  const customDurationFields = document.getElementById("custom-duration-fields");
  const customStartInput = document.getElementById("custom-start-time");
  const customEndInput = document.getElementById("custom-end-time");
  const displaySelectedDuration = document.getElementById("display-selected-duration");

  const sliderVoiceVol = document.getElementById("slider-voice-vol");
  const valVoiceVol = document.getElementById("val-voice-vol");
  const sliderBgVol = document.getElementById("slider-bg-vol");
  const valBgVol = document.getElementById("val-bg-vol");
  const sliderSfxVol = document.getElementById("slider-sfx-vol");
  const valSfxVol = document.getElementById("val-sfx-vol");

  const togglePreserveBg = document.getElementById("toggle-preserve-bg-music");
  const togglePreserveSfx = document.getElementById("toggle-preserve-sfx");
  const toggleReplaceSpeech = document.getElementById("toggle-replace-speech");
  const togglePreserveVideo = document.getElementById("toggle-preserve-video");

  const voiceGender = document.getElementById("voice-gender-select");
  const voiceStyle = document.getElementById("voice-style-select");
  const speakingSpeed = document.getElementById("speaking-speed-select");
  const voicePitch = document.getElementById("voice-pitch-select");

  const toggleSubOrig = document.getElementById("toggle-sub-orig");
  const toggleSubTarget = document.getElementById("toggle-sub-target");
  const toggleBurnSub = document.getElementById("toggle-burn-subtitles");
  const burnSubOptions = document.getElementById("burn-sub-options");
  const subPosition = document.getElementById("subtitle-position-select");
  const subSize = document.getElementById("subtitle-size-select");

  const btnOpenSummary = document.getElementById("btn-open-summary");
  const summaryModal = document.getElementById("summary-modal");
  const btnCloseSummary = document.getElementById("btn-close-summary");
  const btnCancelSummary = document.getElementById("btn-cancel-summary");
  const btnStartProcessing = document.getElementById("btn-start-processing");

  const durationModal = document.getElementById("duration-modal");
  const btnCloseDurModal = document.getElementById("btn-close-duration-modal");
  const btnAutoTrim = document.getElementById("btn-auto-trim");
  const btnChangeLimit = document.getElementById("btn-change-limit");
  const btnProcessFull = document.getElementById("btn-process-full");
  const btnCancelDuration = document.getElementById("btn-cancel-duration");
  const durWarningActual = document.getElementById("dur-warning-actual");
  const durWarningLimit = document.getElementById("dur-warning-limit");

  const sectionProcessing = document.getElementById("section-processing");
  const progressFill = document.getElementById("progress-fill");
  const progressStepText = document.getElementById("progress-step-text");
  const progressPercentText = document.getElementById("progress-percent-text");
  const jobStatusBadge = document.getElementById("job-status-badge");
  const statusWarningBanner = document.getElementById("status-warning-banner");
  const statusErrorBanner = document.getElementById("status-error-banner");

  const sectionPreview = document.getElementById("section-preview");
  const previewOrigVideo = document.getElementById("preview-orig-video");
  const previewTargetVideo = document.getElementById("preview-target-video");
  const audioOrigPlayer = document.getElementById("audio-orig-player");
  const audioTransPlayer = document.getElementById("audio-trans-player");
  const segmentsList = document.getElementById("segments-list");

  const sectionDownload = document.getElementById("section-download");
  const downloadButtonsContainer = document.getElementById("download-buttons-container");

  // Tab switching
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      document.getElementById(targetId).classList.add("active");
    });
  });

  // Load Languages
  async function loadLanguages() {
    try {
      const res = await fetch("/api/languages");
      const data = await res.json();
      state.languages = data.languages;

      origLangSelect.innerHTML = "";
      targetLangSelect.innerHTML = "";

      data.languages.forEach((lang) => {
        const optOrig = document.createElement("option");
        optOrig.value = lang.code;
        optOrig.textContent = lang.name;
        if (lang.code === "en") optOrig.selected = true;
        origLangSelect.appendChild(optOrig);

        if (lang.code !== "auto") {
          const optTarget = document.createElement("option");
          optTarget.value = lang.code;
          optTarget.textContent = lang.name;
          if (lang.code === "te") optTarget.selected = true; // default Telugu
          targetLangSelect.appendChild(optTarget);
        }
      });
    } catch (err) {
      console.error("Failed to load languages:", err);
    }
  }
  loadLanguages();

  // Language Swap
  btnSwapLang.addEventListener("click", () => {
    const curOrig = origLangSelect.value;
    const curTarget = targetLangSelect.value;
    if (curOrig === "auto") {
      alert("Cannot swap when original language is set to 'Auto Detect'. Please choose a specific language first.");
      return;
    }
    origLangSelect.value = curTarget;
    targetLangSelect.value = curOrig;
    validateLanguages();
  });

  function validateLanguages() {
    if (origLangSelect.value !== "auto" && origLangSelect.value === targetLangSelect.value) {
      langError.textContent = "Original Spoken Language and Target Language cannot be identical.";
      langError.style.display = "block";
      return false;
    }
    langError.style.display = "none";
    return true;
  }
  origLangSelect.addEventListener("change", validateLanguages);
  targetLangSelect.addEventListener("change", validateLanguages);

  // Drag and Drop Upload
  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });
  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      handleFileUpload(fileInput.files[0]);
    }
  });

  async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append("file", file);

    dropZone.innerHTML = `
      <div class="loader-sm" style="width:28px;height:28px;margin:1rem auto;"></div>
      <p class="drop-title">Uploading & inspecting video metadata...</p>
      <p class="drop-sub">${escapeHtml(file.name)} (${(file.size / (1024*1024)).toFixed(1)}MB)</p>
    `;

    try {
      const res = await fetch("/api/video/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");

      populateVideoMetadata(data.video);
    } catch (err) {
      alert("Upload Error: " + err.message);
    } finally {
      // Restore drop zone
      dropZone.innerHTML = `
        <input type="file" id="video-file-input" accept=".mp4,.mov,.mkv,.avi,.webm" hidden>
        <div class="drop-icon">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" x2="12" y1="3" y2="15"/>
          </svg>
        </div>
        <p class="drop-title">Drag & drop video file or <span class="highlight">browse</span></p>
        <p class="drop-sub">Supported formats: MP4, MOV, MKV, AVI, WEBM (Max 1GB)</p>
      `;
    }
  }

  // YouTube Ingestion
  btnLoadYt.addEventListener("click", async () => {
    const url = ytInput.value.trim();
    if (!url) {
      alert("Please enter a valid YouTube video URL.");
      return;
    }

    btnLoadYt.disabled = true;
    ytLoader.style.display = "inline-block";
    btnLoadYt.querySelector(".btn-text").textContent = "Loading...";

    try {
      const res = await fetch("/api/video/youtube", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to load YouTube video");

      populateVideoMetadata(data.video);
    } catch (err) {
      alert("YouTube Error: " + err.message);
    } finally {
      btnLoadYt.disabled = false;
      ytLoader.style.display = "none";
      btnLoadYt.querySelector(".btn-text").textContent = "Load Video";
    }
  });

  function populateVideoMetadata(v) {
    state.currentVideo = v;
    metaFilename.textContent = v.original_name;
    metaDuration.textContent = formatSeconds(v.duration);
    metaResolution.textContent = v.resolution;
    metaFps.textContent = `${v.fps} fps`;
    metaFilesize.textContent = `${(v.file_size / (1024 * 1024)).toFixed(1)} MB`;
    metaAudioCodec.textContent = v.audio_codec.toUpperCase();
    metaChannels.textContent = `${v.channels} ch / ${v.sample_rate} Hz`;
    videoMetaBox.style.display = "block";
  }

  // Duration Limit Radio Pills
  durationPills.forEach((pill) => {
    pill.addEventListener("change", (e) => {
      document.querySelectorAll(".duration-pill").forEach((p) => p.classList.remove("active"));
      pill.closest(".duration-pill").classList.add("active");

      const val = e.target.value;
      if (val === "custom") {
        customDurationFields.style.display = "block";
        updateCustomDuration();
      } else {
        customDurationFields.style.display = "none";
        const sec = parseInt(val, 10);
        state.selectedDuration = sec;
        displaySelectedDuration.textContent = sec === 0 ? "Full Video (Unlimited)" : formatSeconds(sec);
      }
    });
  });

  function parseTimeToSec(str) {
    const parts = str.trim().split(":").map(Number);
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    return Number(str) || 0;
  }

  function updateCustomDuration() {
    const s = parseTimeToSec(customStartInput.value);
    const e = parseTimeToSec(customEndInput.value);
    state.customStartTime = s;
    state.customEndTime = e;
    const dur = Math.max(0, e - s);
    state.selectedDuration = dur;
    displaySelectedDuration.textContent = formatSeconds(dur);
  }
  customStartInput.addEventListener("input", updateCustomDuration);
  customEndInput.addEventListener("input", updateCustomDuration);

  // Volume Sliders
  sliderVoiceVol.addEventListener("input", (e) => (valVoiceVol.textContent = `${e.target.value}%`));
  sliderBgVol.addEventListener("input", (e) => (valBgVol.textContent = `${e.target.value}%`));
  sliderSfxVol.addEventListener("input", (e) => (valSfxVol.textContent = `${e.target.value}%`));

  // Burn Subtitles Toggle
  toggleBurnSub.addEventListener("change", (e) => {
    burnSubOptions.style.display = e.target.checked ? "grid" : "none";
  });

  // Open Summary Confirmation
  btnOpenSummary.addEventListener("click", () => {
    if (!state.currentVideo) {
      alert("Please upload a video or load a YouTube URL first.");
      document.getElementById("section-video-input").scrollIntoView({ behavior: "smooth" });
      return;
    }

    if (!validateLanguages()) {
      return;
    }

    const vDur = state.currentVideo.duration;
    const limit = state.selectedDuration;

    // Check if video duration exceeds selected duration limit
    if (limit > 0 && vDur > limit) {
      durWarningActual.textContent = formatSeconds(vDur);
      durWarningLimit.textContent = formatSeconds(limit);
      durationModal.style.display = "flex";
      return;
    }

    showSummaryModal(false);
  });

  function showSummaryModal(autoTrim) {
    document.getElementById("sum-filename").textContent = state.currentVideo.original_name;
    document.getElementById("sum-duration").textContent = formatSeconds(state.currentVideo.duration);
    
    const origLangName = origLangSelect.options[origLangSelect.selectedIndex].text;
    const targetLangName = targetLangSelect.options[targetLangSelect.selectedIndex].text;
    document.getElementById("sum-orig-lang").textContent = origLangName;
    document.getElementById("sum-target-lang").textContent = targetLangName;

    document.getElementById("sum-max-dur").textContent = state.selectedDuration === 0 ? "Full Video" : formatSeconds(state.selectedDuration);
    document.getElementById("sum-music").textContent = togglePreserveBg.checked ? "Preserved (ON)" : "Muted";
    document.getElementById("sum-sfx").textContent = togglePreserveSfx.checked ? "Preserved (ON)" : "Muted";
    document.getElementById("sum-subtitles").textContent = (toggleSubOrig.checked || toggleSubTarget.checked) ? "Enabled" : "Disabled";
    document.getElementById("sum-voice").textContent = `${voiceGender.value} / ${voiceStyle.value} (${speakingSpeed.value}x)`;

    summaryModal.dataset.autoTrim = autoTrim ? "true" : "false";
    summaryModal.style.display = "flex";
  }

  // Duration Modal Actions
  btnCloseDurModal.addEventListener("click", () => (durationModal.style.display = "none"));
  btnCancelDuration.addEventListener("click", () => (durationModal.style.display = "none"));

  btnAutoTrim.addEventListener("click", () => {
    durationModal.style.display = "none";
    showSummaryModal(true);
  });

  btnChangeLimit.addEventListener("click", () => {
    durationModal.style.display = "none";
    document.getElementById("section-duration-limit").scrollIntoView({ behavior: "smooth" });
  });

  btnProcessFull.addEventListener("click", () => {
    durationModal.style.display = "none";
    state.selectedDuration = 0;
    displaySelectedDuration.textContent = "Full Video (Unlimited)";
    document.querySelectorAll(".duration-pill").forEach(p => p.classList.remove("active"));
    const fullPill = Array.from(document.querySelectorAll(".duration-pill input")).find(i => i.value === "0");
    if (fullPill) {
      fullPill.checked = true;
      fullPill.closest(".duration-pill").classList.add("active");
    }
    showSummaryModal(false);
  });

  // Modal Closures
  btnCloseSummary.addEventListener("click", () => (summaryModal.style.display = "none"));
  btnCancelSummary.addEventListener("click", () => (summaryModal.style.display = "none"));

  // Start Processing
  btnStartProcessing.addEventListener("click", async () => {
    summaryModal.style.display = "none";

    const autoTrim = summaryModal.dataset.autoTrim === "true";

    const payload = {
      video_id: state.currentVideo.id,
      original_language: origLangSelect.value,
      target_language: targetLangSelect.value,
      max_duration: state.selectedDuration,
      trim_start: state.customStartTime,
      trim_end: state.customEndTime > 0 ? state.customEndTime : null,
      auto_trim_if_exceeded: autoTrim,
      
      preserve_background_music: togglePreserveBg.checked,
      preserve_sound_effects: togglePreserveSfx.checked,
      replace_spoken_language: toggleReplaceSpeech.checked,
      preserve_original_video: togglePreserveVideo.checked,
      voice_volume: parseFloat(sliderVoiceVol.value) / 100.0,
      background_music_volume: parseFloat(sliderBgVol.value) / 100.0,
      sound_effects_volume: parseFloat(sliderSfxVol.value) / 100.0,
      mute_original_speech: true,
      
      voice_gender: voiceGender.value,
      voice_style: voiceStyle.value,
      speaking_speed: parseFloat(speakingSpeed.value),
      voice_pitch: voicePitch.value,
      
      generate_original_subtitles: toggleSubOrig.checked,
      generate_target_subtitles: toggleSubTarget.checked,
      burn_subtitles: toggleBurnSub.checked,
      subtitle_position: subPosition.value,
      subtitle_size: subSize.value,
    };

    try {
      const res = await fetch("/api/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to start processing");

      state.currentJobId = data.job_id;
      showProcessingUI();
      startJobPolling(data.job_id);
    } catch (err) {
      alert("Error: " + err.message);
    }
  });

  function showProcessingUI() {
    sectionProcessing.style.display = "block";
    sectionPreview.style.display = "none";
    sectionDownload.style.display = "none";
    statusWarningBanner.style.display = "none";
    statusErrorBanner.style.display = "none";
    
    // Reset stages UI
    document.querySelectorAll(".stage-item").forEach(item => {
      item.classList.remove("completed", "active");
    });

    sectionProcessing.scrollIntoView({ behavior: "smooth" });
  }

  function startJobPolling(jobId) {
    if (state.pollInterval) clearInterval(state.pollInterval);

    state.pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/job/${jobId}`);
        const job = await res.json();
        if (!res.ok) return;

        updateProgressUI(job);

        if (job.status === "COMPLETED") {
          clearInterval(state.pollInterval);
          onJobComplete(job);
        } else if (job.status === "FAILED") {
          clearInterval(state.pollInterval);
          onJobFailed(job);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 1500);
  }

  function updateProgressUI(job) {
    progressFill.style.width = `${job.progress}%`;
    progressPercentText.textContent = `${job.progress}%`;
    progressStepText.textContent = job.stage_message;
    jobStatusBadge.textContent = job.status;

    // Highlight stages
    document.querySelectorAll(".stage-item").forEach(item => {
      const stageNum = parseInt(item.getAttribute("data-stage"), 10);
      if (stageNum < job.current_stage) {
        item.classList.add("completed");
        item.classList.remove("active");
      } else if (stageNum === job.current_stage) {
        item.classList.add("active");
        item.classList.remove("completed");
      } else {
        item.classList.remove("completed", "active");
      }
    });

    if (job.warning_message) {
      statusWarningBanner.textContent = job.warning_message;
      statusWarningBanner.style.display = "block";
    }
  }

  function onJobComplete(job) {
    progressFill.style.width = "100%";
    progressPercentText.textContent = "100%";
    jobStatusBadge.textContent = "Completed";
    jobStatusBadge.classList.replace("badge-accent", "badge-success");

    // Display Preview section
    sectionPreview.style.display = "block";
    previewOrigVideo.src = `/api/media/${job.id}/original_video`;
    previewTargetVideo.src = `/api/media/${job.id}/target_video`;
    audioOrigPlayer.src = `/api/media/${job.id}/original_audio`;
    audioTransPlayer.src = `/api/media/${job.id}/translated_audio`;

    // Render dialogue segments
    segmentsList.innerHTML = "";
    if (job.dialogue_segments && job.dialogue_segments.length > 0) {
      job.dialogue_segments.forEach(seg => {
        const card = document.createElement("div");
        card.className = "segment-card";
        card.innerHTML = `
          <span class="segment-time">${formatSeconds(seg.start_time)} → ${formatSeconds(seg.end_time)}</span>
          <div class="segment-orig"><strong>Orig:</strong> ${escapeHtml(seg.original_text)}</div>
          <div class="segment-trans"><strong>Translated:</strong> ${escapeHtml(seg.translated_text)}</div>
        `;
        segmentsList.appendChild(card);
      });
    }

    // Display Download section
    sectionDownload.style.display = "block";
    downloadButtonsContainer.innerHTML = "";

    job.output_files.forEach(f => {
      const btn = document.createElement("a");
      btn.href = `/api/download/${f.id}`;
      btn.className = f.file_type === "video" ? "btn btn-download-primary" : "btn btn-secondary";
      
      let icon = "📄";
      if (f.file_type === "video") icon = "🎬";
      else if (f.file_type === "srt" || f.file_type === "vtt") icon = "💬";

      btn.innerHTML = `<span>${icon}</span> <span>Download ${escapeHtml(f.filename)}</span>`;
      downloadButtonsContainer.appendChild(btn);
    });

    sectionPreview.scrollIntoView({ behavior: "smooth" });
  }

  function onJobFailed(job) {
    jobStatusBadge.textContent = "Failed";
    jobStatusBadge.classList.replace("badge-accent", "badge-danger");
    statusErrorBanner.textContent = job.error_message || "Video conversion failed. Please review input files.";
    statusErrorBanner.style.display = "block";
  }

  function formatSeconds(sec) {
    const s = Math.max(0, Math.floor(sec || 0));
    const hours = Math.floor(s / 3600);
    const mins = Math.floor((s % 3600) / 60);
    const secs = s % 60;
    return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
});
