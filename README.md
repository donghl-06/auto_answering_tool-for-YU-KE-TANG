# 荷塘雨课堂助手

基于 [RainClassroomAssistant](https://github.com/TrickyDeath/RainClassroomAssitant) 修改，专门适配清华大学荷塘雨课堂的桌面端辅助工具。

## 功能

- **自动签到** — 检测到上课后自动完成签到
- **自动答题** — 支持单选题、多选题、填空题的自动作答（从 PPT 中提取答案）
- **DeepSeek AI 答题** — 当 PPT 中无答案时，可调用 DeepSeek API 智能解答
- **自动跟风弹幕** — 一定时间内收到足够数量的相同弹幕后，自动发送
- **语音提醒** — 点名、收到题目、答题结果等情况可语音播报
- **多课程监听** — 支持同时监听多门正在上课的课程
- **图形化界面** — 基于 PyQt5 的简洁桌面 UI

## 截图

> 运行后在主界面点击「登录」通过微信扫码登录，即可在「监听列表」中看到当前正在上课的课程。

## 安装与运行

### 方式一：Release 版本（推荐）

从 [Releases](https://github.com/TrickyDeath/RainClassroomAssitant/releases) 页面下载打包好的可执行文件，双击运行即可。

### 方式二：从源码运行

**环境要求**：Python 3.7+

```bash
# 1. 克隆仓库
git clone https://github.com/TrickyDeath/RainClassroomAssitant.git
cd RainClassroomAssitant

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python main.py
```

### 打包为 exe

```bash
pyinstaller -F -w -i UI/Image/favicon.ico --add-data "UI/Image;UI/Image" main.py
```

## 依赖

| 包 | 最低版本 | 用途 |
|---|---|---|
| PyQt5 | 5.15.7 | GUI 框架 |
| pyttsx3 | 2.99 | 语音合成（TTS） |
| requests | 2.34.0 | HTTP 请求 |
| urllib3 | 2.0 | 网络连接检测 |
| websocket-client | 1.9.0 | WebSocket 实时通信 |

## 使用说明

1. **登录**：点击主界面「登录」按钮，使用微信扫描二维码登录荷塘雨课堂
2. **配置**：点击「配置」按钮，按需开启：
   - **弹幕配置**：开启自动跟风弹幕，设置触发阈值
   - **语音配置**：选择需要语音提醒的事件类型
   - **答题配置**：开启自动答题，选择随机延迟或自定义延迟
   - **DeepSeek 智能答题**：填入 [DeepSeek API Key](https://platform.deepseek.com/)，当 PPT 无答案时自动调用 AI 解答
3. **启用**：点击「启用」按钮开始监听，检测到上课课程后自动加入监听列表

## 配置文件

配置文件位于 `%APPDATA%\RainClassroomAssistant\config.json`，默认内容如下：

```json
{
  "sessionid": "",
  "auto_danmu": true,
  "danmu_config": { "danmu_limit": 5 },
  "audio_on": true,
  "audio_config": {
    "audio_type": {
      "send_danmu": false,
      "others_danmu": false,
      "receive_problem": true,
      "answer_result": true,
      "im_called": true,
      "others_called": true,
      "course_info": true,
      "network_info": true
    }
  },
  "auto_answer": true,
  "answer_config": {
    "answer_delay": { "type": 1, "custom": { "time": 0 } }
  },
  "deepseek_config": {
    "enabled": false,
    "api_key": "",
    "model": "deepseek-v4-pro",
    "timeout": 15
  }
}
```

## 项目结构

```
├── main.py              # 程序入口
├── requirements.txt     # Python 依赖
├── Scripts/
│   ├── Classes.py       # 课程类（WebSocket 通信、答题、弹幕）
│   ├── Monitor.py       # 课程监听器（轮询上课状态）
│   └── Utils.py         # 工具函数（TTS、网络检测、DeepSeek API、配置管理）
└── UI/
    ├── MainWindow.py    # 主窗口界面
    ├── Login.py         # 扫码登录对话框
    ├── Config.py        # 配置对话框
    └── Image/           # 图片资源
```

## 免责声明

本工具仅供学习交流使用，请勿用于任何违反学校规定的用途。使用本工具产生的任何后果由使用者自行承担。

## 许可

基于原项目 [RainClassroomAssistant](https://github.com/TrickyDeath/RainClassroomAssitant) 修改，沿用其开源许可。
