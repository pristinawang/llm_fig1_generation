#!/bin/bash
#




#SBATCH --job-name=llm_fig1_geneartion_2024_iclr
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus=1
#SBATCH --partition=gpu
#SBATCH --mail-user="yaohanguan@gmail.com"  # 邮件通知
#SBATCH --mail-type=ALL          # 通知类型



source /home/yguan19/miniconda3/etc/profile.d/conda.sh
conda activate fig1
ml purge
#module load namd/2.14-cuda-smp
module load cuda/11.7
ml
nvidia-smi
export CUDA_VISIBLE_DEVICES=0,1,2,3
export CONV_RSH=ssh
export HYDRA_FULL_ERROR=1


cd /home/yguan19/llm_fig1_with_all_avenues/llm_fig1_generation
python main.py 

