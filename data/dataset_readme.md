# LLM Debate Human Judge Dataset

## Overview
This dataset contains all human experiment data from "Debating with More Persuasive LLMs Leads to More Truthful Answers". Each row is an LLM debate or consultancy, which was judged by a human annotator.


## Fields
- `debate_id`: Unique identifier for the debate.
- `judge_id`: Unique identifier for the judge. We started with a pool of 30 judges and filtered them down to 21 based on performance in the Test Phase. The following judge ids did not proceed from the test into the main experiments: 11, 17, 20, 22, 29, 32, 34, 35, 36, 37
- `experiment_name`: The name of the experiment.
- `story_title`: The title of the QuALITY article.
- `question`: The QuALITY question.
- `debate_method`: debate, consultancy, or baseline
- `consultant_type`: correct, incorrect, or null
- `interactive_judge`: Indicates if there was a human interactive judge.
- `debater_config`: Config used for the expert model(s).
- `swap`: If False, the correct answer was position A. If True, the correct answer was position B.
- `max_turns_allowed`: The maximum number of turns allowed. In interactive protocols, judges can generate additional rounds until this number is reached. This was always 3.
- `min_turns_required`: The minimum number of turns required. Judges may not submit a judgement until this number is reached. This did not exist for early experiments, but once introduced it was always 3.
- `turns_used`: The number of turns at the time of judgement.
- `transcript_char_count`: The number of characters in the transcript rounds.
- `correct`: Whether the judge chose the correct answer.
- `confidence_correct`: The confidence the judge assigned to the correct answer.
- `confidence`: The confidence the judge assigned to their chosen answer.
- `judgement_time`: The time when the judgement was made.
- `explanation`: The judge's explanation for their decision.
- `answerability`: Average answerability rating given by the QuALITY annotators.
- `untimed_accuracy`: Average accuracy of the untimed QuALITY annotators.
- `speed_accuracy`: Average accuracy of the speed QuALITY annotators.
- `context_required`: Average context required rating given by the QuALITY annotators.
- `question_set_id`: QuALITY set_unique_id.
- `quality_source`: Either Slate or Gutenberg.
- `transcript`: JSON object containing information about the debate or consultancy. This is the object used to store state in our codebase. Some fields are duplicates of those above. New fields are:
  - `story`: The text of the QuALITY article. Omitted in this dataset.
  - `answers`: The two possible answers to the question. One is correct, and one is the best distractor as rated by the QuALITY annotators.
  - `names`: The names of the debate participants.
  - `rounds`: The arguments made by the models and any statements from the judge. This is what we refer to as the "transcript" in the paper.
  - `responses`: In cases where boN or cN was used, this contains all of the candidate arguments the models generated for each round, along with the rating given by the preference model.
- `dataset_split`: The QuALITY split the question came from.

## Judgements used for analysis in the paper
- The primary results in the paper used Experiment 8, as this was our test set.
- The naive baseline was done in Experiment 9.
- The low-elo results came from Experiment 10.
- Experiments 1-7 were for iteration. The data from these experiments has a few issues to be aware of:
  - All experiments after Experiment 1 used only questions with a context_required rating of at least 1.5. Experiment 1 only required questions with context_required 1 or higher. All analysis that used Experiment 1 results only considered the subset of Experiment 1 questions that had context_required of at least 1.5.
  - Experiments 2, 3, and 5_v0 were impacted by a bug that caused the worst argument to be chosen (as rated by the preference model), rather than the best argument. This only applied in cases where swap=True. Analysis done on these experiments only uses the swap=False rows (approx. 50% of the data) for this reason. Experiment 4 was unaffected because it did not use boN. The bug was discovered shortly after releasing Experiment 5. The experiment was paused while the bug was fixed and then resumed. Experiment 5_v0 is the portion of Experiment 5 that was impacted by the bug. When analysing Experiment 5 results, we include the swap=False 5_v0 data.
- The day after we launched Experiment 8, OpenAI released log-prob access for GPT-4-Turbo. Prior to this we had been using GPT-4-Base as our preference model. We switched to using GPT-4-Turbo as our preference model once log-probs became available, because it was much cheaper and gave better results. Experiment 8_v0 is the portion of Experiment 8 that used GPT-4-Base as a preference model. We do not include this data in any of our analysis.
- Analysis was done on judgements received up to Jan 24th. A small number of judgements were submitted after this date and are included here.
