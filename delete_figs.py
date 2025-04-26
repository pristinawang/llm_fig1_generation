import pandas as pd
import os

file_path = '/export/fs06/yguan19/Figure1_Dataset_2021_latexparser/benchmark/fig1_bench.csv'

filename_with_ext =  os.path.basename(file_path)
filename_without_ext= os.path.splitext(filename_with_ext)[0]

parent_path = os.path.dirname(file_path)
saved_file_path = os.path.join(parent_path,f"{filename_without_ext}_filtered.csv")


# 读取CSV文件（注意保持原有分隔符）
df = pd.read_csv(file_path)  # 根据实际情况调整文件路径

# 需要删除的arxiv_id列表（示例）
arxiv_ids_to_remove = [
    "2011.04946v1",
    "2012.15761v2",
    "2105.02657v2",
    "2105.05222v2",
    "2105.07452v1",
    "2105.08504v1",
    "2105.11098v2",
    "2106.00853v1",
    "2106.00941v1",
    "2106.01045v1",
    "2106.01229v2",  # ← 标注为“应该不算？”你可以自己决定是否保留
    "2106.02124v1",
    "2106.03518v3",
    "2106.05691v1",
    "2106.06555v1",
    "2106.07345v1",
    "2106.09233v1",
    "2106.11410v2",
    "2106.13213v1",
    "2106.13553v2"
]


# 过滤出不需要删除的行
filtered_df = df[~df["arxiv_id"].isin(arxiv_ids_to_remove)]

# 保存结果（可选择覆盖原文件或新建文件）
filtered_df.to_csv(saved_file_path, 
                  sep="\t", 
                  index=False, 
                  columns=["paper_title", "arxiv_id", "fig1_file_path", "fig1_caption", "abstract", "introduction"])

print(f"已删除{len(df)-len(filtered_df)}行，剩余{len(filtered_df)}行")