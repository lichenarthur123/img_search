import os
import json
import numpy as np
from embedding import get_image_embedding
from sklearn.metrics.pairwise import cosine_similarity
from global_params import global_lock, global_variable

def load_embeddings(database_dir):
    """
    加载 database 目录下所有 data.jsonl 文件中的 embedding 数据
    """
    embeddings = []
    records = []
    
    for root, _, files in os.walk(database_dir):
        for file in files:
            if file == 'data.jsonl':
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    for line in f:
                        try:
                            record = json.loads(line)
                            if 'emb' in record and 'dir' in record and 'fname' in record:
                                if len(record['emb']) == 1024:
                                    embeddings.append(record['emb'])
                                    records.append({
                                        'dir': record['dir'],
                                        'fname': record['fname']
                                    })
                        except:
                            # 忽略无效行
                            continue
    return embeddings, records

def search_similar_images(image_path, database_dir, top_k=5):
    """
    搜索与输入图片最相似的五条记录
    :param image_path: 图片路径
    :param database_dir: 数据库目录
    :param top_k: 返回最相似的记录数
    :return: 包含 dir, fname 和相似度的列表
    """
    # 获取输入图片的 embedding
    print(image_path)
    input_embedding = get_image_embedding(image_path)
    
    # 加载数据库中的 embedding 和记录
    #embeddings, records = load_embeddings(database_dir)
    with global_lock:
        embeddings = [item['emb'] for item in global_variable['database_data']]

        # 计算点积（假设向量已归一化）
        similarities = np.dot(embeddings, input_embedding)
        
        # 获取最相似的五条记录
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        results = []
        for idx in top_indices:
            results.append({
                'dir': global_variable['database_data'][idx]['dir'],
                'fname': global_variable['database_data'][idx]['fname'],
                'similarity': float(similarities[idx])
            })
        #print(results)
    return results

if __name__ == '__main__':
    # 示例用法
    #input_image = "path/to/your/image.jpg"  # 替换为实际图片路径
    database_dir = "database"  # 替换为实际 database 目录路径

    #similar_images = search_similar_images(input_image, database_dir)
    #print(json.dumps(similar_images, indent=2))