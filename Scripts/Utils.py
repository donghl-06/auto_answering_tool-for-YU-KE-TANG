import threading
import pyttsx3
import json
import urllib3
import requests
import random
import os
import sys

lock = threading.Lock()

def say_something(text):
    # 带线程锁的语音函数
    lock.acquire()
    pyttsx3.speak(text)
    lock.release()
    
def dict_result(text):
    # json string 转 dict object
    return dict(json.loads(text))

def test_network():
    # 网络状态测试
    try:
        http = urllib3.PoolManager()
        http.request('GET', 'https://baidu.com')
        return True
    except:
        return False

def calculate_waittime(limit, type, custom_time):
    # 计算答题等待时间
    '''
    type
    1: 随机
    2: 自定义
    '''
    def default_calculate(limit):
        # 默认的随机答题等待时间算法
        if limit == -1:
            wait_time = random.randint(5,20)
        else:
            if limit > 15:
                wait_time = random.randint(5,limit-10)
            else:
                wait_time = 0
        return wait_time

    if type == 1:
        wait_time = default_calculate(limit)
    elif type == 2:
        # 如果自定义等待时间超过当前题目的剩余时间，则采用默认算法
        if custom_time > limit:
            wait_time = default_calculate(limit)
        else:
            wait_time = custom_time
    return wait_time

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

def query_deepseek(problem_dict, api_key, timeout=15, model="deepseek-chat", question_type="single"):
    if not api_key:
        return (None, "未配置API密钥")

    system_prompt = (
        "你是一个专门解答课堂测验问题的助手。你会收到一道课堂问题的JSON数据，"
        "请分析问题内容，选出正确的答案。\n\n"
        "要求：\n"
        '1. 仔细阅读问题、选项和所有相关信息\n'
        '2. 只输出一个JSON对象，格式严格如下：\n'
        '   {"answer": ["选项字母"], "reasoning": "因为..."}\n'
        "3. answer必须是数组：\n"
        '   - 单选题：["A"] 或 ["B"] 等\n'
        '   - 多选题：["A","C"] 等（所有正确选项）\n'
        '   - 填空题：["正确答案"]\n'
        "4. 不要输出解释或其他文字，只输出JSON\n"
        '5. 如果无法确定答案，返回 {"answer": [], "reasoning": "无法确定"}'
    )
    type_hint_map = {
        "single": "这是一道单选题，只需选出一个正确选项。",
        "multiple": "这是一道多选题，需要选出所有正确选项。",
        "fill": "这是一道填空题。",
    }
    type_hint = type_hint_map.get(question_type, "")
    user_prompt = "题目类型提示：" + type_hint + "\n请回答以下课堂问题。问题JSON数据：\n" + json.dumps(problem_dict, ensure_ascii=False, indent=2)

    headers = {
        "Authorization": "Bearer %s" % api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 512,
    }

    try:
        r = requests.post(
            DEEPSEEK_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
            proxies={"http": None, "https": None},
        )
        r.raise_for_status()
        response_data = r.json()
        content = response_data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        answer_list = parsed.get("answer", [])
        reasoning = parsed.get("reasoning", "")
        if isinstance(answer_list, list) and len(answer_list) > 0:
            return (answer_list, reasoning)
        return (None, reasoning)
    except requests.exceptions.Timeout:
        return (None, "请求超时")
    except requests.exceptions.RequestException as e:
        return (None, "网络错误: %s" % str(e))
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return (None, "响应解析失败: %s" % str(e))

def get_initial_data():
    # 默认配置信息
    initial_data = \
    {
        "sessionid":"",
        "auto_danmu":True,
        "danmu_config":{
            "danmu_limit":5
        },
        "audio_on":True,
        "audio_config":{
            "audio_type":{
                "send_danmu":False,
                "others_danmu":False,
                "receive_problem":True,
                "answer_result":True,
                "im_called":True,
                "others_called":True,
                "course_info":True,
                "network_info":True
            }
        },
        "auto_answer":True,
        "answer_config":{
            "answer_delay":{
                "type":1,
                "custom":{
                    "time":0
                }
            }
        },
        "deepseek_config":{
            "enabled":False,
            "api_key":"",
            "model":"deepseek-v4-pro",
            "timeout":15
        }
    }
    return initial_data

def get_config_path():
    # 获取配置文件路径
    config_route = get_config_dir() + "\\config.json"
    return config_route

def get_config_dir():
    # 获取配置文件所在文件夹
    appdata_route = os.environ['APPDATA']
    dir_route = appdata_route + "\\RainClassroomAssistant"
    return dir_route

def get_user_info(sessionid):
    # 获取用户信息
    headers = {
        "Cookie":"sessionid=%s" % sessionid,
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0",
    }
    r = requests.get(url="https://pro.yuketang.cn/api/v3/user/basic-info",headers=headers,proxies={"http": None,"https":None},timeout=10)
    rtn = dict_result(r.text)
    return (rtn["code"],rtn["data"])

def get_on_lesson(sessionid):
    # 获取用户当前正在上课列表
    headers = {
        "Cookie":"sessionid=%s" % sessionid,
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0",
    }
    r = requests.get("https://pro.yuketang.cn/api/v3/classroom/on-lesson",headers=headers,proxies={"http": None,"https":None},timeout=10)
    rtn = dict_result(r.text)
    return rtn["data"]["onLessonClassrooms"]

def get_on_lesson_old(sessionid):
    # 获取用户当前正在上课的列表（旧版）
    headers = {
        "Cookie":"sessionid=%s" % sessionid,
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0",
    }
    r = requests.get("https://pro.yuketang.cn/v/course_meta/on_lesson_courses",headers=headers,proxies={"http": None,"https":None})
    rtn = dict_result(r.text)
    return rtn["on_lessons"]

def resource_path(relative_path):
    # 解决打包exe的图片路径问题
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    print(os.path.join(base_path, relative_path))
    return os.path.join(base_path, relative_path)