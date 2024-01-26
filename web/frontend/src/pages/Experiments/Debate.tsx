import { useState, useEffect } from "react";
import Button from "../../components/Button";
import DebateHeader from "../../components/DebateHeader";
import { useTypedLoaderData } from "../../utils/types";
import useHideAnswers from "../../hooks/useHideAnswers";
import JudgementPanel from "../../components/JudgementPanel";
import DebateTabs from "../../components/DebateTabs";
import { isDebateComplete, shouldShowFeedback } from "../../utils/utils";
import { DebateProvider } from "../../hooks/debateProvider";

export default function ExperimentDebate() {
  const { debate: loaderDebate } = useTypedLoaderData();
  const [debate, setDebate] = useState(loaderDebate);
  const [getHideAnswers] = useHideAnswers();
  let hideAnswers = getHideAnswers();

  const nextDebateId = debate?.next_debate_id;
  const nextDebate = () => {
    window.location.href = `/experiments/debates/${nextDebateId}${location.search}`;
  };

  useEffect(() => {
    setDebate(loaderDebate);
  }, [loaderDebate]);

  if (!debate) {
    return <div>Loading...</div>;
  }

  if (!debate.experiment) {
    throw Error("Not an experiment debate");
  }

  if (!isDebateComplete(debate) || !shouldShowFeedback(debate)) {
    hideAnswers = true;
  }

  return (
    <DebateProvider>
      <div
        className="flex flex-col overflow-hidden"
        style={{ height: "calc(100vh - 65px)" }}
      >
        <DebateHeader
          question={debate.transcript.question}
          answers={debate.transcript.answers}
          names={debate.transcript.names}
          swap={debate.transcript.swap}
          hideAnswers={hideAnswers}
        />
        <div className="flex flex-grow overflow-hidden">
          <div className="flex flex-col w-3/4">
            <DebateTabs
              debate={debate}
              setDebate={setDebate}
              maxTurns={debate.max_turns}
              judgeMessagesAllowed={debate.allow_judge_interaction}
              hideAnswers={hideAnswers}
              responsesEnabled={false}
              rawTranscriptEnabled={false}
              storyEnabled={false}
            />
          </div>
          <div className="w-1/4 px-4 overflow-y-auto ">
            <div className="mt-8">
              <div className="flex flex-col gap-2 mb-8">
                <p className="">
                  <span className="text-sm font-medium text-gray-700">
                    Title:
                  </span>{" "}
                  {debate.name}
                </p>
                <p className="">
                  <span className="text-sm font-medium text-gray-700">
                    Turns used:
                  </span>{" "}
                  {debate.transcript.rounds.length}
                </p>
                <p>
                  <span className="text-sm font-medium text-gray-700">
                    Turns allowed:
                  </span>{" "}
                  {debate.max_turns || "Unlimited"}
                </p>
                <p>
                  <span className="text-sm font-medium text-gray-700">
                    Minimum turns:
                  </span>{" "}
                  {debate.min_turns || "None"}
                </p>
              </div>
              <JudgementPanel
                debate={debate}
                hideAnswers={hideAnswers}
                isExplanationRequired={true}
                isCommitmentRequired={true}
              />
              {isDebateComplete(debate) && (
                <div>
                  <div className="border-b border-gray-200 pb-2 mb-4">
                    <h3 className="text-base font-semibold leading-6 text-gray-900">
                      {debate.debates_remaining} debate{debate.debates_remaining === 1 ? '' : 's'} remaining
                    </h3>
                  </div>
                  {nextDebateId ? (
                    <Button
                      onClick={nextDebate}
                      variant="primary"
                      className="w-full mb-2"
                    >
                      Next debate
                    </Button>
                  ) : (
                    <div>You've judged all of your assigned debates! 🎉</div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </DebateProvider>
  );
}
