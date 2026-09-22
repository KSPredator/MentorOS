import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { ListChecks, Trophy, RotateCcw, Sparkles, CheckCircle2, ArrowRight } from 'lucide-react';
import { useChat } from '../../stores/chat';
import { useUI } from '../../stores/ui';
import Button from '../ui/Button';
import { toast } from 'sonner';

/**
 * Interactive quiz card with option selections, score presentation, and memory update feedback.
 */
export default function QuizCard({ message }) {
  const quiz = message?.meta?.quiz;
  const submitQuiz = useChat((s) => s.submitQuiz);
  const sendMessage = useChat((s) => s.sendMessage);
  const confirm = useUI((s) => s.confirm);

  const questions = quiz?.questions || [];
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const allAnswered = useMemo(
    () =>
      questions.length > 0 &&
      questions.filter((_, qi) => answers[qi] != null).length === questions.length,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [questions.length, answers],
  );

  if (!questions.length) {
    return (
      <div className="glass-card rounded-2xl p-5 text-sm text-textMuted">
        Quiz could not be generated — try again with different documents.
      </div>
    );
  }

  const onSelect = (qidx, optIdx) => {
    if (result) return;
    setAnswers((a) => ({ ...a, [qidx]: optIdx }));
  };

  const onSubmit = async () => {
    if (!allAnswered || submitting) return;
    setSubmitting(true);
    try {
      const positionAnswers = questions.map((_, qidx) => answers[qidx] ?? -1);
      const res = await submitQuiz(message.id, positionAnswers);
      setResult(res);
      toast.success(`Quiz scored ${res.score}/${res.total}`);
    } catch (e) {
      toast.error(e?.message || 'Failed to submit quiz');
    } finally {
      setSubmitting(false);
    }
  };

  const onRetake = () => {
    confirm({
      title: 'Retake quiz',
      message: 'Your previous score is already recorded. Start a fresh attempt?',
      confirmLabel: 'Retake',
      onConfirm: () => {
        setAnswers({});
        setResult(null);
      },
    });
  };

  if (result) {
    const pct = Math.round((result.score / result.total) * 100);
    const isPassing = pct >= 70;
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-card rounded-2xl overflow-hidden shadow-card"
      >
        <div className="p-6 text-center">
          <motion.div
            initial={{ scale: 0.8, rotate: -10 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            className="w-16 h-16 rounded-2xl mx-auto mb-3.5 flex items-center justify-center shadow-md"
            style={{
              background: isPassing ? 'var(--color-successSoft)' : 'var(--color-warningSoft)',
              color: isPassing ? 'var(--color-success)' : 'var(--color-warning)',
            }}
          >
            <Trophy size={28} strokeWidth={1.8} />
          </motion.div>
          <div className="font-display text-3xl font-extrabold text-textMain mb-1">
            {result.score} / {result.total}
          </div>
          <div
            className="text-sm font-semibold mb-2"
            style={{ color: isPassing ? 'var(--color-success)' : 'var(--color-warning)' }}
          >
            {pct}% Mastery Achieved
          </div>
          {result.feedback && (
            <p className="text-[13.5px] text-textMain/90 mt-2 max-w-md mx-auto leading-relaxed bg-panel/70 p-3.5 rounded-xl border border-border/70">
              {result.feedback}
            </p>
          )}
          {result.memory_updates && result.memory_updates.length > 0 && (
            <div className="inline-flex items-center gap-1.5 mt-3.5 text-[11px] font-mono px-3 py-1.5 rounded-full bg-successSoft text-success border border-success/25">
              <Sparkles size={12} />
              Saved to learning memory: +{result.memory_updates.length} concept updates
            </div>
          )}
        </div>
        <div className="flex gap-2.5 px-6 pb-6">
          <Button variant="secondary" className="flex-1" onClick={onRetake}>
            <RotateCcw size={13} />
            Retake Quiz
          </Button>
          <Button
            variant="primary"
            className="flex-1"
            onClick={() => sendMessage('Explain the questions I missed or got wrong in depth')}
          >
            <span>Review Mistakes</span>
            <ArrowRight size={13} />
          </Button>
        </div>
      </motion.div>
    );
  }

  return (
    <div className="glass-card rounded-2xl overflow-hidden shadow-card">
      <div className="flex items-center gap-2.5 px-4.5 py-3.5 border-b border-border/80 bg-accentSoft/60">
        <div className="w-6 h-6 rounded-lg bg-accent text-white flex items-center justify-center shadow-sm">
          <ListChecks size={13} />
        </div>
        <span className="text-[13.5px] font-bold text-textMain">Active Recall Quiz</span>
        <span className="text-[11px] font-mono text-textMuted ml-auto bg-panel px-2 py-0.5 rounded-md border border-border">
          {Object.keys(answers).length}/{questions.length} answered
        </span>
      </div>

      <div className="p-5 space-y-4.5">
        {questions.map((q, qi) => (
          <QuestionBlock
            key={qi}
            index={qi + 1}
            question={q}
            selected={answers[qi]}
            onSelect={(optIdx) => onSelect(qi, optIdx)}
          />
        ))}
      </div>

      <div className="px-5 pb-5">
        <Button
          variant="primary"
          size="lg"
          className="w-full"
          disabled={!allAnswered || submitting}
          onClick={onSubmit}
        >
          {submitting ? 'Scoring Answers…' : 'Submit Answers'}
        </Button>
        {!allAnswered && (
          <p className="text-[11.5px] text-textFaint text-center mt-2">
            Select an answer for each question to submit
          </p>
        )}
      </div>
    </div>
  );
}

function QuestionBlock({ index, question, selected, onSelect }) {
  const options = question?.options || [];
  return (
    <div>
      <div className="flex items-start gap-2.5 mb-2.5">
        <span className="w-5 h-5 rounded-md bg-accentSoft text-accent font-mono text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
          {index}
        </span>
        <p className="text-[14px] font-semibold text-textMain leading-snug">
          {question.question || question.text}
        </p>
      </div>
      <div className="space-y-2 pl-7.5">
        {options.map((opt, i) => {
          const letter = String.fromCharCode(65 + i);
          const active = selected === i;
          return (
            <motion.button
              key={i}
              whileTap={{ scale: 0.99 }}
              onClick={() => onSelect(i)}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl border text-left text-[13px] transition-all cursor-pointer shadow-subtle
                ${
                  active
                    ? 'border-accent bg-accentSoft text-textMain font-medium shadow-sm'
                    : 'border-border/80 bg-panel hover:border-borderStrong text-textMuted hover:text-textMain'
                }`}
              aria-pressed={active}
            >
              <span
                className={`w-5 h-5 rounded-full border flex items-center justify-center font-mono text-[10px] font-bold flex-shrink-0 transition-colors ${
                  active
                    ? 'border-accent bg-accent text-white'
                    : 'border-borderStrong text-textFaint bg-background'
                }`}
              >
                {active ? <CheckCircle2 size={12} /> : letter}
              </span>
              <span className="flex-1 leading-snug">{opt}</span>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
