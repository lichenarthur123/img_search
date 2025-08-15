import os
import json
import base64
from global_params import global_lock, global_variable, api_key, rembg_session

from rembg import remove, new_session
#from alibabacloud_imagerecog20190930.client import Client as imagerecog20190930Client
#from alibabacloud_tea_openapi import models as open_api_models
#from alibabacloud_imagerecog20190930 import models as imagerecog_models

def get_embedding_from_bytes(image_bytes):
    """
    输入图片二进制数据，返回向量base64编码
    :param image_bytes: 图片二进制数据
    :return: 随机生成的2560维fp32向量的base64编码
    """
    #import numpy as np
    #import base64
    #vector = np.random.rand(2560).astype(np.float32)
    #bytes_data = vector.tobytes()
    #return base64.b64encode(bytes_data).decode('utf-8')

    import dashscope
    from http import HTTPStatus
    # 设置图像格式
    image_format = "png"  # 根据实际情况修改，比如jpg、bmp 等
    image_data = f"data:image/{image_format};base64,{image_bytes}"
    # 输入数据
    input = [{'image': image_data}]

    # 调用模型接口
    dashscope.api_key = api_key
    resp = dashscope.MultiModalEmbedding.call(
        model="multimodal-embedding-v1",
        input=input
    )
    if resp.status_code == HTTPStatus.OK and 'embeddings' in resp.output:
        #result = {
        #    "status_code": resp.status_code,
        #    "request_id": getattr(resp, "request_id", ""),
        #    "code": getattr(resp, "code", ""),
        #    "message": getattr(resp, "message", ""),
        #    "output": resp.output,
        #    "usage": resp.usage
        #}
        #print(json.dumps(result, ensure_ascii=False, indent=4))
        return resp.output['embeddings'][0]['embedding']
    else:
        #print("Request id: " + resp.request_id)
        #print("Status code: " + str(resp.status_code))
        #print(resp.code)
        #print(resp.message)
        return []
    ####

def get_image_embedding(image_path):
    """
    输入图片路径，返回向量base64编码
    :param image_path: 图片路径
    :return: 随机生成的2560维fp32向量的base64编码
    """
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
        image_bytes = remove(image_bytes, session=rembg_session)
        image_bytes = base64.b64encode(image_bytes).decode('utf-8')
    return get_embedding_from_bytes(image_bytes)


def process_directory(directory_path):
    """
    处理目录中的所有图片
    :param directory_path: 图片目录路径
    """
    # 获取随机目录名
    random_dir = os.path.basename(directory_path)
    
    # 创建database目录结构
    database_dir = os.path.join('database', random_dir)
    os.makedirs(database_dir, exist_ok=True)
    
    # 处理每张图片
    for filename in os.listdir(directory_path):
        if filename.endswith('.jpg') or filename.endswith('.png'):
            image_path = os.path.join(directory_path, filename)
            embedding = get_image_embedding(image_path)
            
            # 构建数据行
            data = {
                "emb": embedding,
                "dir": random_dir,
                "fname": filename
            }
            
            # 写入jsonl文件
            jsonl_path = os.path.join(database_dir, 'data.jsonl')
            with open(jsonl_path, 'a') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            
            print(f"Processed {filename} and saved to {jsonl_path}")