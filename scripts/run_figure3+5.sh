#!/bin/bash
set -eoux pipefail
DATE=$(date '+%y-%m-%d')

exp_dir=./exp/figure3+5

# figure 3 - run the cross play tournament and self play runs
python3 -m paper_scripts.run_tournament --tournament_dir $exp_dir --method st --anthropic_num_threads 1 # swiss tournament
python3 -m paper_scripts.run_tournament --tournament_dir $exp_dir --method sp --anthropic_num_threads 1 # self play
python -m core.scoring.ratings --tournament-dir $exp_dir --judge-name gpt-4-1106-preview --dir-name st


# figure 5 - judge the swiss tournament with other judges
for model_judge in gpt-3.5-turbo claude-2.1; do
    judge_args="++judge.language_model.model=$model_judge ++limit=291 ++judge_name=$model_judge ++anthropic_num_threads=1"
    score_args="++judge_name=$model_judge"
    for dir in $exp_dir/st/*/; do
        python3 -m core.judge exp_dir=$dir +experiment='debate' $judge_args
        python3 -m core.scoring.accuracy exp_dir=$dir +experiment='debate' $score_args
    done
    python -m core.scoring.ratings --tournament-dir $exp_dir --judge-name $model_judge --dir-name st
done

# combined judge ratings
python -m core.scoring.ratings --tournament-dir $exp_dir --dir-name st
