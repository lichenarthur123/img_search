#encoding=utf-8
import os
import time
import threading
import glob
import shutil
import zipfile
import json
from search import search_similar_images
from compare_img import compare_img
from search_gpt import search_gpt

from global_params import global_lock, global_variable

def create_result_xlsx(result_json, result_xlsx_path):
    # 输出excel
    # 输出result_json的内容，每一行对应一个image
    #第一列是image_name
    #第二列是image_search_score，如果分数高于80分，单元格变红色
    #第三列是image_search_reason
    #第四列是top1_image_compare_score，如果分数高于80分，单元格变红色
    #第五列是top1_image_compare_reason
    #第六列是image_gpt_score
    #第七列是image_gpt_reason
    import pandas as pd
    data = {
        "图像文件名":[],
        "版权库检索打分":[],
        "版权库top1相似度":[],
        "版权库top1相似度原因":[],
        "GPT相似度":[],
        "GPT相似度原因":[]
        }
    for image_name, image_info in result_json['tasks'].items():
        data["图像文件名"].append(image_name)
        data["版权库检索打分"].append(image_info["image_search_score"])
        data["版权库top1相似度"].append(image_info["top1_image_compare_score"])
        data["版权库top1相似度原因"].append(image_info["top1_image_compare_reason"])
        data["GPT相似度"].append(image_info["image_gpt_score"])
        data["GPT相似度原因"].append(image_info["image_gpt_reason"])
    df = pd.DataFrame(data)
    def color_red(val):
    # 判断是否为数值且大于0
        if isinstance(val, (int, float)) and val >= 80:
            return 'background-color: red'  # 使用CSS样式字符串
        return '' # 其他情况返回空样式

    styled_df = df.style.map(color_red)
    styled_df.to_excel(result_xlsx_path, engine='openpyxl')
    

def process_task(task_path, source_path, result_path):
    # 解压 source.zip 文件 到source目录下
    with zipfile.ZipFile(source_path, 'r') as zip_ref:
        #zip_ref.extractall(f"{task_path}")
        os.makedirs(f"{task_path}/source", exist_ok=True)
        for file_info in zip_ref.filelist:
            try:
                file_name = file_info.filename.encode('cp437').decode('utf-8')
            except:
                file_name = file_info.filename

            file_path = os.path.join(task_path, file_name)
            if not file_name.endswith('.png'):
                continue
            if file_name.startswith("__"):
                continue
            if not file_info.is_dir():
                with zip_ref.open(file_info) as source:
                    with open(file_path, "wb") as target:
                        target.write(source.read())
        
        
    # 处理 temp 目录中的所有图片
    result_json = {
        "total_tasks": 0,
        "completed_tasks": 0,
        "tasks": {
            #"image_file_name":{
            #    "image_search_score": 0.0,
            #    "image_search_reason": "reason",
            #    "top1_image_compare_score": 0.0,
            #    "top1_image_compare_reason": "reason",
            #    "image_gpt_score": 0.0,
            #    "image_gpt_reason": "reason",
            #}
        }
    }

    for image_path in glob.glob(f"{task_path}/source/*"):
        if image_path.endswith('.jpg') or image_path.endswith('.png'):
            result_json['total_tasks'] += 1
            # 获取图片名
            image_name = os.path.basename(image_path)
            result_json['tasks'][image_name] = {
                "image_search_score": -1,
                "image_search_reason": "",
                "top1_image_compare_score": -1,
                "top1_image_compare_reason": "",
                "image_gpt_score": -1,
                "image_gpt_reason": ""
            }
    
    #  保存 result.json 文件
    with open(result_path, 'w') as f:
        f.write(json.dumps(result_json, ensure_ascii=False, indent=4))

    for image_path in glob.glob(f"{task_path}/source/*"):
        #print(f"processing {image_path} xxxx")
        if image_path.endswith('.jpg') or image_path.endswith('.png'):
            # 获取图片名
            image_name = os.path.basename(image_path)

            res_1 = search_similar_images(image_path, 'database', top_k=1)
            #print(f"search_similar_images")
            if res_1 != None:
                result_json['tasks'][image_name]['image_search_score'] = res_1[0]['similarity']
                result_json['tasks'][image_name]['image_search_reason'] = f"{image_name} 与 {res_1[0]['dir']} 中的 {res_1[0]['fname']} 的相似度为 {res_1[0]['similarity']}"

            res_2 = compare_img(image_path, f"source/{res_1[0]['dir']}/{res_1[0]['fname']}")
            #print(f"compare_img")
            if res_2 != None:
                res_2_json_str = res_2["output"]["choices"][0]["message"]["content"][0]["text"]
                res_2_json_str = res_2_json_str.replace("```json", "").replace("```", "")
                res_2_json = json.loads(res_2_json_str)
                result_json['tasks'][image_name]['top1_image_compare_score'] = res_2_json['score']
                result_json['tasks'][image_name]['top1_image_compare_reason'] = res_2_json['reason']

            res_3 = search_gpt(image_path)
            #print(f"search_gpt")
            if res_3 != None:
                res_3_json_str = res_3["output"]["choices"][0]["message"]["content"][0]["text"]
                res_3_json_str = res_3_json_str.replace("```json", "").replace("```", "")
                res_3_json = json.loads(res_3_json_str)
                result_json['tasks'][image_name]['image_gpt_score'] = res_3_json['score']
                result_json['tasks'][image_name]['image_gpt_reason'] = res_3_json['reason']

            result_json['completed_tasks'] += 1

            # 保存 result.json 文件
            with open(result_path, 'w') as f:
                f.write(json.dumps(result_json, ensure_ascii=False, indent=4))

    
    create_result_xlsx(result_json, f"{task_path}/result.xlsx")


def run_batch_compare_task():
    while True:
        try:
            # 检查 batch_compare_task 目录中的任务
            task_dir = 'batch_compare_task'
            if os.path.exists(task_dir):
                for task_id in os.listdir(task_dir):
                    task_path = os.path.join(task_dir, task_id)
                    if os.path.isdir(task_path):
                        # 检查任务状态（示例逻辑，可根据需求扩展）

                        # 检查是否有DEL_FLAG文件，如果有则删除任务目录
                        del_flag_path = os.path.join(task_path, 'DEL_FLAG')
                        if os.path.exists(del_flag_path):
                            print(f"Deleting task: {task_id}")
                            import shutil
                            shutil.rmtree(task_path)
                            continue
                        
                        # 检查是否有source.zip文件，如果没有则跳过
                        source_zip_path = os.path.join(task_path, 'source.zip')
                        if not os.path.exists(source_zip_path):
                            continue

                        # 检查是否有result.json文件，如果有则跳过
                        result_json_path = os.path.join(task_path, 'result.json')
                        if os.path.exists(result_json_path):
                            continue
                            
                        # 处理任务
                        print(f"processing task: {task_id}")
                        process_task(task_path, source_zip_path, result_json_path)
                        
            time.sleep(5)  # 每5秒轮询一次
        except Exception as e:
            print(f"Error in run_batch_compare_task: {e}")

# filter_task
def create_result(result_json, path):
    # 打包标记为1的文件
    import zipfile
    import os
    print(f"start create_result {path}")
    # 创建压缩包路径
    zip_path = os.path.join(path, "filtered_images.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for image_name, image_filter in result_json['image_filter'].items():
            if image_filter == 1:
                image_path = os.path.join(path, "source", image_name)
                if os.path.exists(image_path):
                    zipf.write(image_path, os.path.basename(image_path))

    print(f"end create_result {path}")
   

def process_filter_task(task_path, source_path, result_path, requirement = None):

    print(f"processing task: {task_path}")
    # 解压 source.zip 文件 到source目录下
    with zipfile.ZipFile(source_path, 'r') as zip_ref:
        #zip_ref.extractall(f"{task_path}")
        os.makedirs(f"{task_path}/source", exist_ok=True)
        for file_info in zip_ref.filelist:
            try:
                file_name = file_info.filename.encode('cp437').decode('utf-8')
            except:
                file_name = file_info.filename

            file_path = os.path.join(task_path, file_name)
            if not file_name.endswith('.png'):
                continue
            if file_name.startswith("__"):
                continue
            if not file_info.is_dir():
                with zip_ref.open(file_info) as source:
                    with open(file_path, "wb") as target:
                        target.write(source.read())
        
    # 处理 temp 目录中的所有图片
    result_json = {
        "total_tasks": 1,
        "completed_tasks": 0,
        'image_filter':{},
        #'image_filter_reason':{}
    }

    image_path_list = []
    for image_path in glob.glob(f"{task_path}/source/*"):
        if image_path.endswith('.jpg') or image_path.endswith('.png'):
            result_json['total_tasks'] += 1
            # 获取图片名
            image_name = os.path.basename(image_path)
            result_json['image_filter'][image_name] = 0
            image_path_list.append(image_path)
    
    #  保存 result.json 文件
    with open(result_path, 'w') as f:
        f.write(json.dumps(result_json, ensure_ascii=False, indent=4))

    output_format = '仅输出1个字，满足要求则输出"是"，不满足要求则输出"否"'

    def task(image_path, requirement, output_format):
        res = search_gpt(image_path=image_path, requirement=requirement, output_format=output_format, rmbg=False)
        image_name = os.path.basename(image_path)
        if res != None:
            res_json_str = res["output"]["choices"][0]["message"]["content"][0]["text"]
            if "是" in res_json_str:
                #image_name = os.path.basename(image_path)
                result_json['image_filter'][image_name] = 1
                return image_name, 1
        return image_name, 0
    
    import concurrent.futures

    batch_size = 10
    batch_num = (len(image_path_list) + batch_size - 1) // batch_size
    for i in range(batch_num):
        start = i * batch_size
        end = min((i + 1) * batch_size, len(image_path_list))
        with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures_list = [executor.submit(task, image_path, requirement, output_format) for image_path in image_path_list[start:end]]
            for future in concurrent.futures.as_completed(futures_list):
                try:
                    image_name, image_filter = future.result()
                    result_json['image_filter'][image_name] = image_filter
                except Exception as e:
                    print(f"Error in process_filter_task: {e}")
        result_json['completed_tasks'] += end - start

        # 保存 result.json 文件
        with open(result_path, 'w') as f:
            f.write(json.dumps(result_json, ensure_ascii=False, indent=4))
        time.sleep(1)
    
    create_result(result_json, task_path)
    result_json['completed_tasks'] += 1
    with open(result_path, 'w') as f:
        f.write(json.dumps(result_json, ensure_ascii=False, indent=4))

def run_batch_filter_task():
    while True:
        try:
            # 检查 batch_filter_task 目录中的任务
            task_dir = 'batch_filter_task'
            if os.path.exists(task_dir):
                for task_id in os.listdir(task_dir):
                    task_path = os.path.join(task_dir, task_id)
                    if os.path.isdir(task_path):
                        # 检查任务状态（示例逻辑，可根据需求扩展）

                        # 检查是否有DEL_FLAG文件，如果有则删除任务目录
                        del_flag_path = os.path.join(task_path, 'DEL_FLAG')
                        if os.path.exists(del_flag_path):
                            print(f"Deleting task: {task_id}")
                            import shutil
                            shutil.rmtree(task_path)
                            continue
                        
                        prompt_file = os.path.join(task_path, 'prompt.txt')
                        requirement = None
                        if not os.path.exists(prompt_file):
                            print(f"Error: prompt.txt not found in {task_path}")
                            import shutil
                            shutil.rmtree(task_path)
                            continue
                        else:
                            with open(prompt_file, 'r') as f:
                                requirement = f.read()
                                if requirement == '':
                                    print(f"Error: requirement is empty in {task_path}")
                                    import shutil
                                    shutil.rmtree(task_path)
                                    continue
                        
                        
                        # 检查是否有source.zip文件，如果没有则跳过
                        source_zip_path = os.path.join(task_path, 'source.zip')
                        if not os.path.exists(source_zip_path):
                            continue

                        # 检查是否有result.json文件，如果有则跳过
                        result_json_path = os.path.join(task_path, 'result.json')
                        if os.path.exists(result_json_path):
                            continue
                            
                        # 处理任务
                        print(f"processing task: {task_id}")
                        process_filter_task(task_path, source_zip_path, result_json_path, requirement)
                        
            time.sleep(5)  # 每5秒轮询一次
        except Exception as e:
            print(f"Error in run_batch_filter_task: {e}")



# 启动轮询线程
def start_task_manager():
    #task_thread = threading.Thread(target=run_batch_compare_task, daemon=True)
    #task_thread.start()

    filter_thread = threading.Thread(target=run_batch_filter_task, daemon=True)
    filter_thread.start()