import { useState } from "react";

import { api } from "../api";
import { Burst } from "../components/Celebrate";
import { Icon, SubjectIcon } from "../components/Icon";
import Markdown from "../components/Markdown";
import { isAnswered, QuestionBody, SolutionPanel } from "../components/Question";
import { Empty, ErrorMessage, Loader } from "../components/ui";
import { useApi } from "../hooks";
import { useI18n } from "../i18n";

// Reviews are graded on the server, exactly like a normal attempt; the client only shows the result.
function answerBody(answer) {
  return {
    choice_ids: answer.choice_ids || [],
    text: answer.text || "",
    numeric: answer.numeric === "" || answer.numeric === undefined ? null : answer.numeric,
  };
}

function Summary({ total, correct, dueLeft, xp, onExit, onAgain }) {
  const { t } = useI18n();
  const pct = total ? Math.round((correct / total) * 100) : 0;
  return (
    <div className="card review-summary" style={{ textAlign: "center" }}>
      <div className="score-ring" style={{ "--pct": pct }}>
        <div>
          {correct}/{total}
        </div>
        <Burst size={260} />
      </div>
      <h2 style={{ margin: "14px 0 4px" }}>{t("review.summaryTitle")}</h2>
      <p className="muted">{t("review.summaryBody", { correct, total })}</p>
      {xp > 0 && (
        <p className="with-icon" style={{ justifyContent: "center", color: "var(--success)" }}>
          <Icon name="zap" size={16} /> {t("review.earnedXp", { n: xp })}
        </p>
      )}
      <div className="row" style={{ justifyContent: "center", marginTop: 12 }}>
        {dueLeft > 0 && (
          <button className="btn" onClick={onAgain}>
            <Icon name="refresh" size={16} /> {t("review.keepGoing")}
          </button>
        )}
        <button className="btn btn-secondary" onClick={onExit}>
          {t("review.done")}
        </button>
      </div>
    </div>
  );
}

function Session({ due, onExit, onAgain }) {
  const { t } = useI18n();
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState({});
  const [graded, setGraded] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [tally, setTally] = useState({ correct: 0, xp: 0 });
  const [dueLeft, setDueLeft] = useState(null);
  const [done, setDone] = useState(false);

  const item = due[index];
  const total = due.length;

  async function check() {
    setBusy(true);
    setError(null);
    try {
      const res = await api(`/review/${item.id}/answer/`, { method: "POST", body: answerBody(answer) });
      setGraded(res);
      setDueLeft(res.due_count);
      setTally((s) => ({ correct: s.correct + (res.is_correct ? 1 : 0), xp: s.xp + (res.xp_gained || 0) }));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  function next() {
    if (index + 1 >= total) {
      setDone(true);
      return;
    }
    setIndex(index + 1);
    setAnswer({});
    setGraded(null);
    setError(null);
  }

  if (done) {
    return <Summary total={total} correct={tally.correct} dueLeft={dueLeft ?? 0} xp={tally.xp} onExit={onExit} onAgain={onAgain} />;
  }

  // After grading, show the solution on the question (right/wrong, correct options, the original explanation).
  const question = graded ? { ...item.question, solution: { ...graded.solution, is_correct: graded.is_correct } } : item.question;
  const progress = `${t("review.card", { n: index + 1, total })}`;

  return (
    <div className="quiz-shell">
      <div className="spread" style={{ marginBottom: 12 }}>
        <span className="pill">
          <SubjectIcon name={item.subject.icon} size={14} /> {item.subject.name}
        </span>
        <span className="small muted">{progress}</span>
      </div>
      <div className="progress" role="progressbar" aria-valuenow={index + 1} aria-valuemin={1} aria-valuemax={total} aria-label={progress} style={{ marginBottom: 14 }}>
        <span style={{ width: `${((index + (graded ? 1 : 0)) / total) * 100}%` }} />
      </div>
      <div className="card">
        <Markdown interactive={false}>{question.prompt}</Markdown>
        <QuestionBody question={question} answer={answer} onChange={(patch) => setAnswer((a) => ({ ...a, ...patch }))} locked={Boolean(graded) || busy} />
        {graded && (
          <>
            <SolutionPanel question={question} answer={answer} />
            <div className="small muted with-icon" style={{ marginTop: 10 }}>
              {graded.retired ? (
                <>
                  <Icon name="award" size={15} /> {t("review.mastered")}
                </>
              ) : graded.is_correct ? (
                <>
                  <Icon name="check" size={15} /> {t("review.movedUp")}
                </>
              ) : (
                <>
                  <Icon name="refresh" size={15} /> {t("review.tryAgainSoon")}
                </>
              )}
              {graded.xp_gained > 0 && (
                <span className="pill pill-success" style={{ marginLeft: 8 }}>
                  <Icon name="zap" size={13} /> {t("review.plusXp", { n: graded.xp_gained })}
                </span>
              )}
            </div>
          </>
        )}
        <ErrorMessage error={error} />
        <div className="spread" style={{ marginTop: 16 }}>
          <button className="btn btn-ghost" onClick={onExit}>
            {t("review.leave")}
          </button>
          {graded ? (
            <button className="btn" onClick={next}>
              {index + 1 >= total ? t("review.finish") : t("review.next")} <Icon name="next" size={16} />
            </button>
          ) : (
            <button className="btn btn-success" disabled={!isAnswered(item.question, answer) || busy} onClick={check}>
              {t("review.check")}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function Entry({ data, onStart }) {
  const { t } = useI18n();
  if (!data.total) {
    return (
      <Empty icon="brain">
        <strong>{t("review.emptyTitle")}</strong>
        <br />
        {t("review.emptyBody")}
      </Empty>
    );
  }
  const caughtUp = data.due_count === 0;
  return (
    <div className="card review-entry">
      <h2 className="title-with-icon">
        <Icon name="brain" /> {t("review.title")}
      </h2>
      <p className="muted">{t("review.intro")}</p>
      <div className="stats stats-3" style={{ margin: "14px 0" }}>
        <div className="stat">
          <strong>{data.due_count}</strong>
          <span className="small muted">{t("review.dueToday")}</span>
        </div>
        <div className="stat">
          <strong>{data.total}</strong>
          <span className="small muted">{t("review.inDeck")}</span>
        </div>
      </div>
      {caughtUp ? (
        <div className="alert alert-success" role="status">
          <Icon name="check" /> {t("review.caughtUp")}
        </div>
      ) : (
        <>
          <p className="small muted with-icon">
            <Icon name="info" size={15} /> {t("review.xpNote")}
          </p>
          <button className="btn btn-success" onClick={onStart} style={{ marginTop: 6 }}>
            <Icon name="play" size={16} /> {t("review.start")}
          </button>
        </>
      )}
    </div>
  );
}

export default function ReviewPanel() {
  const state = useApi("/review/");
  const [session, setSession] = useState(null);

  return (
    <Loader state={state}>
      {(data) =>
        session ? (
          <Session
            due={session}
            onExit={() => {
              setSession(null);
              state.reload();
            }}
            onAgain={async () => {
              const fresh = await api("/review/");
              setSession(fresh.due.length ? fresh.due : null);
              if (!fresh.due.length) state.setData(fresh);
            }}
          />
        ) : (
          <Entry data={data} onStart={() => setSession(data.due)} />
        )
      }
    </Loader>
  );
}
