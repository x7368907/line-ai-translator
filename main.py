from fastapi import FastAPI, Request
from dotenv import load_dotenv
from openai import OpenAI

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessageAction,
    MessagingApi,
    QuickReply,
    QuickReplyItem,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

import os
import re

load_dotenv()

app = FastAPI()

# OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# LINE
configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))


@app.get("/")
def home():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):

    body = await request.body()
    signature = request.headers.get("X-Line-Signature")

    handler.handle(body.decode("utf-8"), signature)

    return "OK"


# 判斷是否為日文
def is_japanese(text):

    japanese_pattern = re.compile(r"[\u3040-\u30ff]")

    return bool(japanese_pattern.search(text))


@handler.add(MessageEvent)
def handle_message(event):

    if not isinstance(event.message, TextMessageContent):
        return

    user_text = event.message.text

    # 預設模式
    mode = "translate"
    content = user_text

    # 指令判斷
    if user_text.startswith("/分析"):
        mode = "analyze"
        content = user_text.replace("/分析", "").strip()

    elif user_text.startswith("/回覆"):
        mode = "reply"
        content = user_text.replace("/回覆", "").strip()

    elif user_text.startswith("/翻譯"):
        mode = "translate"
        content = user_text.replace("/翻譯", "").strip()

    elif user_text.startswith("/可愛"):
        mode = "cute"
        content = user_text.replace("/可愛", "").strip()

    elif user_text.startswith("/普通"):
        mode = "normal"
        content = user_text.replace("/普通", "").strip()

    elif user_text.startswith("/曖昧"):
        mode = "flirty"
        content = user_text.replace("/曖昧", "").strip()

    elif user_text.startswith("/高冷"):
        mode = "cold"
        content = user_text.replace("/高冷", "").strip()

    # /回覆 → 顯示 quick reply
    if mode == "reply":

        with ApiClient(configuration) as api_client:

            line_bot_api = MessagingApi(api_client)

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(
                            text="請選擇回覆風格：",
                            quick_reply=QuickReply(
                                items=[
                                    QuickReplyItem(
                                        action=MessageAction(
                                            label="可愛", text=f"/可愛 {content}"
                                        )
                                    ),
                                    QuickReplyItem(
                                        action=MessageAction(
                                            label="普通", text=f"/普通 {content}"
                                        )
                                    ),
                                    QuickReplyItem(
                                        action=MessageAction(
                                            label="曖昧", text=f"/曖昧 {content}"
                                        )
                                    ),
                                    QuickReplyItem(
                                        action=MessageAction(
                                            label="高冷", text=f"/高冷 {content}"
                                        )
                                    ),
                                ]
                            ),
                        )
                    ],
                )
            )

        return

    # Prompt
    if mode == "cute":

        prompt = f"""
請用可愛、撒嬌的日系 LINE 聊天風格回覆。

規則：
- 簡短自然
- 像真人聊天
- 不要解釋
- 只輸出回覆內容

內容：
{content}
"""

    elif mode == "normal":

        prompt = f"""
請用自然普通的 LINE 聊天方式回覆。

規則：
- 自然聊天感
- 不要太正式
- 不要解釋
- 只輸出回覆內容

內容：
{content}
"""

    elif mode == "flirty":

        prompt = f"""
請用帶點曖昧感的日系 LINE 聊天方式回覆。

規則：
- 自然
- 有一點心動感
- 不要太油
- 不要解釋
- 只輸出回覆內容

內容：
{content}
"""

    elif mode == "cold":

        prompt = f"""
請用有點高冷但不失禮貌的 LINE 聊天方式回覆。

規則：
- 簡短
- 酷一點
- 不要太熱情
- 不要解釋
- 只輸出回覆內容

內容：
{content}
"""

    elif mode == "analyze":

        if is_japanese(content):
            target_language = "繁體中文"
        else:
            target_language = "自然日文"

        prompt = f"""
請先翻譯成{target_language}。

再簡短分析聊天語氣。

輸出格式：

翻譯：
（翻譯內容）

語氣：
（簡短分析）

規則：
- 分析簡短即可
- 不要過度腦補
- 只根據這句話判斷

內容：
{content}
"""

    else:

        # 翻譯模式
        if is_japanese(content):
            target_language = "繁體中文"
        else:
            target_language = "自然日文"

        prompt = f"""
請翻譯成{target_language}。

規則：
- 使用自然 LINE 聊天口語
- 保留原本語氣
- 不要潤飾原文
- 不要增加語意
- 如果原文有 emoji 或顏文字則保留
- 如果原文沒有，不要自行新增 emoji
- 只輸出翻譯結果

內容：
{content}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-nano", messages=[{"role": "user", "content": prompt}]
    )

    result = response.choices[0].message.content

    with ApiClient(configuration) as api_client:

        line_bot_api = MessagingApi(api_client)

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token, messages=[TextMessage(text=result)]
            )
        )
