import useHideAnswers from "../../hooks/useHideAnswers";
import { AuthRequirement, useUser } from "../../hooks/userProvider";
import { useEffect, useState } from "react";
import Select from "../../components/Select";
import Button from "../../components/Button";
import { useTypedLoaderData } from "../../utils/types";
import useCreatePlaygroundDebate from "../../hooks/createPlaygroundDebate";
import { isDebateComplete } from "../../utils/utils";
import DebateListItem from "../../components/DebateListItem";

export async function playgroundDebatesLoader() {
  try {
    const debatesRequest = fetch(`/api/playground/debates`);
    const debaterConfigsRequest = fetch(`/api/playground/debater_configs`);

    const [debatesResponse, configsResponse] = await Promise.all([
      debatesRequest,
      debaterConfigsRequest,
    ]);

    const { debates } = await debatesResponse.json();
    const configs = await configsResponse.json();

    return {
      debates,
      debaterConfigs: {
        debater_configs: configs.debater_configs.sort(),
        consultant_configs: configs.consultant_configs.sort(),
      },
    };
  } catch (error) {
    console.error("Error:", error);
  }
}

const debateTypes = [
  { label: "Debate", value: "debate" },
  { label: "Consultancy", value: "consultancy" },
  { label: "Correct Consultancy", value: "correct_consultancy" },
  { label: "Incorrect Consultancy", value: "incorrect_consultancy" },
];

export default function PlaygroundDebates() {
  const { debates, debaterConfigs: configs } = useTypedLoaderData();
  useUser(AuthRequirement.Admin);
  const [getHideAnswers] = useHideAnswers();
  const [selectedDebateType, setSelectedDebateType] = useState(
    debateTypes[0].value,
  );
  const [selectedConfig, setSelectedConfig] = useState<string | null>(null);
  const hideAnswers = getHideAnswers();
  const createDebate = useCreatePlaygroundDebate();

  useEffect(() => {
    // Make sure a correct config for the debate type is always selected
    if (!configs || !debateTypes) {
      return;
    }
    if (selectedDebateType === debateTypes[0].value) {
      if (
        !selectedConfig ||
        !configs.debater_configs.includes(selectedConfig)
      ) {
        setSelectedConfig(configs.debater_configs[0]);
      }
    } else {
      if (
        !selectedConfig ||
        !configs.consultant_configs.includes(selectedConfig)
      ) {
        setSelectedConfig(configs.consultant_configs[0]);
      }
    }
  }, [configs, debateTypes, selectedDebateType]);

  if (!debates || !debateTypes || !configs) {
    return <span>Loading...</span>;
  }
  const {
    debater_configs: debaterConfigs,
    consultant_configs: consultantConfigs,
  } = configs;
  const pendingDebates = debates.filter((d) => !isDebateComplete(d));
  const finishedDebates = debates.filter((d) => isDebateComplete(d));

  return (
    <div className="py-8">
      <div className="flex flex-row justify-center items-end mb-16">
        <Select
          value={selectedDebateType}
          label="Debate type"
          className="mr-2"
          onChange={(e) => setSelectedDebateType(e.target.value)}
        >
          {debateTypes.map((debateType) => (
            <option key={debateType.label} value={debateType.value}>
              {debateType.label}
            </option>
          ))}
        </Select>
        <Select
          value={selectedConfig || ""}
          label="Config"
          className="mr-2"
          onChange={(e) => setSelectedConfig(e.target.value)}
        >
          <optgroup label="Debater configs">
            {debaterConfigs.map((config: string) => (
              <option key={config} value={config}>
                {config}
              </option>
            ))}
          </optgroup>
          <optgroup label="Consultant configs">
            {consultantConfigs.map((config: string) => (
              <option key={config} value={config}>
                {config}
              </option>
            ))}
          </optgroup>
        </Select>
        <Button
          onClick={() => createDebate(selectedDebateType, selectedConfig)}
          className="ml-4"
        >
          New Debate
        </Button>
      </div>
      <div className="px-4">
        <div className="">
          <div className="border-b border-gray-200 pb-4 mb-4 flex flex-row justify-between">
            <h3 className="text-base font-semibold leading-6 text-gray-900">
              In progress debates ({pendingDebates.length})
            </h3>
          </div>
          <ul className=" flex flex-col gap-2 px-4">
            {pendingDebates
              .sort((a, b) => b.id - a.id)
              .map((debate) => (
                <DebateListItem
                  key={debate.id}
                  debate={debate}
                  hideAnswers={hideAnswers}
                  urlPrefix={"/playground/debates"}
                />
              ))}
          </ul>
        </div>
      </div>
      <div className="px-4 mt-16">
        <div className="">
          <div className="border-b border-gray-200 pb-4 mb-4 flex flex-row justify-between">
            <h3 className="text-base font-semibold leading-6 text-gray-900">
              Finished debates ({finishedDebates.length})
            </h3>
          </div>
          <ul className=" flex flex-col gap-2 px-4">
            {finishedDebates
              .sort((a, b) => b.judgement.id - a.judgement.id)
              .map((debate) => (
                <DebateListItem
                  key={debate.id}
                  debate={debate}
                  hideAnswers={hideAnswers}
                  urlPrefix={"/playground/debates"}
                />
              ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
