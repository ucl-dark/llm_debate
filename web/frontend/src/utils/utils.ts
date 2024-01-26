import {
  Debate,
  TranscriptConfig,
  TranscriptNames,
  TranscriptRound,
} from "./types";

export function swapNames(
  transcript: string,
  name_1: string,
  name_2: string,
): string {
  return transcript
    .replace(new RegExp(name_1, "g"), "TEMP_NAME")
    .replace(new RegExp(name_2, "g"), name_1)
    .replace(new RegExp("TEMP_NAME", "g"), name_2);
}

export function classNames(
  ...classes: (string | number | boolean | null | undefined)[]
) {
  return classes.filter(Boolean).join(" ");
}

export function swapSubstrings(str: string, sub1: string, sub2: string) {
  const tempMarker = "___TEMP___";
  let tempStr = str.replace(new RegExp(sub1, "g"), tempMarker);

  tempStr = tempStr.replace(new RegExp(sub2, "g"), sub1);

  return tempStr.replace(new RegExp(tempMarker, "g"), sub2);
}

export function swapNamesInRound(
  round: TranscriptRound,
  names: TranscriptNames,
) {
  const { correct, incorrect } = names;
  if (!correct || !incorrect) {
    return round;
  }

  const newRound: TranscriptRound = { ...round };
  Object.keys(round).forEach((key) => {
    const name = key as keyof TranscriptRound;
    if (round[name]) {
      newRound[name] = swapSubstrings(
        round[name] as string,
        correct,
        incorrect,
      );
    }
  });

  return newRound;
}

export function reverseTranscript(transcript: TranscriptConfig) {
  // TODO: Should also swap debater names that appear within arguments
  const reversed = {
    ...transcript,
    names: {
      ...transcript.names,
      correct: transcript.names.incorrect,
      incorrect: transcript.names.correct,
    },
    rounds: transcript.rounds.map((r) => swapNamesInRound(r, transcript.names)),
    swap: !transcript.swap,
  };
  return reversed;
}

export function isJSONParsable(str: string) {
  try {
    JSON.parse(str);
    return true;
  } catch (e) {
    return false;
  }
}

export function isDebateComplete(debate: Debate) {
  return Boolean(debate.judgement);
}

export function isDebateTwoSided(debate: Debate) {
  return debate.method === "debate"
}

export function quadraticScore(confidencesCorrect: number[]) {
  const n = confidencesCorrect.length;
  if (n === 0) {
    throw new Error("Array must not be empty.");
  }

  let sum = 0;
  for (const confidence of confidencesCorrect) {
    // Normalize the input to range between -50 and +50
    const normalizedInput = confidence - 50;
    // Calculate the quadratic score
    const score = Math.pow(normalizedInput, 2) / 25;

    if (confidence > 50) {
      sum = sum + score
    } else {
      sum = sum - score
    }
  }


  return sum;
}

export function shouldShowFeedback(debate: Debate) {
  return !debate.experiment || debate.experiment.give_judge_feedback
}

export function hasInteractiveJudge(debate: Debate) {
  return debate.allow_judge_interaction
}

export function getDebateType(debate: Debate, hideAnswers = true) {
  let debateType
  if (!isDebateTwoSided(debate)) {
    if (isDebateComplete(debate) && !hideAnswers && shouldShowFeedback(debate)) {
      debateType = debate.transcript.names.correct
        ? "Honest Consultancy"
        : "Dishonest Consultancy";
    } else {
      debateType = "Consultancy";
    }
  } else {
    debateType = "Debate";
  }

  return debateType
}
