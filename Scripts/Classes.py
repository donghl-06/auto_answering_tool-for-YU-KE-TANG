import requests
import threading
import random
import time
import websocket
import json
from Scripts.Utils import get_user_info, dict_result, calculate_waittime, query_deepseek

wss_url = "wss://pro.yuketang.cn/wsapp/"
class Lesson:
    def __init__(self,lessonid,lessonname,classroomid,main_ui):
        self.classroomid = classroomid
        self.lessonid = lessonid
        self.lessonname = lessonname
        self.sessionid = main_ui.config["sessionid"]
        self.headers = {
            "Cookie":"sessionid=%s" % self.sessionid,
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0",
        }
        self.receive_danmu = {}
        self.sent_danmu_dict = {}
        self.danmu_dict = {}
        self.problems_ls = []
        self.seen_problem_ids = set()
        self.answered_problem_ids = set()
        self.unlocked_problem = []
        self.classmates_ls = []
        self.add_message = main_ui.add_message_signal.emit
        self.add_course = main_ui.add_course_signal.emit
        self.del_course = main_ui.del_course_signal.emit
        self.config = main_ui.config
        code, rtn = get_user_info(self.sessionid)
        self.user_uid = rtn["id"]
        self.user_uname = rtn["name"]
        self.main_ui = main_ui

    def _get_ppt(self,presentationid):
        # 获取课程各页ppt
        r = requests.get(url="https://pro.yuketang.cn/api/v3/lesson/presentation/fetch?presentation_id=%s" % (presentationid),headers=self.headers,proxies={"http": None,"https":None},timeout=15)
        return dict_result(r.text)["data"]

    def get_problems(self,presentationid):
        # 获取课程ppt中的题目
        data = self._get_ppt(presentationid)
        problems = []
        for idx, slide in enumerate(data["slides"]):
            if "problem" in slide:
                problem = slide["problem"]
                page = slide.get("order") or slide.get("page") or slide.get("slideNumber") or (idx + 1)
                problem["_slidePage"] = page
                problems.append(problem)
        total_slides = len(data["slides"])
        new_problems = [p for p in problems if p["problemId"] not in self.seen_problem_ids]
        self.add_message("【DEBUG】[%s] PPT扫描：共%s页，题目总数%s，新题目%s" % (self.lessonname, total_slides, len(problems), len(new_problems)), 3)
        if new_problems:
            for p in new_problems:
                options = p.get("options", [])
                if options:
                    opt_str = " ".join("%s.%s" % (o["key"], o["value"]) for o in options)
                    self.add_message("【DEBUG】[%s] PPT新题目（第%s页）：%s 【选项】%s" % (self.lessonname, p["_slidePage"], p.get("body", ""), opt_str), 3)
                else:
                    self.add_message("【DEBUG】[%s] PPT新题目（第%s页）：%s" % (self.lessonname, p["_slidePage"], p.get("body", "")), 3)
                # 打印题目所有字段名，便于定位真实题干位置
                all_keys = sorted(p.keys())
                extra_fields = {k: p[k] for k in all_keys if k not in ("problemId", "problemType", "body", "options", "blanks", "answers", "score", "limit", "sendTime", "result", "_slidePage", "bullets", "submit")}
                if extra_fields:
                    self.add_message("【DEBUG】[%s] 题目额外字段: %s" % (self.lessonname, json.dumps(extra_fields, ensure_ascii=False)), 3)
        for p in new_problems:
            self.seen_problem_ids.add(p["problemId"])
        return new_problems

    def answer_questions(self,problemid,problemtype,answer,limit):
        # 回答问题
        if answer:
            wait_time = calculate_waittime(limit, self.config["answer_config"]["answer_delay"]["type"], self.config["answer_config"]["answer_delay"]["custom"]["time"])
            if wait_time != 0:
                meg = "%s检测到问题，将在%s秒后自动回答，答案为%s" % (self.lessonname,wait_time,answer)
                # threading.Thread(target=say_something,args=(meg,)).start()
                self.add_message(meg,3)
                time.sleep(wait_time)
            else:
                meg = "%s检测到问题，剩余时间小于15秒，将立即自动回答，答案为%s" % (self.lessonname,answer)
                self.add_message(meg,3)
                # threading.Thread(target=say_something,args=(meg,)).start()
            data = {"problemId":problemid,"problemType":problemtype,"dt":int(time.time()),"result":answer}
            r = requests.post(url="https://pro.yuketang.cn/api/v3/lesson/problem/answer",headers=self.headers,data=json.dumps(data),proxies={"http": None,"https":None},timeout=10)
            return_dict = dict_result(r.text)
            if return_dict["code"] == 0:
                meg = "%s自动回答成功" % self.lessonname
                self.add_message(meg,4)
                # threading.Thread(target=say_something,args=(meg,)).start()
                return True
            else:
                meg = "%s自动回答失败，原因：%s" % (self.lessonname,return_dict["msg"].replace("_"," "))
                self.add_message(meg,4)
                # threading.Thread(target=say_something,args=(meg,)).start()
                return False
        else:
            if limit == -1:
                meg = "%s的问题没有找到答案，该题不限时，请尽快前往荷塘雨课堂回答" % (self.lessonname)
            else:
                meg = "%s的问题没有找到答案，请在%s秒内前往荷塘雨课堂回答" % (self.lessonname,limit)
            # threading.Thread(target=say_something,args=(meg,)).start()
            self.add_message(meg,4)
            return False
    
    def on_open(self, wsapp):
        self.handshark = {"op":"hello","userid":self.user_uid,"role":"student","auth":self.auth,"lessonid":self.lessonid}
        wsapp.send(json.dumps(self.handshark))

    def checkin_class(self):
        r = requests.post(url="https://pro.yuketang.cn/api/v3/lesson/checkin",headers=self.headers,data=json.dumps({"source":5,"lessonId":self.lessonid}),proxies={"http": None,"https":None},timeout=15)
        set_auth = r.headers.get("Set-Auth",None)
        times = 1
        while not set_auth and times <= 3:
            set_auth = r.headers.get("Set-Auth",None)
            times += 1
            time.sleep(1)
        self.headers["Authorization"] = "Bearer %s" % set_auth
        return dict_result(r.text)["data"]["lessonToken"]

    def on_message(self, wsapp, message):
        data = dict_result(message)
        op = data["op"]
        if op == "hello":
            presentations = list(set([slide["pres"] for slide in data["timeline"] if slide["type"]=="slide"]))
            current_presentation = data["presentation"]
            if current_presentation not in presentations:
                presentations.append(current_presentation)
            for presentationid in presentations:
                self.problems_ls.extend(self.get_problems(presentationid))
            self.unlocked_problem = data["unlockedproblem"]
            for problemid in self.unlocked_problem:
                self._current_problem(wsapp, problemid)
        elif op == "unlockproblem":
            self.add_message("【DEBUG】unlockproblem 数据：%s" % json.dumps(data, ensure_ascii=False), 3)
            self.start_answer(data["problem"]["sid"],data["problem"]["limit"])
        elif op == "lessonfinished":
            meg = "%s下课了" % self.lessonname
            # threading.Thread(target=say_something,args=(meg,)).start()
            self.add_message(meg,7)
            wsapp.close()
        elif op == "presentationupdated":
            self.problems_ls.extend(self.get_problems(data["presentation"]))
        elif op == "presentationcreated":
            self.problems_ls.extend(self.get_problems(data["presentation"]))
        elif op == "newdanmu" and self.config["auto_danmu"]:
            current_content = data["danmu"].lower()
            uid = data["userid"]
            sent_danmu_user = User(uid)
            if sent_danmu_user in self.classmates_ls:
                for i in self.classmates_ls:
                    if i == sent_danmu_user:
                        meg = "%s课程的%s%s发送了弹幕：%s" %(self.lessonname,i.sno,i.name,data["danmu"])
                        self.add_message(meg,2)
                        break
            else:
                self.classmates_ls.append(sent_danmu_user)
                sent_danmu_user.get_userinfo(self.classroomid,self.headers)
                meg = "%s课程的%s%s发送了弹幕：%s" %(self.lessonname,sent_danmu_user.sno,sent_danmu_user.name,data["danmu"])
                self.add_message(meg,2)
            now = time.time()
            # 收到一条弹幕，尝试取出其之前的所有记录的列表，取不到则初始化该内容列表
            try:
                same_content_ls = self.danmu_dict[current_content]
            except KeyError:
                self.danmu_dict[current_content] = []
                same_content_ls = self.danmu_dict[current_content]
            # 清除超过60秒的弹幕记录
            for i in same_content_ls:
                if now - i > 60:
                    same_content_ls.remove(i)
            # 如果当前的弹幕没被发过，或者已发送时间超过60秒
            if current_content not in self.sent_danmu_dict.keys() or now - self.sent_danmu_dict[current_content] > 60:
                if len(same_content_ls) + 1 >= self.config["danmu_config"]["danmu_limit"]:
                    self.send_danmu(current_content)
                    same_content_ls = []
                    self.sent_danmu_dict[current_content] = now
                else:
                    same_content_ls.append(now)
        elif op == "callpaused":
            meg = "%s点名了，点到了：%s" % (self.lessonname, data["name"])
            if self.user_uname == data["name"]:
                self.add_message(meg,5)
            else:
                self.add_message(meg,6)
        # 程序在上课中途运行，由_current_problem发送的已解锁题目数据，得到的返回值。
        # 此处需要筛选未到期的题目进行回答。
        elif op == "probleminfo":
            if data["limit"] != -1:
                time_left = int(data["limit"]-(int(data["now"]) - int(data["dt"]))/1000)
            else:
                time_left = data["limit"]
            # 筛选未到期题目
            if time_left > 0 or time_left == -1:
                if self.config["auto_answer"]:
                    self.start_answer(data["problemid"],time_left)
                else:
                    if time_left == -1:
                        meg = "%s检测到问题，该题不限时，请尽快前往荷塘雨课堂回答" % (self.lessonname)
                        self.add_message(meg,3)
                    else:
                        meg = "%s检测到问题，请在%s秒内前往荷塘雨课堂回答" % (self.lessonname,time_left)

    def _get_question_type(self, promble):
        problem_type = promble.get("problemType", "")
        pt_str = str(problem_type).lower()
        # 投票题检测：problemType=3 或题干含"投票"关键词
        if pt_str in ("3", "vote", "poll"):
            return "vote"
        body = promble.get("body", "")
        if "投票" in body:
            return "vote"
        if pt_str in ("2", "multiple", "multi_choice", "multiple_choice"):
            return "multiple"
        if pt_str in ("1", "single", "single_choice"):
            return "single"
        answers = promble.get("answers", [])
        if len(answers) > 1:
            return "multiple"
        if len(answers) == 1:
            return "single"
        if "多选" in body or "多选题" in body:
            return "multiple"
        if "单选" in body or "单选题" in body:
            return "single"
        return "single"

    def start_answer(self, problemid, limit):
        if problemid in self.answered_problem_ids:
            self.add_message("【DEBUG】problemId=%s 已处理过，跳过" % problemid, 3)
            return
        self.answered_problem_ids.add(problemid)
        for promble in self.problems_ls:
            if promble["problemId"] == problemid:
                self.add_message("【DEBUG】找到匹配题目 problemId=%s（第%s页），数据：%s" % (problemid, promble.get("_slidePage", "?"), json.dumps(promble, ensure_ascii=False)), 3)
                if promble["result"] is not None:
                    # 如果该题已经作答过，直接跳出函数以忽略该题
                    # 该情况理论上只会出现在启动监听时
                    return
                question_type = self._get_question_type(promble)
                self.add_message("【DEBUG】题目类型: %s（problemType原始值: %s）" % (question_type, promble.get("problemType", "无")), 3)
                blanks = promble.get("blanks",[])
                answers = []
                if blanks:
                    for i in blanks:
                        answers.append(random.choice(i["answers"]))
                else:
                    answers = promble.get("answers",[])
                # 投票题：无标准答案，跳过PPT答案，尝试DeepSeek后随机兜底
                if question_type == "vote":
                    self.add_message("%s 检测到投票题，将随机选择选项" % self.lessonname, 3)
                if not answers:
                    # PPT无答案时，尝试调用DeepSeek AI
                    deepseek_cfg = self.config.get("deepseek_config", {})
                    if deepseek_cfg.get("enabled", False):
                        ds_api_key = deepseek_cfg.get("api_key", "")
                        ds_timeout = deepseek_cfg.get("timeout", 15)
                        ds_model = deepseek_cfg.get("model", "deepseek-chat")
                        self.add_message("%s PPT无答案，正在请求DeepSeek AI解答..." % self.lessonname, 3)
                        ds_result = query_deepseek(promble, ds_api_key, ds_timeout, ds_model, question_type)
                        if ds_result[0]:
                            answers = ds_result[0]
                            self.add_message("%s DeepSeek返回答案: %s" % (self.lessonname, answers), 3)
                            if ds_result[1]:
                                self.add_message("%s DeepSeek推理: %s" % (self.lessonname, ds_result[1]), 3)
                        else:
                            if ds_result[1]:
                                self.add_message("%s DeepSeek失败: %s" % (self.lessonname, ds_result[1]), 4)
                            else:
                                self.add_message("%s DeepSeek未能获取答案" % (self.lessonname, 4))
                # DeepSeek未给出答案时，从选项中随机选择一个作为兜底
                if not answers:
                    options = promble.get("options", [])
                    if options:
                        fallback = random.choice([o["key"] for o in options])
                        answers = [fallback]
                        if question_type == "vote":
                            self.add_message("%s 投票题随机选择选项: %s" % (self.lessonname, fallback), 3)
                        else:
                            self.add_message("%s 未能获取答案，随机选择选项: %s" % (self.lessonname, fallback), 4)
                threading.Thread(target=self.answer_questions,args=(promble["problemId"],promble["problemType"],answers,limit)).start()
                break
        else:
            self.add_message("【DEBUG】在 problems_ls 中未找到 problemId=%s" % problemid, 3)
            if limit == -1:
                meg = "%s的问题没有找到答案，该题不限时，请尽快前往荷塘雨课堂回答" % (self.lessonname)
            else:
                meg = "%s的问题没有找到答案，请在%s秒内前往荷塘雨课堂回答" % (self.lessonname,limit)
            self.add_message(meg,4)
            # threading.Thread(target=say_something,args=(meg,)).start()

    
    def _current_problem(self, wsapp, promblemid):
        # 为获取已解锁的问题详情信息，向wsapp发送probleminfo
        query_problem = {"op":"probleminfo","lessonid":self.lessonid,"problemid":promblemid,"msgid":1}
        wsapp.send(json.dumps(query_problem))
    
    def start_lesson(self, callback):
        self.auth = self.checkin_class()
        rtn = self.get_lesson_info()
        teacher = rtn["teacher"]["name"]
        title = rtn["title"]
        timestamp = rtn["startTime"] // 1000
        time_str = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(timestamp))
        index = self.main_ui.tableWidget.rowCount()
        self.add_course([self.lessonname,title,teacher,time_str],index)
        self.wsapp = websocket.WebSocketApp(url=wss_url,header=self.headers,on_open=self.on_open,on_message=self.on_message)
        self.wsapp.run_forever()
        meg = "%s监听结束" % self.lessonname
        self.add_message(meg,7)
        self.del_course(index)
        # threading.Thread(target=say_something,args=(meg,)).start()
        return callback(self)
    
    def send_danmu(self,content):
        url = "https://pro.yuketang.cn/api/v3/lesson/danmu/send"
        data = {
            "extra": "",
            "fromStart": "50",
            "lessonId": self.lessonid,
            "message": content,
            "requiredCensor": False,
            "showStatus": True,
            "target": "",
            "userName": "",
            "wordCloud": True
        }
        r = requests.post(url=url,headers=self.headers,data=json.dumps(data),proxies={"http": None,"https":None})
        if dict_result(r.text)["code"] == 0:
            meg = "%s弹幕发送成功！内容：%s" % (self.lessonname,content)
        else:
            meg = "%s弹幕发送失败！内容：%s" % (self.lessonname,content)
        self.add_message(meg,1)
    
    def get_lesson_info(self):
        url = "https://pro.yuketang.cn/api/v3/lesson/basic-info"
        r = requests.get(url=url,headers=self.headers,proxies={"http": None,"https":None},timeout=10)
        return dict_result(r.text)["data"]
        

    def __eq__(self, other):
        return self.lessonid == other.lessonid

class User:
    def __init__(self, uid):
        self.uid = uid
    
    def get_userinfo(self, classroomid, headers):
        r = requests.get("https://pro.yuketang.cn/v/course_meta/fetch_user_info_new?query_user_id=%s&classroom_id=%s" % (self.uid,classroomid),headers=headers,proxies={"http": None,"https":None})
        data = dict_result(r.text)["data"]
        self.sno = data["school_number"]
        self.name = data["name"]