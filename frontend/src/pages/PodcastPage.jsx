import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Radio,
  Sparkles,
  Volume2,
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Download,
  Mic,
  Clock,
  BookOpen,
  Check,
  AlertCircle,
  Loader2,
  ChevronRight,
  Headphones,
} from 'lucide-react';
import { generatePodcast, getPodcastList, getPodcastAudioUrl } from '../api';
import { useStatus } from '../stores/status';
import { fadeInUp, stagger, staggerItem } from '../lib/variants';
import Button from '../components/ui/Button';
import { toast } from 'sonner';

const CHAPTER_SUGGESTIONS = [
  'Foundation Models & AI Engineering',
  'Prompt Engineering & In-Context Learning',
  'Retrieval-Augmented Generation (RAG) Architecture',
  'Vector Databases & Semantic Search',
  'Evaluation Frameworks & Hallucination Gating',
  'Memory Systems, Reflection & Agentic Loops',
  'Fine-Tuning, LoRA & Model Adaptation',
  'Serving, Quantization & Latency Optimization',
];

export default function PodcastPage() {
  const [topicInput, setTopicInput] = useState('');
  const [numTurns, setNumTurns] = useState(8);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState('');
  const [error, setError] = useState(null);

  const [episodes, setEpisodes] = useState([]);
  const [activeEpisode, setActiveEpisode] = useState(null);
  const [loadingEpisodes, setLoadingEpisodes] = useState(true);

  // Audio Player state
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [activeTurnIndex, setActiveTurnIndex] = useState(0);

  const ollama = useStatus((s) => s.ollama_available);

  useEffect(() => {
    loadEpisodes();
  }, []);

  const loadEpisodes = async () => {
    setLoadingEpisodes(true);
    try {
      const list = await getPodcastList();
      setEpisodes(list || []);
      if (list && list.length > 0 && !activeEpisode) {
        setActiveEpisode(list[0]);
      }
    } catch (err) {
      console.warn('Failed to load podcast episodes:', err);
    } finally {
      setLoadingEpisodes(false);
    }
  };

  const handleGenerate = async (customTopic = null) => {
    const targetTopic = customTopic || topicInput.trim();
    if (!targetTopic || isGenerating) return;

    setIsGenerating(true);
    setError(null);
    setGenerationStep('Retrieving material and drafting 2-person dialogue script...');

    try {
      const timer = setTimeout(() => {
        setGenerationStep('Synthesizing dual-voice neural audio (Alex & Sam)...');
      }, 4000);

      const episode = await generatePodcast(targetTopic, null, numTurns);
      clearTimeout(timer);

      setActiveEpisode(episode);
      setEpisodes((prev) => [episode, ...prev.filter((e) => e.id !== episode.id)]);
      setIsGenerating(false);
      setGenerationStep('');
      toast.success(`Generated: ${episode.title || targetTopic}`);

      // Auto-play new episode
      setTimeout(() => {
        if (audioRef.current) {
          audioRef.current.play().catch(() => {});
        }
      }, 400);
    } catch (err) {
      setIsGenerating(false);
      setGenerationStep('');
      setError(err?.message || 'Failed to generate podcast.');
      toast.error(err?.message || 'Failed to generate podcast.');
    }
  };

  // Sync audio time and active dialogue turn
  const handleTimeUpdate = () => {
    if (!audioRef.current) return;
    const time = audioRef.current.currentTime;
    setCurrentTime(time);

    if (activeEpisode?.turns?.length) {
      let turnIdx = 0;
      for (let i = 0; i < activeEpisode.turns.length; i++) {
        const turnStart = activeEpisode.turns[i].start_time_s || 0;
        if (time >= turnStart) {
          turnIdx = i;
        } else {
          break;
        }
      }
      setActiveTurnIndex(turnIdx);
    }
  };

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch((e) => toast.error(`Audio playback error: ${e.message}`));
    }
  };

  const seekTo = (seconds) => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = Math.max(0, Math.min(seconds, duration || 9999));
  };

  const handleSpeedChange = (rate) => {
    setPlaybackRate(rate);
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  };

  const formatTime = (secs) => {
    if (!secs || isNaN(secs)) return '00:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const currentSpeaker = activeEpisode?.turns?.[activeTurnIndex]?.speaker || 'HOST';
  const audioSrc = activeEpisode?.audio_url || (activeEpisode?.audio_filename ? getPodcastAudioUrl(activeEpisode.audio_filename) : '');

  return (
    <div className="flex flex-col h-full min-h-0 relative z-0">
      {/* Page Header */}
      <header className="flex items-center justify-between h-14 px-5 border-b border-border/80 bg-background/70 backdrop-blur-md flex-shrink-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-accent to-sky-400 text-white flex items-center justify-center shadow-md shadow-accent/20">
            <Radio size={16} />
          </div>
          <div>
            <h1 className="font-display font-semibold text-[15px] text-textMain flex items-center gap-2">
              <span>Podcast Studio</span>
              <span className="text-[10.5px] font-mono px-2 py-0.5 rounded-full bg-accentSoft text-accent border border-accent/25">
                Two-Voice Neural TTS
              </span>
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-1.5 text-[11px] font-mono px-3 py-1 rounded-full border border-border/80 bg-panel/70 backdrop-blur text-textMuted shadow-sm">
            <Sparkles size={11} className="text-accent" />
            <span>{ollama ? 'ollama · ready' : 'offline'}</span>
          </div>
        </div>
      </header>

      {/* Main Studio Workspace */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
        {/* Left Column: Generator & Episode Library (5 cols) */}
        <div className="lg:col-span-5 border-r border-border/80 p-5 flex flex-col bg-panel/30 overflow-y-auto space-y-5">
          {/* Generator Card */}
          <div className="glass-card rounded-2xl p-4.5 border border-border/80 shadow-card space-y-3.5">
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-semibold text-textMain flex items-center gap-1.5">
                <Mic size={14} className="text-accent" />
                <span>Create New Episode</span>
              </span>
              <span className="text-[11px] text-accent font-mono font-medium">Dual-Voice Explainer</span>
            </div>

            <div className="space-y-1.5">
              <label className="text-[11.5px] text-textMuted font-medium">Topic or Question:</label>
              <input
                type="text"
                value={topicInput}
                onChange={(e) => setTopicInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
                placeholder="e.g. How do vector databases enable semantic search?"
                className="w-full text-xs px-3.5 py-2.5 rounded-xl glass-panel text-textMain outline-none focus:border-accent/60 transition-colors placeholder:text-textFaint"
              />
            </div>

            {/* Quick Suggestions */}
            <div className="space-y-1.5">
              <span className="text-[10.5px] text-textFaint font-mono uppercase tracking-wider">
                Chapter Suggestions:
              </span>
              <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto pr-1">
                {CHAPTER_SUGGESTIONS.map((ch, idx) => (
                  <button
                    key={idx}
                    onClick={() => setTopicInput(ch)}
                    className="text-[11px] px-2.5 py-1 rounded-lg border border-border/70 glass-panel text-textMuted hover:text-accent hover:border-accent/40 transition-all text-left truncate cursor-pointer shadow-subtle"
                  >
                    {ch}
                  </button>
                ))}
              </div>
            </div>

            {/* Turns selector */}
            <div className="space-y-2 pt-1">
              <div className="flex items-center justify-between text-[11.5px]">
                <span className="text-textMuted font-medium">
                  Dialogue Length: <span className="font-mono text-accent font-bold">{numTurns} turns</span>
                </span>
                <span className="text-textFaint font-mono text-[10.5px]">
                  ~{Math.round(numTurns * 18)}s ({Math.round((numTurns * 18) / 60 * 10) / 10} min)
                </span>
              </div>

              {/* Quick Presets */}
              <div className="flex flex-wrap gap-1.5">
                {[6, 8, 12, 16, 20, 24].map((t) => (
                  <button
                    key={t}
                    onClick={() => setNumTurns(t)}
                    className={`px-2 py-1 text-[11px] rounded-lg border font-mono transition-all cursor-pointer ${
                      numTurns === t
                        ? 'bg-accent text-white border-accent shadow-sm'
                        : 'glass-panel border-border/80 text-textMuted hover:text-textMain'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>

              {/* Slider for custom length */}
              <input
                type="range"
                min="4"
                max="30"
                step="2"
                value={numTurns}
                onChange={(e) => setNumTurns(parseInt(e.target.value, 10))}
                className="w-full h-1.5 bg-border rounded-lg appearance-none cursor-pointer accent-accent"
              />
            </div>

            {/* Submit button */}
            <Button
              variant="primary"
              size="md"
              className="w-full justify-center"
              onClick={() => handleGenerate()}
              disabled={isGenerating || !topicInput.trim() || !ollama}
            >
              {isGenerating ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  <span>Recording Podcast...</span>
                </>
              ) : (
                <>
                  <Sparkles size={14} />
                  <span>Generate 2-Voice Podcast</span>
                </>
              )}
            </Button>

            {isGenerating && (
              <div className="p-3 rounded-xl bg-accentSoft/60 border border-accent/30 text-xs text-accent flex items-center gap-2 animate-pulse">
                <Loader2 size={13} className="animate-spin flex-shrink-0" />
                <span>{generationStep}</span>
              </div>
            )}

            {error && (
              <div className="p-3 rounded-xl bg-dangerSoft/60 border border-danger/30 text-xs text-danger flex items-center gap-2">
                <AlertCircle size={14} className="flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </div>

          {/* Episode Library */}
          <div className="flex-1 flex flex-col min-h-0 space-y-2.5">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-textFaint">
                Episode Library ({episodes.length})
              </h3>
              <button
                onClick={loadEpisodes}
                className="text-[11px] text-accent hover:underline cursor-pointer"
              >
                Refresh
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              {loadingEpisodes ? (
                <div className="text-center py-8 text-textFaint text-xs flex items-center justify-center gap-2">
                  <Loader2 size={14} className="animate-spin text-accent" />
                  <span>Loading episodes...</span>
                </div>
              ) : episodes.length === 0 ? (
                <div className="text-center py-10 glass-card rounded-2xl p-4 text-textMuted text-xs">
                  <Headphones size={24} className="mx-auto mb-2 text-textFaint opacity-60" />
                  <p className="font-semibold text-textMain mb-1">No episodes recorded yet</p>
                  <p className="text-textFaint">Generate your first two-voice study episode above!</p>
                </div>
              ) : (
                episodes.map((ep) => {
                  const isSelected = activeEpisode?.id === ep.id;
                  return (
                    <div
                      key={ep.id}
                      onClick={() => {
                        setActiveEpisode(ep);
                        if (audioRef.current) {
                          audioRef.current.pause();
                          setIsPlaying(false);
                        }
                      }}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-accentSoft/70 border-accent/50 shadow-md shadow-accent/10'
                          : 'glass-card border-border/80 hover:border-accent/40'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1 space-y-1">
                          <h4 className="text-[13px] font-semibold text-textMain truncate">
                            {ep.title}
                          </h4>
                          <div className="flex items-center gap-2 text-[11px] text-textMuted">
                            <span className="flex items-center gap-1 font-mono">
                              <Clock size={11} />
                              ~{Math.round(ep.total_duration_s || 0)}s
                            </span>
                            <span>·</span>
                            <span className="font-mono">{ep.turns?.length || 0} turns</span>
                          </div>
                        </div>
                        <div className={`p-1.5 rounded-lg ${isSelected ? 'text-accent' : 'text-textFaint'}`}>
                          {isSelected && isPlaying ? <Pause size={14} /> : <Play size={14} />}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Studio Player & Synced Dialogue Transcript (7 cols) */}
        <div className="lg:col-span-7 flex flex-col h-full bg-background/50 overflow-hidden">
          {activeEpisode ? (
            <>
              {/* Speaker HUD (Avatars) */}
              <div className="px-6 py-4 border-b border-border/80 bg-panel/50 backdrop-blur-md">
                <div className="flex items-center justify-around gap-4">
                  {/* Speaker A: Alex (Host / Tutor) */}
                  <div
                    className={`flex items-center gap-3 p-3 rounded-2xl border transition-all ${
                      currentSpeaker === 'HOST' && isPlaying
                        ? 'bg-accentSoft/60 border-accent shadow-md shadow-accent/20 scale-[1.03]'
                        : 'glass-panel border-border/60 opacity-80'
                    }`}
                  >
                    <div className="relative">
                      <div className="w-11 h-11 rounded-full bg-gradient-to-tr from-accent to-sky-500 text-white flex items-center justify-center text-lg shadow-sm">
                        👨‍🏫
                      </div>
                      {currentSpeaker === 'HOST' && isPlaying && (
                        <span className="absolute -bottom-1 -right-1 flex h-3.5 w-3.5">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
                          <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-accent text-[8px] text-white items-center justify-center font-bold">
                            ●
                          </span>
                        </span>
                      )}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-textMain">Alex (Host)</div>
                      <div className="text-[11px] text-accent font-medium">Tutor</div>
                      {currentSpeaker === 'HOST' && isPlaying && (
                        <span className="text-[10px] text-success font-semibold">Speaking now…</span>
                      )}
                    </div>
                  </div>

                  <div className="text-textFaint font-bold text-sm">vs</div>

                  {/* Speaker B: Sam (Student / Learner) */}
                  <div
                    className={`flex items-center gap-3 p-3 rounded-2xl border transition-all ${
                      currentSpeaker === 'STUDENT' && isPlaying
                        ? 'bg-sky-500/15 border-sky-400 shadow-md shadow-sky-500/20 scale-[1.03]'
                        : 'glass-panel border-border/60 opacity-80'
                    }`}
                  >
                    <div className="relative">
                      <div className="w-11 h-11 rounded-full bg-gradient-to-tr from-sky-400 to-indigo-500 text-white flex items-center justify-center text-lg shadow-sm">
                        👩‍🎓
                      </div>
                      {currentSpeaker === 'STUDENT' && isPlaying && (
                        <span className="absolute -bottom-1 -right-1 flex h-3.5 w-3.5">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75" />
                          <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-sky-400 text-[8px] text-white items-center justify-center font-bold">
                            ●
                          </span>
                        </span>
                      )}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-textMain">Sam (Student)</div>
                      <div className="text-[11px] text-sky-400 font-medium">Learner</div>
                      {currentSpeaker === 'STUDENT' && isPlaying && (
                        <span className="text-[10px] text-success font-semibold">Speaking now…</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Synced Transcript View */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-textFaint">
                    Interactive Transcript (Click any turn to jump)
                  </span>
                  {activeEpisode.sources?.length > 0 && (
                    <span className="text-[11px] text-textMuted truncate max-w-xs">
                      {activeEpisode.sources.join(', ')}
                    </span>
                  )}
                </div>

                <div className="space-y-3">
                  {activeEpisode.turns?.map((turn, idx) => {
                    const isTurnActive = idx === activeTurnIndex;
                    const isHost = (turn.speaker || '').toUpperCase() === 'HOST';
                    const turnText = turn.text || turn.line || '';

                    return (
                      <div
                        key={idx}
                        onClick={() => seekTo(turn.start_time_s || 0)}
                        className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                          isTurnActive
                            ? isHost
                              ? 'bg-accentSoft/40 border-accent/80 shadow-md ring-1 ring-accent/30'
                              : 'bg-sky-500/10 border-sky-400/80 shadow-md ring-1 ring-sky-400/30'
                            : 'glass-card border-border/80 hover:border-accent/40'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <span
                              className={`px-2 py-0.5 rounded text-[10.5px] font-bold uppercase tracking-wider ${
                                isHost
                                  ? 'bg-accent/20 text-accent'
                                  : 'bg-sky-500/20 text-sky-400'
                              }`}
                            >
                              {isHost ? '🎙️ Alex (Host)' : '🎓 Sam (Student)'}
                            </span>
                            {isTurnActive && isPlaying && (
                              <span className="text-[10px] text-success font-semibold animate-pulse">
                                ● Playing
                              </span>
                            )}
                          </div>
                          <span className="text-[11px] font-mono text-textFaint">
                            {formatTime(turn.start_time_s || 0)}
                          </span>
                        </div>
                        <p className={`text-[13px] leading-relaxed ${isTurnActive ? 'text-textMain font-medium' : 'text-textMuted'}`}>
                          {turnText}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Bottom Audio Player Bar */}
              <div className="p-4 border-t border-border/80 bg-panel/70 backdrop-blur-md">
                {audioSrc && (
                  <audio
                    ref={audioRef}
                    src={audioSrc}
                    onTimeUpdate={handleTimeUpdate}
                    onLoadedMetadata={() => {
                      if (audioRef.current) {
                        setDuration(audioRef.current.duration || activeEpisode.total_duration_s || 0);
                      }
                    }}
                    onPlay={() => setIsPlaying(true)}
                    onPause={() => setIsPlaying(false)}
                    onEnded={() => setIsPlaying(false)}
                  />
                )}

                {/* Scrubber Bar */}
                <div className="space-y-1.5 mb-3">
                  <div className="flex items-center justify-between text-xs font-mono text-textMuted">
                    <span>{formatTime(currentTime)}</span>
                    <span>{formatTime(duration || activeEpisode.total_duration_s)}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max={duration || activeEpisode.total_duration_s || 100}
                    step="0.1"
                    value={currentTime}
                    onChange={(e) => seekTo(parseFloat(e.target.value))}
                    className="w-full h-1.5 bg-border rounded-lg appearance-none cursor-pointer accent-accent"
                  />
                </div>

                {/* Controls */}
                <div className="flex items-center justify-between flex-wrap gap-2">
                  {/* Left: Speed selector */}
                  <div className="flex items-center gap-1">
                    <span className="text-[11px] text-textMuted mr-1">Speed:</span>
                    {[1, 1.25, 1.5, 2].map((rate) => (
                      <button
                        key={rate}
                        onClick={() => handleSpeedChange(rate)}
                        className={`px-2 py-0.5 text-[11px] font-mono rounded-md transition-all cursor-pointer ${
                          playbackRate === rate
                            ? 'bg-accent text-white font-bold'
                            : 'text-textMuted hover:text-textMain bg-panelHover border border-border/60'
                        }`}
                      >
                        {rate}x
                      </button>
                    ))}
                  </div>

                  {/* Center: Playback buttons */}
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => seekTo(currentTime - 10)}
                      title="Skip 10s back"
                      className="p-2 text-textMuted hover:text-textMain hover:bg-panelHover rounded-lg transition-colors text-xs font-mono cursor-pointer"
                    >
                      ⏪ 10s
                    </button>

                    <button
                      onClick={togglePlay}
                      className="w-11 h-11 rounded-full bg-accent hover:bg-accentDim text-white flex items-center justify-center text-sm shadow-md shadow-accent/25 transition-transform active:scale-95 cursor-pointer"
                    >
                      {isPlaying ? <Pause size={16} /> : <Play size={16} className="ml-0.5" />}
                    </button>

                    <button
                      onClick={() => seekTo(currentTime + 10)}
                      title="Skip 10s forward"
                      className="p-2 text-textMuted hover:text-textMain hover:bg-panelHover rounded-lg transition-colors text-xs font-mono cursor-pointer"
                    >
                      10s ⏩
                    </button>
                  </div>

                  {/* Right: Download MP3 */}
                  <div>
                    {audioSrc && (
                      <a
                        href={audioSrc}
                        download={`MentorOS_${activeEpisode.topic || 'podcast'}.mp3`}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg glass-panel text-textMuted hover:text-textMain border border-border/80 text-xs font-medium transition-colors"
                      >
                        <Download size={13} />
                        <span>MP3</span>
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-textMuted">
              <Headphones size={36} className="mb-3 text-accent opacity-70" />
              <h4 className="text-sm font-semibold text-textMain mb-1">No Episode Selected</h4>
              <p className="text-xs max-w-sm text-textMuted">
                Select an episode from the left or generate a new two-voice podcast explainer from your notes.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
