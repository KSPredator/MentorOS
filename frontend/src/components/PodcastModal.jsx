import React, { useState, useEffect, useRef } from 'react';
import { generatePodcast, getPodcastList, getPodcastAudioUrl } from '../api';

const CHAPTER_SUGGESTIONS = [
  "Chapter 1: Introduction to Foundation Models & AI Engineering",
  "Chapter 2: Prompt Engineering & In-Context Learning",
  "Chapter 3: Retrieval-Augmented Generation (RAG) Architecture",
  "Chapter 4: Vector Databases, Embeddings & Semantic Search",
  "Chapter 5: Evaluation Frameworks & Hallucination Gating",
  "Chapter 6: Memory Systems, Reflection & Agentic Loops",
  "Chapter 7: Fine-Tuning, LoRA & Model Adaptation",
  "Chapter 8: Serving, Quantization & Latency Optimization",
];

export default function PodcastModal({ isOpen, onClose, initialTopic = '', initialContext = null }) {
  const [topicInput, setTopicInput] = useState('');
  const [numTurns, setNumTurns] = useState(8);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState('');
  const [error, setError] = useState(null);

  const [episodes, setEpisodes] = useState([]);
  const [activeEpisode, setActiveEpisode] = useState(null);

  // Audio Player state
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [activeTurnIndex, setActiveTurnIndex] = useState(0);

  // Load episodes on modal open
  useEffect(() => {
    if (isOpen) {
      loadEpisodes();
      if (initialTopic) {
        setTopicInput(initialTopic);
      }
    }
  }, [isOpen, initialTopic]);

  // Handle auto-generation if initialContext was passed
  useEffect(() => {
    if (isOpen && initialTopic && initialContext && !activeEpisode && !isGenerating) {
      handleGenerate(initialTopic, initialContext);
    }
  }, [isOpen, initialTopic, initialContext]);

  const loadEpisodes = async () => {
    try {
      const list = await getPodcastList();
      setEpisodes(list);
      if (list.length > 0 && !activeEpisode) {
        setActiveEpisode(list[0]);
      }
    } catch (err) {
      console.warn("Failed to load podcast episodes:", err);
    }
  };

  const handleGenerate = async (customTopic = null, customContext = null) => {
    const targetTopic = customTopic || topicInput.trim();
    if (!targetTopic) return;

    setIsGenerating(true);
    setError(null);
    setGenerationStep('Retrieving material and drafting 2-person dialogue script...');

    try {
      const timer = setTimeout(() => {
        setGenerationStep('Synthesizing dual-voice neural audio (Host & Student)...');
      }, 4000);

      const episode = await generatePodcast(targetTopic, customContext || null, numTurns);
      clearTimeout(timer);
      
      setActiveEpisode(episode);
      setEpisodes(prev => [episode, ...prev.filter(e => e.id !== episode.id)]);
      setIsGenerating(false);
      setGenerationStep('');
      
      // Auto-play new episode
      setTimeout(() => {
        if (audioRef.current) {
          audioRef.current.play().catch(() => {});
        }
      }, 300);
    } catch (err) {
      setIsGenerating(false);
      setGenerationStep('');
      setError(err.message || 'Failed to generate podcast.');
    }
  };

  // Sync audio time and active dialogue turn
  const handleTimeUpdate = () => {
    if (!audioRef.current) return;
    const time = audioRef.current.currentTime;
    setCurrentTime(time);
    
    if (activeEpisode && activeEpisode.turns) {
      // Find turn by matching cumulative start times
      let idx = 0;
      for (let i = 0; i < activeEpisode.turns.length; i++) {
        const turn = activeEpisode.turns[i];
        if (time >= (turn.start_time_s || 0)) {
          idx = i;
        }
      }
      setActiveTurnIndex(idx);
    }
  };

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch(e => console.warn(e));
    }
  };

  const seekTo = (seconds) => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = Math.max(0, Math.min(seconds, duration));
  };

  const handleSpeedChange = (rate) => {
    setPlaybackRate(rate);
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  };

  const formatTime = (secs) => {
    if (!secs || isNaN(secs)) return "00:00";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  if (!isOpen) return null;

  const currentSpeaker = activeEpisode?.turns?.[activeTurnIndex]?.speaker || "HOST";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="bg-[#0f172a] border border-slate-700/60 rounded-2xl w-full max-w-5xl h-[88vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Top Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/60">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center text-xl shadow-lg shadow-indigo-500/20">
              🎧
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-lg font-bold text-white tracking-wide">MentorOS Podcast Studio</h2>
                <span className="px-2 py-0.5 text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-full">
                  Two-Voice Explainer
                </span>
              </div>
              <p className="text-xs text-slate-400">Interactive educational dialogues powered by dual neural TTS</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Main Content Body */}
        <div className="flex-1 grid grid-cols-1 md:grid-cols-12 overflow-hidden">
          
          {/* Left Panel: Creator & Episode Library (5 cols) */}
          <div className="md:col-span-5 border-r border-slate-800/80 p-5 flex flex-col bg-slate-900/30 overflow-y-auto space-y-6">
            
            {/* Quick Generator Box */}
            <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 space-y-3">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center justify-between">
                <span>🎙️ Generate New Episode</span>
                <span className="text-xs text-indigo-400 font-normal">Local Neural TTS</span>
              </h3>

              <div className="space-y-2">
                <label className="text-xs text-slate-400">Select Chapter or Enter Topic:</label>
                <input
                  type="text"
                  value={topicInput}
                  onChange={(e) => setTopicInput(e.target.value)}
                  placeholder="e.g. Chapter 3: RAG Architecture or LoRA Fine-Tuning"
                  className="w-full bg-slate-950 border border-slate-700/70 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 placeholder-slate-500"
                />
              </div>

              {/* Suggestions */}
              <div className="space-y-1">
                <span className="text-[11px] text-slate-500 font-medium">Quick Suggestions:</span>
                <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto pr-1">
                  {CHAPTER_SUGGESTIONS.map((ch, idx) => (
                    <button
                      key={idx}
                      onClick={() => setTopicInput(ch)}
                      className="text-[11px] px-2 py-1 bg-slate-900 hover:bg-slate-750 text-slate-300 hover:text-indigo-300 border border-slate-700/50 rounded-md text-left truncate max-w-full transition-colors"
                    >
                      {ch.split(':')[0]}
                    </button>
                  ))}
                </div>
              </div>

              {/* Dialogue Length Options */}
              <div className="flex items-center justify-between pt-1">
                <span className="text-xs text-slate-400">Turns:</span>
                <div className="flex space-x-1.5">
                  {[6, 8, 12].map(t => (
                    <button
                      key={t}
                      onClick={() => setNumTurns(t)}
                      className={`px-2.5 py-1 text-xs rounded-md border transition-all ${
                        numTurns === t
                          ? 'bg-indigo-600 border-indigo-500 text-white font-medium'
                          : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {t} turns
                    </button>
                  ))}
                </div>
              </div>

              {/* Generate Button */}
              <button
                onClick={() => handleGenerate()}
                disabled={isGenerating || !topicInput.trim()}
                className="w-full py-2.5 px-4 bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 disabled:opacity-50 text-white font-medium text-xs rounded-lg shadow-lg shadow-indigo-500/20 transition-all flex items-center justify-center space-x-2"
              >
                {isGenerating ? (
                  <>
                    <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                    <span>Recording Podcast...</span>
                  </>
                ) : (
                  <>
                    <span>✨ Generate 2-Voice Podcast</span>
                  </>
                )}
              </button>

              {isGenerating && (
                <div className="p-2.5 bg-indigo-950/40 border border-indigo-800/40 rounded-lg text-xs text-indigo-300 animate-pulse">
                  {generationStep}
                </div>
              )}

              {error && (
                <div className="p-2.5 bg-red-950/40 border border-red-800/40 rounded-lg text-xs text-red-300">
                  {error}
                </div>
              )}
            </div>

            {/* Previous Episodes Library */}
            <div className="flex-1 flex flex-col space-y-2 min-h-0">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Episode Library ({episodes.length})
              </h3>
              
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {episodes.length === 0 ? (
                  <div className="text-center py-8 text-slate-500 text-xs">
                    No podcast episodes recorded yet.<br/>Generate your first one above!
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
                        className={`p-3 rounded-xl border cursor-pointer transition-all ${
                          isSelected
                            ? 'bg-indigo-950/50 border-indigo-500/60 shadow-md shadow-indigo-950/50'
                            : 'bg-slate-800/20 border-slate-700/40 hover:bg-slate-800/50'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="space-y-1 overflow-hidden pr-2">
                            <h4 className="text-xs font-semibold text-slate-200 truncate">
                              {ep.title}
                            </h4>
                            <div className="flex items-center space-x-2 text-[11px] text-slate-400">
                              <span>⏱️ ~{Math.round(ep.total_duration_s || 0)}s</span>
                              <span>•</span>
                              <span>{ep.turns?.length || 0} turns</span>
                            </div>
                          </div>
                          <span className="text-base">{isSelected ? '▶️' : '🎙️'}</span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

          </div>

          {/* Right Panel: Studio Player & Synced Dialogue Transcript (7 cols) */}
          <div className="md:col-span-7 flex flex-col h-full bg-[#0b1120] overflow-hidden">
            
            {activeEpisode ? (
              <>
                {/* Visual Speaker HUD (Avatars) */}
                <div className="px-6 py-4 border-b border-slate-800/80 bg-slate-900/40">
                  <div className="flex items-center justify-around">
                    
                    {/* Speaker A: Alex (Host) */}
                    <div className={`flex items-center space-x-3 p-2.5 rounded-xl border transition-all ${
                      currentSpeaker === 'HOST' && isPlaying
                        ? 'bg-indigo-950/60 border-indigo-500 shadow-lg shadow-indigo-500/20 scale-105'
                        : 'bg-slate-800/20 border-slate-700/30 opacity-70'
                    }`}>
                      <div className="relative">
                        <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-indigo-500 to-blue-600 flex items-center justify-center text-xl shadow-md">
                          👨‍🏫
                        </div>
                        {currentSpeaker === 'HOST' && isPlaying && (
                          <span className="absolute -bottom-1 -right-1 flex h-4 w-4">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-4 w-4 bg-indigo-500 items-center justify-center text-[9px] text-white">🎙️</span>
                          </span>
                        )}
                      </div>
                      <div>
                        <div className="text-xs font-bold text-slate-200">Alex (Host)</div>
                        <div className="text-[11px] text-indigo-400">Enthusiastic Tutor</div>
                        {currentSpeaker === 'HOST' && isPlaying && (
                          <span className="text-[10px] text-emerald-400 font-medium">Speaking now...</span>
                        )}
                      </div>
                    </div>

                    <div className="text-slate-600 font-bold text-lg">⚡</div>

                    {/* Speaker B: Sam (Student) */}
                    <div className={`flex items-center space-x-3 p-2.5 rounded-xl border transition-all ${
                      currentSpeaker === 'STUDENT' && isPlaying
                        ? 'bg-cyan-950/60 border-cyan-500 shadow-lg shadow-cyan-500/20 scale-105'
                        : 'bg-slate-800/20 border-slate-700/30 opacity-70'
                    }`}>
                      <div className="relative">
                        <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-cyan-500 to-teal-600 flex items-center justify-center text-xl shadow-md">
                          👩‍🎓
                        </div>
                        {currentSpeaker === 'STUDENT' && isPlaying && (
                          <span className="absolute -bottom-1 -right-1 flex h-4 w-4">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-4 w-4 bg-cyan-500 items-center justify-center text-[9px] text-white">🎧</span>
                          </span>
                        )}
                      </div>
                      <div>
                        <div className="text-xs font-bold text-slate-200">Sam (Student)</div>
                        <div className="text-[11px] text-cyan-400">Curious Learner</div>
                        {currentSpeaker === 'STUDENT' && isPlaying && (
                          <span className="text-[10px] text-emerald-400 font-medium">Speaking now...</span>
                        )}
                      </div>
                    </div>

                  </div>
                </div>

                {/* Synced Transcript View */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Interactive Transcript (Click turn to seek)
                    </span>
                    {activeEpisode.sources?.length > 0 && (
                      <span className="text-[11px] text-slate-400">
                        Sources: {activeEpisode.sources.join(', ')}
                      </span>
                    )}
                  </div>

                  <div className="space-y-3">
                    {activeEpisode.turns?.map((turn, idx) => {
                      const isTurnActive = idx === activeTurnIndex;
                      const isHost = turn.speaker === 'HOST';

                      return (
                        <div
                          key={idx}
                          onClick={() => seekTo(turn.start_time_s || 0)}
                          className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                            isTurnActive
                              ? isHost
                                ? 'bg-indigo-950/40 border-indigo-500/80 shadow-md ring-1 ring-indigo-500/40'
                                : 'bg-cyan-950/40 border-cyan-500/80 shadow-md ring-1 ring-cyan-500/40'
                              : 'bg-slate-800/10 border-slate-800 hover:bg-slate-800/30'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <div className="flex items-center space-x-2">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                isHost ? 'bg-indigo-500/20 text-indigo-300' : 'bg-cyan-500/20 text-cyan-300'
                              }`}>
                                {isHost ? '🎙️ Alex (Host)' : '🎓 Sam (Student)'}
                              </span>
                              {isTurnActive && isPlaying && (
                                <span className="text-[10px] text-emerald-400 font-medium animate-pulse">● Playing</span>
                              )}
                            </div>
                            <span className="text-[11px] font-mono text-slate-500">
                              {formatTime(turn.start_time_s || 0)}
                            </span>
                          </div>
                          <p className={`text-xs leading-relaxed ${
                            isTurnActive ? 'text-slate-100 font-medium' : 'text-slate-300'
                          }`}>
                            {turn.text}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Bottom Audio Player Controls Bar */}
                <div className="p-4 border-t border-slate-800 bg-slate-900/80 backdrop-blur-md">
                  <audio
                    ref={audioRef}
                    src={getPodcastAudioUrl(activeEpisode.audio_filename)}
                    onTimeUpdate={handleTimeUpdate}
                    onLoadedMetadata={() => {
                      if (audioRef.current) {
                        setDuration(audioRef.current.duration || activeEpisode.total_duration_s);
                      }
                    }}
                    onPlay={() => setIsPlaying(true)}
                    onPause={() => setIsPlaying(false)}
                    onEnded={() => setIsPlaying(false)}
                  />

                  {/* Scrubber Bar */}
                  <div className="space-y-1.5 mb-3">
                    <div className="flex items-center justify-between text-xs font-mono text-slate-400">
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
                      className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500 hover:accent-indigo-400"
                    />
                  </div>

                  {/* Playback Button Controls */}
                  <div className="flex items-center justify-between">
                    
                    {/* Left: Speed selector */}
                    <div className="flex items-center space-x-1">
                      <span className="text-[11px] text-slate-400 mr-1">Speed:</span>
                      {[1, 1.25, 1.5, 2].map(rate => (
                        <button
                          key={rate}
                          onClick={() => handleSpeedChange(rate)}
                          className={`px-2 py-0.5 text-[11px] rounded transition-all ${
                            playbackRate === rate
                              ? 'bg-indigo-600 text-white font-bold'
                              : 'text-slate-400 hover:text-white bg-slate-800'
                          }`}
                        >
                          {rate}x
                        </button>
                      ))}
                    </div>

                    {/* Center: Controls */}
                    <div className="flex items-center space-x-3">
                      <button
                        onClick={() => seekTo(currentTime - 10)}
                        title="Skip 10s back"
                        className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors text-sm"
                      >
                        ⏪ 10s
                      </button>

                      <button
                        onClick={togglePlay}
                        className="w-12 h-12 rounded-full bg-gradient-to-r from-indigo-500 to-cyan-500 hover:from-indigo-400 hover:to-cyan-400 text-white flex items-center justify-center text-lg shadow-lg shadow-indigo-500/30 transition-transform active:scale-95"
                      >
                        {isPlaying ? '⏸️' : '▶️'}
                      </button>

                      <button
                        onClick={() => seekTo(currentTime + 10)}
                        title="Skip 10s forward"
                        className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors text-sm"
                      >
                        10s ⏩
                      </button>
                    </div>

                    {/* Right: Download MP3 */}
                    <div>
                      <a
                        href={getPodcastAudioUrl(activeEpisode.audio_filename)}
                        download={`MentorOS_${activeEpisode.topic}.mp3`}
                        className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white text-xs rounded-lg transition-colors border border-slate-700"
                      >
                        <span>⬇️</span>
                        <span>MP3</span>
                      </a>
                    </div>

                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-500">
                <div className="text-4xl mb-3">🎙️</div>
                <h4 className="text-sm font-semibold text-slate-300 mb-1">No Episode Selected</h4>
                <p className="text-xs max-w-sm">Select an episode from the left or generate a new two-voice podcast explainer from your notes.</p>
              </div>
            )}

          </div>

        </div>

      </div>
    </div>
  );
}
