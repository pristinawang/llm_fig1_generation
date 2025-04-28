from benchmark_helpers import *
import os
import concurrent.futures
from src import *

def main():
    # Use benchmark_helpers to crawl bench mark
    # year='2021'
    # venue='naacl'
    target_dict = {
        '2023':'cvpr',
        '2024':'cvpr',
        '2025':'cvpr'
        }
    
    # save_dir_path = '/scratch4/afield6/pwang71/llm_fig1_generation/arxiv_source/'
    latex_files_path = './arxiv_source/'
    # csv_path = os.path.join('./benchmark/', venue, year, f'{venue}_{year}.csv')
    # backup_db_path = '/scratch4/afield6/pwang71/llm_fig1_generation/arxiv_id_db_backup.csv'
    benchmark_dir_path = './benchmark/'
    backup_dir_path ='/export/fs05/pwang71/llm_fig1_generation'
    cpu_num = 8
    
    #concurrent_full_extraction(target_dict, latex_files_path, benchmark_dir_path, backup_dir_path, cpu_num)
    # save_ids(target_dict, backup_dir_path)
    regular_full_extraction(target_dict, latex_files_path, benchmark_dir_path, backup_dir_path)
    
    # titles=return_paper_titles(year=year, venue=venue)
    # paper_id_dict, not_found_titles = get_arxiv_id_dict(titles=titles, max_results=10, backup_db_path=backup_db_path)
    # paper_id_dict=download_latex_files(paper_id_dict=paper_id_dict, save_dir_path=save_dir_path)
    # success_extractions=extract_to_csv(paper_id_dict=paper_id_dict, latex_files_path=latex_files_path, csv_path=csv_path)
    # print("🎉",len(success_extractions),"out of", len(titles),"papers are successfully extracted")

if __name__ == "__main__":
    main()
    