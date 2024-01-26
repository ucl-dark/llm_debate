#!/bin/bash
set -eoux pipefail

exp_dir=./exp/figure1

limit=47 # limit number of questions to speed up if needed
dataset_args="++max_num_from_same_story=5 ++split=both ++human_experiments=8 ++limit=$limit" # T_h dataset (47 questions)
debate_args="++correct_debater.language_model.model=gpt-4-1106-preview \
            ++incorrect_debater.language_model.model=gpt-4-1106-preview \
            ++correct_preference.language_model.model=gpt-4-1106-preview \
            ++incorrect_preference.language_model.model=gpt-4-1106-preview \
            ++correct_debater.BoN=16 ++incorrect_debater.BoN=16 \
            ++correct_debater.language_model.temperature=0.8 \
            ++incorrect_debater.language_model.temperature=0.8"
mkdir -p $exp_dir

# Run debate doesn't need interactive judge
python3 -m core.debate exp_dir=$exp_dir +experiment='debate' $debate_args $dataset_args

# Initialise additional baselines
python3 -m core.debate exp_dir=$exp_dir +experiment='blind' $dataset_args
python3 -m core.debate exp_dir=$exp_dir +experiment='oracle' $dataset_args

for model_judge in gpt-3.5-turbo gpt-4-1106-preview claude-2.1; do

    # Run debate and consultancy with interactive judge
    interactive_args="$debate_args ++cross_examiner.language_model.model=$model_judge"
    python3 -m core.debate exp_dir=$exp_dir/interactive=$model_judge +experiment='debate_interactive' \
        $interactive_args $dataset_args
    python3 -m core.debate exp_dir=$exp_dir/interactive=$model_judge +experiment='consultancy' method_type='correct' \
        $interactive_args $dataset_args
    python3 -m core.debate exp_dir=$exp_dir/interactive=$model_judge +experiment='consultancy' method_type='incorrect' \
        $interactive_args $dataset_args

    # Judge all experiments
    judge_args="++judge.language_model.model=$model_judge ++judge_name=$model_judge"
    python3 -m core.judge exp_dir=$exp_dir +experiment='debate' \
        $judge_args
    python3 -m core.judge exp_dir=$exp_dir/interactive=$model_judge +experiment='debate_interactive' \
        $judge_args
    python3 -m core.judge exp_dir=$exp_dir/interactive=$model_judge +experiment='consultancy' method_type='correct' \
        $judge_args
    python3 -m core.judge exp_dir=$exp_dir/interactive=$model_judge +experiment='consultancy' method_type='incorrect' \
        $judge_args

    # Additional baselines
    python3 -m core.judge exp_dir=$exp_dir +experiment='blind' \
        $judge_args

    model_judge_expert=$model_judge
    if [ $model_judge == "gpt-3.5-turbo" ]; then
        # Expert judge needs longer context
        model_judge_expert="gpt-3.5-turbo-16k"
    fi
    judge_expert_args="++judge.language_model.model=$model_judge_expert ++judge_name=$model_judge"
    python3 -m core.judge exp_dir=$exp_dir +experiment='oracle' \
        $judge_expert_args

    # Score all experiments
    score_args="++judge_name=$model_judge"
    python3 -m core.scoring.accuracy exp_dir=$exp_dir/interactive=$model_judge +experiment='debate_interactive' $score_args
    python3 -m core.scoring.accuracy exp_dir=$exp_dir/interactive=$model_judge +experiment='consultancy' method_type='correct' $score_args
    python3 -m core.scoring.accuracy exp_dir=$exp_dir/interactive=$model_judge +experiment='consultancy' method_type='incorrect' $score_args
    python3 -m core.scoring.accuracy exp_dir=$exp_dir +experiment='blind' $score_args
    python3 -m core.scoring.accuracy exp_dir=$exp_dir +experiment='oracle' $score_args
done
