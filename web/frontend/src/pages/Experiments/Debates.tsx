import useHideAnswers from "../../hooks/useHideAnswers";
import { AuthRequirement, useUser } from "../../hooks/userProvider";
import { Debate, Experiment, useTypedLoaderData } from "../../utils/types";
import DebateListItem from "../../components/DebateListItem";

export async function experimentDebatesLoader() {
  try {
    const completedDebatesRequest = fetch(`/api/experiments/completed_debates`);
    const nextDebateRequest = fetch(`/api/debates/next`);

    const [completedDebatesResponse, nextDebateResponse] = await Promise.all([
      completedDebatesRequest,
      nextDebateRequest,
    ]);

    const { debates: completedDebates } = await completedDebatesResponse.json();
    const debate = await nextDebateResponse.json();

    return { completedDebates, debate };
  } catch (error) {
    console.error("Error:", error);
  }
}

function groupDebatesByExperiment(debates: Debate[]) {
  const experiments: Experiment[] = [];
  debates
    .filter((d) => d.experiment)
    .forEach((debate) => {
      let experiment = experiments.find((e) => e.id === debate.experiment!.id);
      if (!experiment) {
        experiment = {...debate.experiment!}
        experiments.push(experiment);
      }
      if (!experiment.debates) {
        experiment.debates = [];
      }
      experiment.debates.push(debate);
    });
  return experiments;
}

function CompletedDebatesExperiment({
  experiment,
}: {
  experiment: Experiment;
}) {
  const [getHideAnswers] = useHideAnswers();
  const hideAnswers = getHideAnswers();
  const urlPrefix = `/experiments/debates`;
  return (
    <div className="mb-16">
        <h3 className="text-base font-semibold leading-6 text-gray-900 mb-4">
          {experiment.public_name || experiment.name} (
          {experiment.debates!.length})
        </h3>

      <ul className=" flex flex-col gap-2 px-4">
        {experiment
          .debates!.filter((d) => d.judgement)
          .sort((a, b) => b.judgement!.id - a.judgement!.id)
          .map((debate) => (
            <DebateListItem
              key={debate.id}
              debate={debate}
              hideAnswers={hideAnswers}
              urlPrefix={urlPrefix}
            />
          ))}
      </ul>
    </div>
  );
}

function CompletedDebatesExperimentsList({
  experiments,
}: {
  experiments: Experiment[];
}) {
  return (
    <div>
      {experiments
        .filter((e) => e.debates?.length)
        .sort((a, b) => b.id - a.id)
        .map((experiment) => (
          <CompletedDebatesExperiment experiment={experiment} key={experiment.id} />
        ))}
    </div>
  );
}
export default function ExperimentDebates() {
  useUser(AuthRequirement.User);
  const { completedDebates, debate } = useTypedLoaderData();
  const [getHideAnswers] = useHideAnswers();
  const hideAnswers = getHideAnswers();

  if (debate === undefined || completedDebates === undefined) {
    return <span>Loading...</span>;
  }
  const urlPrefix = `/experiments/debates`;

  const experiments = groupDebatesByExperiment(completedDebates);

  // Neat trick here: if viewing an experiment debate, change the url to playground to see all the extra stuff
  return (
    <div className="py-8 px-4">
      <div className="">
        <div className="border-b border-gray-200 pb-4 mb-4 flex flex-row justify-between">
          <h3 className="text-base font-semibold leading-6 text-gray-900">
            {debate
              ? debate.experiment?.public_name || "Next debate"
              : "No active experiment"}
          </h3>
          <h3 className="text-base font-semibold leading-6 text-gray-900">
            {debate ? `${debate?.debates_remaining || 0} remaining` : ""}
          </h3>
        </div>
        <ul className=" flex flex-col gap-2 px-4">
          {debate ? (
            <DebateListItem
              debate={debate}
              hideAnswers={hideAnswers}
              urlPrefix={urlPrefix}
            />
          ) : (
            <p>No debates to judge for now. </p>
          )}
        </ul>
      </div>
      <div className={`mt-16`}>
        <div className="">
          <div className="border-b border-gray-200 pb-4 mb-8 flex flex-row justify-between">
            <h2 className="text-base font-semibold leading-6 text-gray-900">
              Finished debates
            </h2>
          </div>
          <CompletedDebatesExperimentsList experiments={experiments} />
        </div>
      </div>
    </div>
  );
}
