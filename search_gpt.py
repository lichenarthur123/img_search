#encoding=utf-8
import dashscope
from http import HTTPStatus

import base64
import numpy as np
import json
import os
import io
from PIL import Image
from rembg import remove
from global_params import api_key, rembg_session


default_task = "分析这张图片中的印花图案是否有明显的侵权风险，\
                如果印花的图案存在明显的品牌、IP、商标信息则为高风险，\
                可以参考搜索结果，并给出侵权风险分数从0-100，0为无风险，100为最高风险。"
default_output = '{"score": 0-100, "reason": "尽可能简洁地表述风险原因"}'
prompt = '请帮我检测图片是否满足下列要求：\n{}\n按照以下规则输出结果：\n{}\n\n'

def search_gpt_bytes(image_bytes, requirement = None, output_format = None):
    
    # 设置图像格式
    image_format = "png"  # 根据实际情况修改，比如jpg、bmp 等
    image_data = f"data:image/{image_format};base64,{image_bytes}"
    # 输入数据

    messages = [
        {
            "role": "user",
            "content": [
                {"image": image_data},
                {"text": prompt.format(
                        requirement if requirement else default_task,
                        output_format if output_format else default_output
                        )}
            ]
        }
    ]

    dashscope.api_key = api_key
    response = dashscope.MultiModalConversation.call(
        model='qwen-vl-plus-latest', # 此处以qwen-vl-max为例，可按需更换模型名称。模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        messages=messages,
        enable_search=True
    )
    if response.status_code == HTTPStatus.OK:
        return response
    else:
        return None
        #print("Request failed: %s" % response.status_code)
    

def search_gpt(image_path, requirement = None, output_format = None, compress_size = 0.5, rmbg = True):
    with open(image_path, 'rb') as f:
        original_image = Image.open(f)
        original_size = original_image.size

        new_size = (int(original_size[0] * compress_size), int(original_size[1] * compress_size))
        compress_img = original_image.resize(new_size, Image.LANCZOS)

        if rmbg:
            compress_img = remove(compress_img, session=rembg_session)

        buff = io.BytesIO()
        compress_img.save(buff, format="PNG")
        image_bytes = buff.getvalue()

        image_bytes = base64.b64encode(image_bytes).decode('utf-8')
        return search_gpt_bytes(image_bytes, requirement, output_format)
    

if __name__ == '__main__':

    img_file = "nirvana.png"
    print(search_gpt(img_file))

