import dashscope
from http import HTTPStatus

import base64
import numpy as np
import json
import os
from global_params import api_key

def compare_img_bytes(image_bytes):
    
    messages = [
        {
            "role": "user",
            "content": []
        }
    ]
    #print(len(image_bytes))
    for img in image_bytes:
        image_format = "png"  # 根据实际情况修改，比如jpg、bmp 等
        image_data = f"data:image/{image_format};base64,{img}"
        messages[0]['content'].append({"image": image_data})
    
    
    messages[0]['content'].append({"text": "请分析两张图片视觉上是否存在相关性，图片中的主要元素，图样是否相似，如果是T恤则比较T恤中的印花和图片的相似度，并给出相似度分数从0-100，0为无风险，100为最高风险,如果足够相似则因大于80。输出格式为json，参考格式如下：{'score': 0-100, 'reason': '尽可能简洁地表述打分的依据'}。"})

    dashscope.api_key = api_key
    #print(messages)
    response = dashscope.MultiModalConversation.call(
        model='qwen-vl-plus', # 此处以qwen-vl-max为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        messages=messages
    )

    if response.status_code == HTTPStatus.OK:
        #print(response)
        return response
    else:
        #print("Request failed: %s" % response.status_code)
        return None
    

def compare_img(image_path1, image_path2):
    image_bytes_list = []
    with open(image_path1, 'rb') as f:
        image_bytes = f.read()
        #image_bytes = remove(image_bytes)
        image_bytes = base64.b64encode(image_bytes).decode('utf-8')
        image_bytes_list.append(image_bytes)
    with open(image_path2, 'rb') as f:
        image_bytes = f.read()
        image_bytes = base64.b64encode(image_bytes).decode('utf-8')
        image_bytes_list.append(image_bytes)

    return compare_img_bytes(image_bytes_list)
    

if __name__ == '__main__':

    img_file = "nirvana.png"
    img_file2 = "ele.png"
    compare_img(img_file, img_file2)

