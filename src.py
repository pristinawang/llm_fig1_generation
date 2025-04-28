from benchmark_helpers import *
import concurrent.futures
from concurrent_helpers import *
import os

def save_latex(target_dict, latex_files_path, backup_dir_path, backup_db_file_name='arxiv_id_db_backup.csv'):
    for year, venue in target_dict.items():
        backup_db_path = os.path.join(backup_dir_path, backup_db_file_name)

        titles=return_paper_titles(year=year, venue=venue)
        paper_id_dict, not_found_titles = get_arxiv_id_dict(titles=titles, max_results=10, backup_db_path=backup_db_path)
        paper_id_dict=download_latex_files(paper_id_dict=paper_id_dict, save_dir_path=latex_files_path)

def save_ids(target_dict, backup_dir_path, backup_db_file_name='arxiv_id_db_backup.csv'):
    for year, venue in target_dict.items():
        backup_db_path = os.path.join(backup_dir_path, backup_db_file_name)

        titles=return_paper_titles(year=year, venue=venue)
        paper_id_dict, not_found_titles = get_arxiv_id_dict(titles=titles, max_results=10, backup_db_path=backup_db_path)

def concurrent_download_latex(target_dict, latex_files_path, benchmark_dir_path, backup_dir_path, cpu_num, backup_db_file_name='arxiv_id_db_backup.csv'):
    assert 1 == 0, "this will triggered arxiv captcha, better not use this"

    for year, venue in target_dict.items():
        csv_path = os.path.join(benchmark_dir_path, venue, year, f'{venue}_{year}.csv')
        backup_db_path = os.path.join(backup_dir_path, backup_db_file_name)

        titles=return_paper_titles(year=year, venue=venue)
        
        paper_id_dict, not_found_titles = get_arxiv_id_dict(titles=titles, max_results=10, backup_db_path=backup_db_path)
        paper_id_dict=parallel_download_latex_files(paper_id_dict=paper_id_dict, save_dir_path=latex_files_path, max_workers=cpu_num)

def concurrent_full_extraction(target_dict, latex_files_path, benchmark_dir_path, backup_dir_path, cpu_num, backup_db_file_name='arxiv_id_db_backup.csv'):
    for year, venue in target_dict.items():
        csv_path = os.path.join(benchmark_dir_path, venue, year, f'{venue}_{year}.csv')
        backup_db_path = os.path.join(backup_dir_path, backup_db_file_name)

        titles=return_paper_titles(year=year, venue=venue)
        
        paper_id_dict, not_found_titles = get_arxiv_id_dict(titles=titles, max_results=10, backup_db_path=backup_db_path)
        paper_id_dict=download_latex_files(paper_id_dict=paper_id_dict, save_dir_path=latex_files_path)
        success_extractions=parallel_extract_to_csv(paper_id_dict=paper_id_dict, latex_files_path=latex_files_path, csv_path=csv_path, max_workers=cpu_num)
        print("🎉",len(success_extractions),"out of", len(titles),"papers are successfully extracted")

def regular_full_extraction(target_dict, latex_files_path, benchmark_dir_path, backup_dir_path, backup_db_file_name='arxiv_id_db_backup.csv'):
    for year, venue in target_dict.items():
        csv_path = os.path.join(benchmark_dir_path, venue, year, f'{venue}_{year}.csv')
        backup_db_path = os.path.join(backup_dir_path, backup_db_file_name)

        titles=return_paper_titles(year=year, venue=venue)
        
        paper_id_dict, not_found_titles = get_arxiv_id_dict(titles=titles, max_results=10, backup_db_path=backup_db_path)
        paper_id_dict=download_latex_files(paper_id_dict=paper_id_dict, save_dir_path=latex_files_path)
        success_extractions=extract_to_csv(paper_id_dict=paper_id_dict, latex_files_path=latex_files_path, csv_path=csv_path)
        print("🎉",len(success_extractions),"out of", len(titles),"papers are successfully extracted")

