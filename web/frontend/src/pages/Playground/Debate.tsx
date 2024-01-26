import { useState, useEffect } from "react";
import { useUser } from "../../hooks/userProvider";
import Button from "../../components/Button";
import DebateHeader from "../../components/DebateHeader";
import { useTypedLoaderData } from "../../utils/types";
import useCreatePlaygroundDebate from "../../hooks/createPlaygroundDebate";
import useHideAnswers from "../../hooks/useHideAnswers";
import JudgementPanel from "../../components/JudgementPanel";
import DebateTabs from "../../components/DebateTabs";
import { isDebateComplete, isDebateTwoSided } from "../../utils/utils";
import { DebateProvider } from "../../hooks/debateProvider";

export default function PlaygroundDebate() {
  const { debate: loaderDebate } = useTypedLoaderData();
  const { user } = useUser();
  const [debate, setDebate] = useState(loaderDebate);
  const createDebate = useCreatePlaygroundDebate();
  const [getHideAnswers] = useHideAnswers();
  let hideAnswers = getHideAnswers();

  useEffect(() => {
    setDebate(loaderDebate);
  }, [loaderDebate]);

  if (!debate) {
    return <div>Loading...</div>;
  }

  if (!isDebateComplete(debate)) {
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
              hideAnswers={hideAnswers}
            />
          </div>
          <div className="w-1/4 px-4 ">
            <div className="mt-8">
              <p className="mb-8">
                Turns used: {debate.transcript.rounds.length}
              </p>
              <JudgementPanel debate={debate} hideAnswers={hideAnswers} />
              {isDebateComplete(debate) && user && user.admin && (
                <div>
                  <Button
                    onClick={() =>
                      createDebate(
                        isDebateTwoSided(debate) ? "debate" : "consultancy",
                        debate.config_path,
                        debate.id,
                      )
                    }
                    variant="secondary"
                    className="w-full"
                  >
                    Re-run debate
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </DebateProvider>
  );
}
