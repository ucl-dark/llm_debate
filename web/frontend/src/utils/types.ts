import { useLoaderData } from "react-router-dom";

export interface TranscriptAnswers {
  correct: string;
  incorrect: string;
}

export interface TranscriptNames {
  judge?: string;
  cross_examiner?: string;
  correct?: string;
  incorrect?: string;
}

export interface TranscriptRound {
  judge?: string;
  cross_examiner?: string;
  correct?: string;
  incorrect?: string;
  error?: string
  type: string;
}

export interface TranscriptConfig {
  index: number;
  question: string;
  story?: string;
  answers: TranscriptAnswers;
  names: TranscriptNames;
  swap: boolean;
  rounds: TranscriptRound[];
  responses?: TranscriptRound[]
  extra: { string: any };
}

export interface Question {
  id: number;
  question_text: string;
  correct_answer: string;
  incorrect_answer: string;
  dataset?: string;
}

export interface File {
  id: number;
  path: string;
  path_hash?: string;
  created_at: Date;
  imported_at: Date;
}

export interface RowSummary {
  id: number;
  row_number: number;
}

// export interface RowDetail extends RowSummary {
//
// }

// Backend has a DB Judgement and a response Judgements... in files api, judgement table is not used
export interface ModelJudgement {
  judgement_text: string;
  judge_name: string;
  is_correct?: boolean | null;
}

export interface HumanJudgement {
  id: number;
  created_at: Date
  judge_name: string;
  confidence_correct: number;
  explanation: string;
}

// May need to extract some of this into a RowDetail
export interface GetRowResponse extends RowSummary {
  question: Question;
  file: File;
  raw_transcript: string;
  transcript?: TranscriptConfig;
  judgement?: ModelJudgement;
  next_available?: boolean;
}

export interface GetFileResponseRow extends RowSummary {
  question: Question;
  is_judgement_correct?: boolean;
}

export interface GetFileResponse extends File {
  rows: GetFileResponseRow[];
}

export interface GetFilesResponseItem extends File {
  row_count?: number;
}

export type GetFilesResponse = GetFilesResponseItem[];

export interface Experiment {
  id: number
  name: string
  public_name?: string
  give_judge_feedback: boolean
  starts_at: Date
  ends_at: Date
  debates?: Debate[]
}

export interface Debate {
  id: number;
  name: string
  max_turns?: number
  min_turns?: number
  method: "debate" | "consultancy"
  config_path: string
  allow_judge_interaction: boolean
  user: User;
  transcript: TranscriptConfig;
  judgement?: HumanJudgement;
  experiment?: Experiment
}

export type GetDebatesResponse = Debate[];
export interface GetDebateResponse extends Debate {
  raw_transcript: string;
  next_debate_id?: number;
  debates_remaining?: number
}

export interface GetConfigsResponse {
  debater_configs: string[]
  consultant_configs: string[]
}

export interface LoaderData {
  row?: GetRowResponse;
  file?: GetFileResponse;
  files?: GetFilesResponse;
  debates?: GetDebatesResponse;
  completedDebates?: GetDebatesResponse;
  debate?: GetDebateResponse | null;
  debaterConfigs?: GetConfigsResponse | null
}

export function useTypedLoaderData() {
  return useLoaderData() as LoaderData;
}

export interface User {
  id: number
  user_name: string
  full_name?: string
  admin: boolean
}
