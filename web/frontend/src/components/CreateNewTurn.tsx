import { useEffect, useState } from "react";
import { Debate } from "../utils/types";
import Button from "./Button";
import TextArea from "./TextArea";
import { useDebateContext } from "../hooks/debateProvider";

const formatTime = (timeInSeconds: number) => {
  const minutes = Math.floor(timeInSeconds / 60);
  const seconds = timeInSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
};

interface CreateNewTurnProps {
  debate: Debate;
  setDebate: (debate: Debate) => void;
  onNewTurn: () => void;
  maxTurns?: number;
  judgeMessagesAllowed?: boolean;
}

export default function CreateNewTurn({
  debate,
  setDebate,
  onNewTurn,
  maxTurns,
  judgeMessagesAllowed = true,
}: CreateNewTurnProps) {
  const { generatingTurn, setGeneratingTurn } = useDebateContext();
  const [loadingTime, setLoadingTime] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [judgeMessage, setJudgeMessage] = useState("");
  const maxTurnsReached =
    maxTurns && maxTurns <= debate.transcript.rounds.length;

  useEffect(() => {
    if (debate.transcript.rounds.length === 0 && !debate.judgement) {
      createNewTurn();
    }
  }, [debate.transcript.rounds.length]);

  useEffect(() => {
    if (generatingTurn) {
      const loadingMessage = `Thinking... (${formatTime(loadingTime)})\n\nThis usually takes about a minute.`
      const currentRound = {
        ...debate.transcript.rounds[debate.transcript.rounds.length - 1],
        correct: loadingMessage,
        incorrect: loadingMessage,
      };
      setDebate({
        ...debate,
        transcript: {
          ...debate.transcript,
          rounds: [...debate.transcript.rounds.slice(0, -1), currentRound],
        },
      });
    }
  }, [generatingTurn, loadingTime]);

  const createNewTurn = async () => {
    if (generatingTurn) {
      return;
    }
    let timer;

    try {
      setGeneratingTurn(true);
      setLoadingTime(0);
      setError(null);
      const localJudgeMessage = judgeMessage;
      setJudgeMessage("");
      timer = setInterval(() => {
        setLoadingTime((prevTime) => prevTime + 1);
      }, 1000);
      const newRound = {
        correct: "",
        incorrect: "",
        judge: localJudgeMessage ? localJudgeMessage : undefined,
        type: "sim",
      };

      setDebate({
        ...debate,
        transcript: {
          ...debate.transcript,
          rounds: [
            ...debate.transcript.rounds.filter((r) => !r.error),
            newRound,
          ],
        },
      });
      onNewTurn();

      const response = await fetch(`/api/debates/${debate.id}/turn`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          judge_message: localJudgeMessage,
        }),
      });

      if (!response.ok) {
        // TODO: Extract this
        const contentType = response.headers.get("content-type");
        let error;
        if (contentType && contentType.includes("application/json")) {
          error = await response.json();
        } else {
          error = await response.text();
        }
        throw new Error(
          `HTTP Error: ${response.status} - ${error.detail ? error.detail : error
          }`,
        );
      }
      const newDebate = await response.json();
      setDebate(newDebate);
      setGeneratingTurn(false);
      onNewTurn();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.error("Failed to fetch debate:", message);
      setError(message);
      const newRound = {
        error: `${message}`,
        type: "sim",
      };

      const newRounds = [
        ...debate.transcript.rounds.filter((r) => !r.error),
        newRound,
      ];
      setDebate({
        ...debate,
        transcript: {
          ...debate.transcript,
          rounds: newRounds,
        },
      });
    } finally {
      clearInterval(timer);
      setLoadingTime(0);
      setGeneratingTurn(false);
    }
  };
  if (error) {
    return (
      <form className="h-32 flex p-2 pr-8 w-full justify-center bg-white items-center">
        <Button
          onClick={createNewTurn}
          disabled={generatingTurn}
          className="ml-2 whitespace-nowrap"
        >
          <span>Retry error</span>
        </Button>
      </form>
    );
  }
  return (
    <form className="flex p-2 pr-8 w-full justify-between bg-white items-center">
      {judgeMessagesAllowed ? (
        <TextArea
          className="w-full"
          label="Judge message"
          value={judgeMessage}
          onChange={(e) => setJudgeMessage(e.target.value)}
          inputClassName="h-32 "
          disabled={!!maxTurnsReached}
        />
      ) : (
        <div className=" p-4">Judge interaction disabled for this debate.</div>
      )}

      {maxTurnsReached ? (
        <div className="ml-2 whitespace-nowrap">Turn limit reached.</div>
      ) : (
        <Button
          onClick={createNewTurn}
          disabled={generatingTurn}
          className="ml-2 whitespace-nowrap"
        >
          {generatingTurn ? (
            <span>Loading...</span>
          ) : (
            <span>Continue Debate</span>
          )}
        </Button>
      )}
    </form>
  );
}
