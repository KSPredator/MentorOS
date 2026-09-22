import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Mic, Copy, Check, Clock, Radio, Volume2, Play, Pause, Download, FastForward } from 'lucide-react';
import { toast } from 'sonner';

/**
 * Enhanced podcast preview card with real dual-voice audio player and synced speaker turns.
 */
export default function PodcastCard({ script, audioUrl }) {
  const [copied, setCopied] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const audioRef = useRef(null);

  // Extract structured script & audio URL
  const scriptData = Array.isArray(script) ? script : (script?.podcast_script || script?.turns || []);
  const text = typeof script === 'string'
    ? script
    : script?.content || scriptData.map(t => `${t.speaker || 'SPEAKER'}: ${t.line || t.text}`).join('\n\n');
  
  const effectiveAudioUrl = audioUrl || script?.podcast_audio_url || script?.audio_url || null;
  const title = script?.title || 'Two-Voice Study Podcast';
  const minutes = Math.max(1, Math.round(text.split(/\s+/).length / 140));

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast.success('Script copied to clipboard');
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error('Copy failed');
    }
  };

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch((err) => toast.error('Playback error: ' + err.message));
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const seekTo = (secs) => {
    if (audioRef.current) {
      audioRef.current.currentTime = secs;
    }
  };

  const toggleSpeed = () => {
    const nextRate = playbackRate === 1 ? 1.25 : playbackRate === 1.25 ? 1.5 : 1;
    setPlaybackRate(nextRate);
    if (audioRef.current) {
      audioRef.current.playbackRate = nextRate;
    }
  };

  const formatTime = (secs) => {
    if (!secs || isNaN(secs)) return '00:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card rounded-2xl overflow-hidden shadow-card border border-border/80"
    >
      {/* Hidden HTML5 Audio Element */}
      {effectiveAudioUrl && (
        <audio
          ref={audioRef}
          src={effectiveAudioUrl}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={() => setDuration(audioRef.current?.duration || 0)}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
        />
      )}

      {/* Header Bar */}
      <div className="flex items-center gap-3 px-4.5 py-3.5 bg-accentSoft/60 border-b border-border/80">
        <div className="w-8.5 h-8.5 rounded-xl bg-gradient-to-tr from-accent to-sky-400 text-white flex items-center justify-center shadow-md shadow-accent/25">
          <Radio size={16} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[13.5px] font-bold text-textMain truncate">{title}</div>
          <div className="flex items-center gap-2 text-[11px] text-textMuted mt-0.5">
            <span className="flex items-center gap-1">
              <Clock size={11} />
              ~{minutes} min dialogue
            </span>
            <span>·</span>
            <span className="flex items-center gap-1 text-accent font-medium">
              <Volume2 size={11} />
              Alex (Tutor) & Sam (Learner)
            </span>
          </div>
        </div>

        {/* Animated wave bars */}
        <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-lg bg-panel/60 border border-border/50">
          {[12, 20, 16, 24, 14, 22, 10].map((h, i) => (
            <motion.span
              key={i}
              className={`w-1 rounded-full ${isPlaying ? 'bg-accent' : 'bg-accent/40'}`}
              style={{ height: h }}
              animate={isPlaying ? { height: [h * 0.4, h, h * 0.5] } : { height: h * 0.4 }}
              transition={{ repeat: Infinity, duration: 0.8 + (i % 3) * 0.2, ease: 'easeInOut' }}
            />
          ))}
        </div>

        <button
          onClick={copy}
          className="flex items-center gap-1.5 text-[11.5px] font-medium px-3 py-1.5 rounded-lg
            border border-border/80 glass-panel text-textMuted hover:text-textMain hover:bg-panelHover transition-all cursor-pointer shadow-subtle"
        >
          {copied ? <Check size={12} className="text-success" /> : <Copy size={12} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>

      {/* Embedded Playable Audio Controls */}
      {effectiveAudioUrl && (
        <div className="px-4.5 py-3 bg-panel/70 border-b border-border/60 flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <button
              onClick={togglePlay}
              className="w-9 h-9 rounded-full bg-accent hover:bg-accent/90 text-white flex items-center justify-center shadow-md transition-transform active:scale-95 flex-shrink-0"
              title={isPlaying ? 'Pause' : 'Play Podcast Audio'}
            >
              {isPlaying ? <Pause size={15} /> : <Play size={15} className="ml-0.5" />}
            </button>

            <div className="flex-1 flex flex-col gap-1">
              <input
                type="range"
                min="0"
                max={duration || 100}
                step="0.1"
                value={currentTime}
                onChange={(e) => seekTo(parseFloat(e.target.value))}
                className="w-full h-1.5 bg-border rounded-lg appearance-none cursor-pointer accent-accent"
              />
              <div className="flex justify-between text-[10.5px] font-mono text-textMuted">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>

            <button
              onClick={toggleSpeed}
              className="px-2 py-1 rounded bg-panelHover text-[11px] font-semibold text-textMuted hover:text-textMain border border-border"
              title="Change speed"
            >
              {playbackRate}x
            </button>

            <a
              href={effectiveAudioUrl}
              download="mentoros_podcast.mp3"
              className="p-2 rounded-lg bg-panelHover text-textMuted hover:text-textMain border border-border transition-colors"
              title="Download MP3"
            >
              <Download size={13} />
            </a>
          </div>
        </div>
      )}

      {/* Script Content / Structured Dialogue */}
      <div className="p-4.5">
        {scriptData.length > 0 ? (
          <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
            {scriptData.map((item, idx) => {
              const isHost = (item.speaker || '').toUpperCase() === 'HOST';
              return (
                <div
                  key={idx}
                  className={`p-3 rounded-xl border text-[13px] leading-relaxed transition-all ${
                    isHost
                      ? 'bg-accentSoft/30 border-accent/30 text-textMain'
                      : 'bg-panel/50 border-border text-textMain/90'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-[10.5px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                      isHost ? 'bg-accent/20 text-accent' : 'bg-sky-500/20 text-sky-400'
                    }`}>
                      {isHost ? '🎙️ Alex (Host)' : '🎓 Sam (Student)'}
                    </span>
                  </div>
                  <p>{item.line || item.text}</p>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-[13.5px] leading-relaxed text-textMain/90 whitespace-pre-wrap max-h-80 overflow-y-auto answer-md pr-1">
            {text}
          </div>
        )}

        <div className="mt-3.5 pt-3 border-t border-border/70 flex items-center justify-between text-[11px] text-textFaint">
          <span className="flex items-center gap-1.5">
            <Mic size={11} className="text-accent" />
            Generated from your local knowledge documents & dual neural TTS
          </span>
          <span className="font-mono text-[10px]">Phase 12</span>
        </div>
      </div>
    </motion.div>
  );
}
